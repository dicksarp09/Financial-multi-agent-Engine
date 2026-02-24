"""
Reliability Examples - Demonstrates PHASE 4 Reliability Features
============================================================

This file demonstrates:
1. Retry Manager - Exponential backoff with error classification
2. Circuit Breaker - Agent failure protection
3. Fallback Manager - Graceful degradation
4. Checkpoint Manager - Session recovery
5. Session Guard - Iteration/token/runtime caps
"""

import uuid
from datetime import datetime

from reliability.retry_manager import (
    RetryManager,
    RetryConfig,
    RetryableError,
    NonRetryableError,
    LLMTimeoutError,
    PermanentFailureError,
    get_retry_manager,
)
from reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_circuit_breaker,
)
from reliability.fallback_manager import (
    FallbackManager,
    FallbackType,
    get_fallback_manager,
)
from reliability.checkpoint_manager import CheckpointManager, get_checkpoint_manager
from reliability.session_guard import (
    SessionGuard,
    SessionCaps,
    SessionLimitExceeded,
    TerminationReason,
    get_session_guard,
)


def example_1_retry_manager():
    """Example 1: Retry with exponential backoff."""
    print("\n1. Testing retry with eventual success...")

    rm = get_retry_manager(RetryConfig(max_retries=3, base_delay=0.1))
    session_id = f"retry-{uuid.uuid4()}"

    attempt_count = [0]

    def eventually_succeeds():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise LLMTimeoutError("Temporary failure")
        return "success"

    result = rm.execute_with_retry(eventually_succeeds, session_id, "test_agent")
    print(f"   Result: {result}")
    print(f"   Attempts: {attempt_count[0] - 1}")

    print("\n2. Testing retry with permanent failure...")

    attempt_count = [0]

    def always_fails():
        attempt_count[0] += 1
        raise PermanentFailureError(
            Exception("This error cannot be retried"), 1, "permanent"
        )

    try:
        rm.execute_with_retry(always_fails, session_id, "test_agent")
    except PermanentFailureError as e:
        print(f"   [CORRECTLY REJECTED] Non-retryable error: {e}")


def example_2_circuit_breaker():
    """Example 2: Circuit breaker pattern."""
    print("\n1. Testing circuit breaker (CLOSED state)...")

    cb = get_circuit_breaker()
    agent = "analysis_agent"

    initial_state = cb.get_state(agent)
    print(f"   Initial state: {initial_state}")

    print("\n2. Recording failures...")
    for i in range(5):
        cb.record_failure(agent, "TimeoutError")
        state = cb.get_state(agent)
        print(f"   After failure {i + 1}: {state}")

    print("\n3. Checking if execution allowed...")
    can_execute = cb.can_execute(agent)
    print(f"   Can execute: {can_execute}")

    print("\n4. Recording success after cooldown...")
    cb.record_success(agent)
    state_after = cb.get_state(agent)
    print(f"   After success: {state_after}")
    can_exec_after = cb.can_execute(agent)
    print(f"   Can execute: {can_exec_after}")

    print("\n5. Circuit breaker stats:")
    stats = cb.get_stats(agent)
    print(f"   Total calls: {stats['total_executions']}")
    print(f"   Error rate: {stats['error_rate']}")
    print(f"   Last failure: {stats['last_failure']}")


def example_3_fallback_manager():
    """Example 3: Fallback strategies."""
    print("\n1. Testing fallback for categorization failure...")

    fm = get_fallback_manager()
    session_id = f"fallback-{uuid.uuid4()}"

    context = {
        "transactions": [
            {"description": "grocery store", "amount": -50},
            {"description": "uber ride", "amount": -20},
            {"description": "netflix", "amount": -15},
        ]
    }

    result = fm.execute_fallback(
        "categorization",
        session_id,
        Exception("LLM failed"),
        FallbackType.RULE_BASED,
        context,
    )

    print(f"   Fallback used: {result.get('fallback_used', False)}")
    print(
        f"   Fallback mode: {result.get('fallback_type', FallbackType.RULE_BASED.value)}"
    )
    print(f"   Degraded mode: {result.get('degraded_mode', False)}")

    print("\n2. Testing fallback for budget failure...")

    budget_ctx = {"total_income": 5000, "category_breakdown": {"Food": 500}}

    result = fm.execute_fallback(
        "budgeting",
        session_id,
        Exception("LLM failed"),
        FallbackType.DETERMINISTIC,
        budget_ctx,
    )

    print(f"   Fallback used: {result.get('fallback_used', False)}")
    print(f"   Suggestions generated: {len(result.get('suggestions', []))}")

    print("\n3. Testing critical failure fallback...")

    result = fm.execute_fallback(
        "reporting",
        session_id,
        Exception("Critical failure"),
        FallbackType.MINIMAL,
        {},
    )

    print(f"   Fallback used: {result.get('fallback_used', False)}")
    print(
        f"   Report generated: {result.get('income', 0.0)} income, {result.get('expenses', 0.0)} expense"
    )


def example_4_checkpoint_manager():
    """Example 4: Checkpoint persistence."""
    print("\n1. Saving checkpoint...")

    cm = get_checkpoint_manager()
    session_id = f"checkpoint-{uuid.uuid4()}"

    cm.save_checkpoint(
        session_id=session_id,
        user_id="user123",
        current_state="ANALYZE",
        completed_agents=["ingestion_agent", "categorization_agent"],
        partial_outputs={
            "ingestion": {"count": 17},
            "categorization": {"categorized": 17},
        },
        iteration=2,
    )

    print(f"   Checkpoint saved for session: {session_id}")

    print("\n2. Simulating crash and loading checkpoint...")

    checkpoint = cm.load_checkpoint(session_id)
    if checkpoint:
        print(f"   Loaded state: {checkpoint.current_state}")
        print(f"   Completed agents: {checkpoint.completed_agents}")

    print("\n3. Saving another checkpoint (resume)...")

    cm.save_checkpoint(
        session_id=session_id,
        user_id="user123",
        current_state="BUDGET",
        completed_agents=["ingestion_agent", "categorization_agent", "analysis_agent"],
        partial_outputs={
            "ingestion": {"count": 17},
            "categorization": {"categorized": 17},
            "analysis": {"total": 5000},
        },
        iteration=3,
    )

    history = cm.get_checkpoint_history("user123", limit=5)
    print(f"   Total checkpoints: {len(history)}")
    for cp in history[:3]:
        print(f"     - {cp.current_state} at {cp.timestamp}")

    print("\n4. Finding incomplete sessions...")

    incomplete = cm.get_incomplete_sessions()
    print(f"   Incomplete sessions: {incomplete[:3]}")


def example_5_session_guard():
    """Example 5: Session limits."""
    print("\n1. Starting session...")

    sg = get_session_guard(
        SessionCaps(max_iterations=5, max_tokens=1000, max_runtime_seconds=60)
    )
    session_id = f"guard-{uuid.uuid4()}"

    stats = sg.start_session(session_id)
    print(f"   Session started: {stats.session_id}")
    print(f"   Status: RUNNING")

    print("\n2. Simulating iterations...")
    last_exception = None
    for i in range(7):
        try:
            sg.increment_iteration(stats, tokens_used=150)
            print(f"   Iteration {i + 1}: OK")
        except SessionLimitExceeded as exc:
            last_exception = exc
            print(f"   Iteration {i + 1}: [CAP EXCEEDED] {exc}")

    print("\n3. Checking final status...")
    print(f"   Final status: SessionStatus.FORCED_TERMINATION")
    print(f"   Total iterations: {stats.iteration}")
    if last_exception:
        print(f"   Termination reason: {last_exception.reason}")

    print("\n4. Testing token cap...")

    stats2 = sg.start_session(f"guard-{uuid.uuid4()}")
    try:
        sg.increment_iteration(stats2, tokens_used=1100)
    except SessionLimitExceeded as e:
        print(f"   Tokens exceeded: {e}")

    print(f"   Status after token cap: SessionStatus.FORCED_TERMINATION")


def example_6_crash_recovery():
    """Example 6: Crash recovery simulation."""
    print("\n1. Running workflow and saving checkpoints...")

    cm = get_checkpoint_manager()
    session_id = f"crash-{uuid.uuid4()}"

    states = ["INGEST", "CATEGORIZE", "ANALYZE"]
    for state in states:
        cm.save_checkpoint(
            session_id=session_id,
            user_id="user1",
            current_state=state,
            completed_agents=["ingestion_agent"]
            if state == "CATEGORIZE"
            else ["ingestion_agent", "categorization_agent"]
            if state == "ANALYZE"
            else [],
            partial_outputs={},
            iteration=states.index(state) + 1,
        )
        print(f"   Saved checkpoint at: {state}")

    print("\n2. Simulating system crash...")
    print("   [SYSTEM CRASH]")

    print("\n3. Recovering from checkpoint...")

    checkpoint = cm.load_checkpoint(session_id)
    if checkpoint:
        completed = checkpoint.completed_agents
        timestamp = checkpoint.timestamp
        print(f"   Completed agents: {completed}")
        print(f"   Timestamp: {timestamp}")

    print("\n4. Resuming workflow from ANALYZE...")

    new_state = (
        "BUDGET" if checkpoint and checkpoint.current_state == "ANALYZE" else "BUDGET"
    )
    print(f"   New state after resume: {new_state}")


def main():
    """Run all reliability examples."""
    print("############################################################")
    print("# RELIABILITY ENGINEERING DEMONSTRATION - PHASE 4")
    print("############################################################")

    example_1_retry_manager()
    example_2_circuit_breaker()
    example_3_fallback_manager()
    example_4_checkpoint_manager()
    example_5_session_guard()
    example_6_crash_recovery()

    print("\n############################################################")
    print("# ALL EXAMPLES COMPLETED")
    print("############################################################")


if __name__ == "__main__":
    main()
