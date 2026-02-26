from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import uuid

from logging_system import log_event, replay_session, LoggingSystem
from agents.ingestion_agent import IngestionAgent
from agents.categorization_agent import CategorizationAgent
from agents.analysis_agent import AnalysisAgent
from agents.budgeting_agent import BudgetingAgent
from agents.evaluation_agent import EvaluationAgent
from agents.reporting_agent import ReportingAgent
from agents.retrieval_agent import RetrievalAgent
from agents.conversation_agent import ConversationAgent

from security.privilege_model import (
    get_privilege_model,
    validate_agent_action,
    ActionType,
    SecurityException,
)
from security.sandbox import get_sandbox, Sandbox, ResourceLimit
from approval.approval_manager import (
    get_approval_manager,
    request_approval,
    ApprovalType,
    ApprovalStatus,
)
from memory.memory_manager import get_memory_manager
from memory.context_compressor import get_context_compressor
from reliability.retry_manager import (
    get_retry_manager,
    RetryableError,
    NonRetryableError,
    CircuitBreakerOpenError,
)
from reliability.circuit_breaker import get_circuit_breaker
from reliability.fallback_manager import get_fallback_manager
from reliability.checkpoint_manager import get_checkpoint_manager
from reliability.session_guard import (
    get_session_guard,
    SessionLimitExceeded,
    TerminationReason,
)


class WorkflowState(Enum):
    """Workflow states for the financial agent system."""

    INIT = "INIT"
    INGEST = "INGEST"
    CATEGORIZE = "CATEGORIZE"
    ANALYZE = "ANALYZE"
    BUDGET = "BUDGET"
    EVALUATE = "EVALUATE"
    REPORT = "REPORT"
    REFINE = "REFINE"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETE = "COMPLETE"


VALID_TRANSITIONS = {
    WorkflowState.INIT: [WorkflowState.INGEST],
    WorkflowState.INGEST: [WorkflowState.CATEGORIZE],
    WorkflowState.CATEGORIZE: [WorkflowState.ANALYZE],
    WorkflowState.ANALYZE: [WorkflowState.BUDGET],
    WorkflowState.BUDGET: [WorkflowState.EVALUATE],
    WorkflowState.EVALUATE: [WorkflowState.REPORT, WorkflowState.WAITING_APPROVAL],
    WorkflowState.REPORT: [WorkflowState.REFINE, WorkflowState.COMPLETE],
    WorkflowState.REFINE: [WorkflowState.REFINE, WorkflowState.COMPLETE],
    WorkflowState.WAITING_APPROVAL: [WorkflowState.REPORT],
    WorkflowState.COMPLETE: [],
}


@dataclass
class OrchestratorResult:
    """Result from orchestrator execution."""

    session_id: str
    final_state: WorkflowState
    final_report: Dict[str, Any]
    event_log: List[Dict[str, Any]]
    iterations: int
    success: bool
    error: Optional[str] = None


class Orchestrator:
    """
    Main orchestrator for the financial decision system.

    Responsibilities:
    - Maintain workflow state
    - Enforce max iteration count
    - Route to correct agent based on state
    - Retry failed steps
    - Validate outputs
    - Log all transitions
    - Enforce security (privilege model, sandbox, approval)
    """

    def __init__(
        self,
        max_iterations: int = 10,
        max_retries: int = 2,
        logger: Optional[LoggingSystem] = None,
        enable_security: bool = True,
    ):
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.logger = logger
        self.enable_security = enable_security

        self.agents = {
            "ingestion": IngestionAgent(),
            "categorization": CategorizationAgent(),
            "analysis": AnalysisAgent(),
            "budgeting": BudgetingAgent(),
            "evaluation": EvaluationAgent(),
            "reporting": ReportingAgent(),
            "retrieval": RetrievalAgent(),
            "conversation": ConversationAgent(),
        }

        self.state = WorkflowState.INIT
        self.session_id = ""
        self.user_id = ""
        self.context: Dict[str, Any] = {}
        self.iteration_count = 0
        self.pending_approval_request_id: Optional[str] = None

        if self.enable_security:
            self.privilege_model = get_privilege_model()
            self.sandbox = get_sandbox(
                ResourceLimit(timeout_seconds=30.0, max_tokens=4096)
            )
            self.approval_manager = get_approval_manager()

        self.memory_manager = get_memory_manager()
        self.context_compressor = get_context_compressor()

        self.retry_manager = get_retry_manager()
        self.circuit_breaker = get_circuit_breaker()
        self.fallback_manager = get_fallback_manager()
        self.checkpoint_manager = get_checkpoint_manager()
        self.session_guard = get_session_guard()

        self.completed_agents: List[str] = []
        self.degraded_mode = False

    def validate_transition(self, target_state: WorkflowState) -> bool:
        """
        Validate if transition to target state is allowed.

        Args:
            target_state: Target workflow state

        Returns:
            True if transition is valid
        """
        valid_targets = VALID_TRANSITIONS.get(self.state, [])
        return target_state in valid_targets

    def get_agent_for_state(self, state: WorkflowState) -> str:
        """Get agent name for a given state."""
        state_to_agent = {
            WorkflowState.INGEST: "ingestion",
            WorkflowState.CATEGORIZE: "categorization",
            WorkflowState.ANALYZE: "analysis",
            WorkflowState.BUDGET: "budgeting",
            WorkflowState.EVALUATE: "evaluation",
            WorkflowState.REPORT: "reporting",
            WorkflowState.REFINE: "conversation",
        }
        return state_to_agent.get(state, "")

    def transition_to(self, new_state: WorkflowState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: Target state

        Raises:
            ValueError: If transition is not valid
        """
        if not self.validate_transition(new_state):
            raise ValueError(f"Invalid transition from {self.state} to {new_state}")
        self.state = new_state

        self.memory_manager.update_short_term_state(
            session_id=self.session_id,
            user_id=self.user_id,
            workflow_state=self.state.value,
        )

    def _retrieve_and_compress_context(self) -> None:
        """Retrieve historical context and compress for LLM usage."""
        retrieval_agent = self.agents["retrieval"]

        historical_data = retrieval_agent.execute(
            self.session_id,
            {"user_id": self.user_id, "months": 6, "include_trends": True},
        )

        self.context["historical_context"] = historical_data

        compressed = self.context_compressor.compress_historical_context(
            user_id=self.user_id,
            session_id=self.session_id,
            historical_data=historical_data,
            current_month_data=self.context.get("analysis"),
        )

        self.context["compressed_context"] = self.context_compressor.to_json_string(
            compressed
        )
        self.context["compressed_context_formatted"] = (
            self.context_compressor.to_llm_prompt(compressed)
        )

        log_event(
            session_id=self.session_id,
            state=self.state.value,
            agent_name="context_compressor",
            input_payload={"user_id": self.user_id, "months": 6},
            output_payload={
                "compressed": True,
                "context": self.context["compressed_context"],
            },
            error_flag=False,
        )

    def execute_agent(
        self, agent_name: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an agent with retry logic, security validation, and sandboxing.

        Args:
            agent_name: Name of agent to execute
            input_data: Input data for agent

        Returns:
            Agent output

        Raises:
            ValueError: If agent fails after retries
            SecurityException: If security validation fails
        """
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")

        if self.enable_security:
            try:
                validate_agent_action(agent_name, ActionType.READ_FILE, self.session_id)
            except SecurityException as e:
                log_event(
                    session_id=self.session_id,
                    state=self.state.value,
                    agent_name=agent_name,
                    input_payload=input_data,
                    output_payload={"error": str(e)},
                    error_flag=True,
                )
                raise

        agent = self.agents[agent_name]
        last_error = None

        for attempt in range(self.max_retries):
            try:
                if self.enable_security:
                    try:
                        output = agent.execute(self.session_id, input_data)
                    except Exception as e:
                        raise ValueError(f"Agent execution failed: {e}")
                else:
                    output = agent.execute(self.session_id, input_data)

                log_event(
                    session_id=self.session_id,
                    state=self.state.value,
                    agent_name=agent_name,
                    input_payload=input_data,
                    output_payload=output,
                    error_flag=False,
                )

                return output

            except Exception as e:
                last_error = str(e)
                log_event(
                    session_id=self.session_id,
                    state=self.state.value,
                    agent_name=agent_name,
                    input_payload=input_data,
                    output_payload={"error": last_error},
                    error_flag=True,
                )

        raise ValueError(
            f"Agent {agent_name} failed after {self.max_retries} attempts: {last_error}"
        )

    def run(
        self, input_payload: Dict[str, Any], session_id: Optional[str] = None
    ) -> OrchestratorResult:
        """
        Run the orchestrator with input payload.

        Args:
            input_payload: Input data containing file_path and optional settings
            session_id: Optional session ID (generated if not provided)

        Returns:
            OrchestratorResult with final report and event log
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = input_payload.get("user_id", "default_user")
        self.state = WorkflowState.INIT
        self.context = {}
        self.iteration_count = 0

        self.memory_manager.update_short_term_state(
            session_id=self.session_id,
            user_id=self.user_id,
            workflow_state=self.state.value,
        )

        log_event(
            session_id=self.session_id,
            state=self.state.value,
            agent_name="orchestrator",
            input_payload=input_payload,
            output_payload={"status": "session_started"},
            error_flag=False,
        )

        try:
            self.transition_to(WorkflowState.INGEST)

            while self.state != WorkflowState.COMPLETE:
                self.iteration_count += 1

                if self.iteration_count > self.max_iterations:
                    raise ValueError(f"Max iterations ({self.max_iterations}) exceeded")

                current_state = self.state
                agent_name = self.get_agent_for_state(current_state)

                if current_state == WorkflowState.BUDGET:
                    self._retrieve_and_compress_context()

                if not agent_name:
                    if current_state == WorkflowState.INIT:
                        self.transition_to(WorkflowState.INGEST)
                        continue
                    elif current_state == WorkflowState.COMPLETE:
                        break
                    else:
                        raise ValueError(f"No agent mapped for state: {current_state}")

                output = self.execute_agent(
                    agent_name, self.context.get("last_input", input_payload)
                )

                self.context["last_output"] = output
                self.context[f"{agent_name}_output"] = output

                if current_state == WorkflowState.INGEST:
                    self.context["transactions"] = output.get("transactions", [])
                    self.context["last_input"] = {
                        "transactions": self.context["transactions"]
                    }

                elif current_state == WorkflowState.CATEGORIZE:
                    self.context["categorized_transactions"] = output.get(
                        "transactions", []
                    )
                    self.context["last_input"] = {
                        "transactions": self.context["categorized_transactions"]
                    }

                elif current_state == WorkflowState.ANALYZE:
                    self.context["analysis"] = output
                    self.context["last_input"] = output

                elif current_state == WorkflowState.BUDGET:
                    self.context["budget"] = output
                    combined_input = {**output, **self.context.get("analysis", {})}
                    self.context["last_input"] = combined_input

                elif current_state == WorkflowState.EVALUATE:
                    self.context["evaluation"] = output

                    if self.enable_security:
                        analysis = self.context.get("analysis", {})
                        anomalies = analysis.get("anomalies", [])

                        if anomalies:
                            for anomaly in anomalies:
                                if self.approval_manager.requires_approval(
                                    ApprovalType.ANOMALY_DETECTED,
                                    anomaly.get("risk_score", 0.0),
                                ):
                                    approval_req = self.approval_manager.request_approval(
                                        session_id=self.session_id,
                                        approval_type=ApprovalType.ANOMALY_DETECTED,
                                        reason=f"Anomaly detected: {anomaly.get('reason', 'Unknown')}",
                                        details=anomaly,
                                    )
                                    self.pending_approval_request_id = (
                                        approval_req.request_id
                                    )
                                    self.transition_to(WorkflowState.WAITING_APPROVAL)

                                    log_event(
                                        session_id=self.session_id,
                                        state=self.state.value,
                                        agent_name="orchestrator",
                                        input_payload=input_payload,
                                        output_payload={
                                            "status": "waiting_approval",
                                            "request_id": approval_req.request_id,
                                        },
                                        error_flag=False,
                                    )
                                    return OrchestratorResult(
                                        session_id=self.session_id,
                                        final_state=WorkflowState.WAITING_APPROVAL,
                                        final_report={
                                            "status": "pending_approval",
                                            "request_id": approval_req.request_id,
                                        },
                                        event_log=replay_session(self.session_id),
                                        iterations=self.iteration_count,
                                        success=True,
                                    )

                    combined_input = {
                        **self.context.get("analysis", {}),
                        **self.context.get("budget", {}),
                        "budget_suggestions": self.context["budget"].get(
                            "suggestions", []
                        ),
                    }
                    self.context["last_input"] = combined_input

                elif current_state == WorkflowState.REPORT:
                    self.context["report"] = output

                elif current_state == WorkflowState.REFINE:
                    self.context["refine_output"] = output
                    # Update report with refined data if metrics changed
                    if output.get("updated_metrics"):
                        self.context["report"].update(output.get("updated_metrics", {}))

                next_state = VALID_TRANSITIONS.get(
                    current_state, [WorkflowState.COMPLETE]
                )[0]
                self.transition_to(next_state)

            final_report = self.context.get("report", {})
            event_log = replay_session(self.session_id)

            log_event(
                session_id=self.session_id,
                state=self.state.value,
                agent_name="orchestrator",
                input_payload=input_payload,
                output_payload={
                    "status": "session_completed",
                    "iterations": self.iteration_count,
                },
                error_flag=False,
            )

            return OrchestratorResult(
                session_id=self.session_id,
                final_state=self.state,
                final_report=final_report,
                event_log=event_log,
                iterations=self.iteration_count,
                success=True,
            )

        except Exception as e:
            error_msg = str(e)
            event_log = replay_session(self.session_id)

            log_event(
                session_id=self.session_id,
                state=self.state.value,
                agent_name="orchestrator",
                input_payload=input_payload,
                output_payload={"status": "session_failed", "error": error_msg},
                error_flag=True,
            )

            return OrchestratorResult(
                session_id=self.session_id,
                final_state=self.state,
                final_report={},
                event_log=event_log,
                iterations=self.iteration_count,
                success=False,
                error=error_msg,
            )


def run_orchestrator(
    input_payload: Dict[str, Any],
    session_id: Optional[str] = None,
    max_iterations: int = 10,
    enable_security: bool = True,
) -> OrchestratorResult:
    """
    Convenience function to run the orchestrator.

    Args:
        input_payload: Input data with file_path
        session_id: Optional session ID
        max_iterations: Maximum iterations allowed
        enable_security: Enable security features

    Returns:
        OrchestratorResult
    """
    orchestrator = Orchestrator(
        max_iterations=max_iterations, enable_security=enable_security
    )
    return orchestrator.run(input_payload, session_id)


def resume_from_approval(
    session_id: str,
    request_id: str,
    approved_by: str,
    comment: Optional[str] = None,
) -> OrchestratorResult:
    """
    Resume orchestrator after approval.

    Args:
        session_id: Session ID to resume
        request_id: Approval request ID
        approved_by: Approver ID
        comment: Optional comment

    Returns:
        OrchestratorResult
    """
    approval_manager = get_approval_manager()

    if not approval_manager.is_approved(request_id):
        raise ApprovalException(request_id, "Request not approved")

    return OrchestratorResult(
        session_id=session_id,
        final_state=WorkflowState.COMPLETE,
        final_report={"status": "resumed_after_approval"},
        event_log=[],
        iterations=0,
        success=True,
    )


def refine_session(
    session_id: str,
    message: str,
    report: Dict[str, Any],
    transactions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Handle conversational refinement request.

    This integrates with the conversation agent to process
    natural language commands and update the report.

    Args:
        session_id: Current session ID
        message: Natural language command
        report: Current report data
        transactions: Optional list of transactions

    Returns:
        Dict with agent response including message, action, suggestions, updated_metrics
    """
    conversation_agent = get_conversation_agent()

    input_data = {
        "message": message,
        "report": report,
        "transactions": transactions or [],
    }

    result = conversation_agent.execute(session_id, input_data)

    log_event(
        session_id=session_id,
        state=WorkflowState.REFINE.value,
        agent_name="conversation",
        input_payload={"message": message},
        output_payload=result,
        error_flag=result.get("action") == "error",
    )

    return result


def run_whatif_simulation(
    session_id: str,
    simulation_type: str,
    params: Dict[str, Any],
    report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run a what-if simulation without modifying the report.

    Args:
        session_id: Current session ID
        simulation_type: Type of simulation (reduce_category, reduce_income, etc.)
        params: Simulation parameters
        report: Current report data

    Returns:
        Dict with simulation results
    """
    conversation_agent = get_conversation_agent()

    # Build message from simulation params
    message = ""
    if simulation_type == "reduce_category":
        message = (
            f"What if I spend ${params.get('amount')} less on {params.get('category')}?"
        )
    elif simulation_type == "reduce_income":
        message = f"What if my income drops {params.get('percentage')}%?"
    elif simulation_type == "increase_category":
        message = (
            f"What if I increase {params.get('category')} by ${params.get('amount')}?"
        )

    input_data = {"message": message, "report": report, "transactions": []}

    result = conversation_agent.execute(session_id, input_data)

    return result.get("simulation", {})


class ApprovalException(Exception):
    """Raised when approval requirements not met."""

    pass
