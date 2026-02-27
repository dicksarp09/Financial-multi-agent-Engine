import os
import json
from typing import List, Dict, Any, Optional
from enum import Enum

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq

# System prompt for autonomous agent
AUTONOMOUS_SYSTEM_PROMPT = """You are an Autonomous Financial Analysis Agent with reasoning capabilities.

Your capabilities:
1. Analyze financial data comprehensively
2. Plan multi-step budget optimizations
3. Execute budget changes automatically
4. Learn from user preferences
5. Set and work toward goals autonomously

When responding:
- Show your reasoning step-by-step
- Always explain the "why" behind recommendations
- Propose specific actionable changes
- If user approves, execute them automatically

You have access to these tools:
- analyze: Get comprehensive financial analysis
- plan: Create multi-step optimization plan
- execute: Apply budget changes
- monitor: Check for anomalies and alerts
- learn: Remember user preferences

Current context:
- Report data: {report_summary}
- Recent transactions: {recent_transactions}
- User preferences: {preferences}
- Active goals: {goals}

Conversation history:
{conversation_history}"""


class AgentState(dict):
    """State for the autonomous agent"""

    messages: List[Dict]
    current_task: str
    reasoning: List[str]
    plan: List[Dict]
    executed: List[Dict]
    goals: List[Dict]
    preferences: Dict


class AutonomousAgent:
    """
    Autonomous financial agent using LangGraph for orchestration.
    """

    def __init__(self, llm: Optional[Any] = None):
        # Initialize LLM
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")

        self.llm = llm or ChatGroq(
            model="openai/gpt-oss-120b", groq_api_key=api_key, temperature=0.3
        )

        # User preferences (would be stored in DB)
        self.preferences = {
            "response_style": "concise",  # concise or detailed
            "preferred_categories": [],
            "avoid_categories": [],
            "approval_needed": True,  # Need approval before changes
            "auto_execute": False,
        }

        # Active goals
        self.goals = []

        # Build the agent graph
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build LangGraph workflow"""

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze", self.analyze_node)
        workflow.add_node("reason", self.reasoning_node)
        workflow.add_node("plan", self.planning_node)
        workflow.add_node("execute", self.execution_node)
        workflow.add_node("monitor", self.monitoring_node)

        # Define edges
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "reason")
        workflow.add_edge("reason", "plan")
        workflow.add_edge("plan", "execute")

        # Conditional: go to monitor or end
        workflow.add_conditional_edges(
            "execute", self.should_continue, {"continue": "monitor", "end": END}
        )

        return workflow.compile()

    def should_continue(self, state: AgentState) -> str:
        """Decide whether to continue monitoring or end"""
        if state.get("current_task") == "monitor":
            return "continue"
        return "end"

    def analyze_node(self, state: AgentState) -> AgentState:
        """Analyze current financial state"""
        state["reasoning"].append("Analyzing current financial state...")
        return state

    def reasoning_node(self, state: AgentState) -> AgentState:
        """Generate multi-step reasoning"""
        reasoning = state.get("reasoning", [])

        # Get last user message
        last_msg = None
        for msg in reversed(state.get("messages", [])):
            if msg.get("role") == "user":
                last_msg = msg.get("content", "")
                break

        if last_msg:
            # Generate reasoning steps
            reasoning.append(f"User request: {last_msg}")
            reasoning.append("Breaking down into actionable steps...")
            reasoning.append("Evaluating current budget allocation...")

        state["reasoning"] = reasoning
        return state

    def planning_node(self, state: AgentState) -> AgentState:
        """Create optimization plan"""
        plan = state.get("plan", [])

        # Generate plan based on request
        last_msg = ""
        for msg in reversed(state.get("messages", [])):
            if msg.get("role") == "user":
                last_msg = msg.get("content", "").lower()
                break

        # Parse what user wants
        if "cut" in last_msg or "reduce" in last_msg or "save" in last_msg:
            plan.append(
                {
                    "step": 1,
                    "action": "analyze_current",
                    "description": "Analyze current spending categories",
                }
            )
            plan.append(
                {
                    "step": 2,
                    "action": "identify_opportunities",
                    "description": "Identify areas to reduce",
                }
            )
            plan.append(
                {
                    "step": 3,
                    "action": "calculate_impact",
                    "description": "Calculate savings impact",
                }
            )
            plan.append(
                {
                    "step": 4,
                    "action": "execute_or_propose",
                    "description": "Execute or propose changes",
                }
            )

        state["plan"] = plan
        return state

    def execution_node(self, state: AgentState) -> AgentState:
        """Execute planned actions"""
        executed = state.get("executed", [])

        # Execute plan items
        for item in state.get("plan", []):
            executed.append(
                {
                    "completed": True,
                    "action": item.get("action"),
                    "description": item.get("description"),
                }
            )

        state["executed"] = executed
        return state

    def monitoring_node(self, state: AgentState) -> AgentState:
        """Check for alerts/monitoring"""
        state["reasoning"].append("Checking for anomalies and alerts...")
        return state

    def set_goal(self, goal: str, target_value: float) -> None:
        """Set an autonomous goal"""
        self.goals.append({"goal": goal, "target": target_value, "status": "active"})

    def execute(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the autonomous agent workflow.
        """
        message = input_data.get("message", "")
        report = input_data.get("report", {})
        transactions = input_data.get("transactions", [])
        conversation_history = input_data.get("conversation_history", [])

        # Build initial state
        initial_state = AgentState(
            {
                "messages": conversation_history
                + [{"role": "user", "content": message}],
                "current_task": message,
                "reasoning": [],
                "plan": [],
                "executed": [],
                "goals": self.goals,
                "preferences": self.preferences,
            }
        )

        # Format context for LLM
        report_summary = self._format_report(report)
        recent_txns = self._format_transactions(transactions[:5])
        prefs = self._format_preferences()
        goals_text = self._format_goals()
        conv_hist = self._format_history(conversation_history)

        # Build system message
        system_msg = AUTONOMOUS_SYSTEM_PROMPT.format(
            report_summary=report_summary,
            recent_transactions=recent_txns,
            preferences=prefs,
            goals=goals_text,
            conversation_history=conv_hist,
        )

        # Use LLM for natural language response
        try:
            response = self.llm.invoke(
                [SystemMessage(content=system_msg), HumanMessage(content=message)]
            )

            # Parse response - check if auto-execute is enabled
            response_text = response.content

            # Check if this is an execute command
            if self.preferences.get("auto_execute"):
                # Auto-execute budget changes
                changes = self._parse_and_execute(message, report)
                if changes:
                    response_text = (
                        f"I've analyzed your request and made the following changes:\n\n"
                        + response_text
                    )

            return {
                "message": response_text,
                "reasoning": initial_state.get("reasoning", []),
                "plan": initial_state.get("plan", []),
                "executed": initial_state.get("executed", []),
                "action": "completed",
            }

        except Exception as e:
            return {
                "message": f"I encountered an error: {str(e)}",
                "reasoning": initial_state.get("reasoning", []),
                "plan": [],
                "executed": [],
                "action": "error",
            }

    def _parse_and_execute(self, message: str, report: Dict) -> List[Dict]:
        """Parse message and execute budget changes"""
        message_lower = message.lower()
        changes = []

        # Parse cut/reduce commands
        if "cut" in message_lower or "reduce" in message_lower:
            categories = [
                "housing",
                "food",
                "transportation",
                "utilities",
                "entertainment",
                "shopping",
                "healthcare",
            ]
            for cat in categories:
                if cat in message_lower:
                    # Extract percentage
                    import re

                    pct_match = re.search(r"(\d+)\s*%", message)
                    if pct_match:
                        pct = int(pct_match.group(1)) / 100
                        # Find current amount
                        for c in report.get("category_breakdown", []):
                            if c.get("category", "").lower() == cat:
                                old_amt = c.get("amount", 0)
                                new_amt = old_amt * (1 - pct)
                                changes.append(
                                    {
                                        "category": cat.title(),
                                        "old": old_amt,
                                        "new": new_amt,
                                        "action": "cut",
                                    }
                                )

        return changes

    def _format_report(self, report: Dict) -> str:
        if not report:
            return "No data available"

        lines = []
        lines.append(f"Income: ${report.get('total_income', 0):,.2f}")
        lines.append(f"Expenses: ${report.get('total_expenses', 0):,.2f}")
        lines.append(f"Savings Rate: {report.get('savings_rate', 0):.1f}%")
        lines.append(f"Risk Score: {report.get('risk_score', 0):.1f}")

        return "\n".join(lines)

    def _format_transactions(self, txns: List[Dict]) -> str:
        if not txns:
            return "No transactions"
        return ", ".join([f"{t.get('description')}: ${t.get('amount')}" for t in txns])

    def _format_preferences(self) -> str:
        return json.dumps(self.preferences)

    def _format_goals(self) -> str:
        if not self.goals:
            return "No active goals"
        return ", ".join([f"{g.get('goal')} ({g.get('target')})" for g in self.goals])

    def _format_history(self, history: List[Dict]) -> str:
        if not history:
            return "No previous conversation"
        return "\n".join(
            [f"{m.get('role', 'user')}: {m.get('message', '')}" for m in history[-5:]]
        )


# Legacy method for backward compatibility
def process_autonomous(
    message: str,
    report: Optional[Dict] = None,
    transactions: List[Dict] = [],
    conversation_history: List[Dict] = [],
) -> Dict[str, Any]:
    """Process message through autonomous agent"""
    agent = AutonomousAgent()

    input_data = {
        "message": message,
        "report": report or {},
        "transactions": transactions,
        "conversation_history": conversation_history,
    }

    return agent.execute("session", input_data)


# Singleton
_autonomous_agent: Optional[AutonomousAgent] = None


def get_autonomous_agent() -> AutonomousAgent:
    global _autonomous_agent
    if _autonomous_agent is None:
        _autonomous_agent = AutonomousAgent()
    return _autonomous_agent
