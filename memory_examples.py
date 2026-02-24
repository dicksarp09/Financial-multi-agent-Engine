"""
Memory Examples - Demonstrates PHASE 3 Memory & Context Features
==============================================================

This file demonstrates:
1. Short-Term Memory - Session-scoped state
2. Long-Term Memory - Transaction/summary storage
3. Retrieval Agent - Historical context retrieval
4. Context Compression - LLM-ready summaries
5. User Isolation - Cross-user protection
"""

from memory.memory_manager import (
    get_memory_manager,
    MonthlySummary,
    TransactionRecord,
    UserScopeViolation,
)
from memory.context_compressor import get_context_compressor, CompressedContext
from agents.retrieval_agent import RetrievalAgent, RetrievalRequest
from security.privilege_model import (
    get_privilege_model,
    validate_agent_action,
    ActionType,
    SecurityException,
)


def example_1_short_term_memory():
    """Example 1: Short-term memory operations."""
    print("\n1. Creating short-term memory for session test-session-001...")

    memory = get_memory_manager()
    session_id = "test-session-001"
    user_id = "user_demo"

    state = memory.update_short_term_state(
        session_id=session_id,
        user_id=user_id,
        workflow_state="INIT",
        current_transactions=[],
        agent_outputs={},
    )
    print(f"   Created: {state.session_id}, state: {state.workflow_state}")

    print("\n2. Updating short-term memory...")
    state = memory.update_short_term_state(
        session_id=session_id,
        user_id=user_id,
        workflow_state="ANALYZE",
        current_transactions=[{"id": "tx1", "amount": -50}],
        agent_outputs={"analysis": {"total": 5000}},
    )
    print(f"   Updated state: {state.workflow_state}")
    print(f"   Transactions: {len(state.current_transactions)}")

    print("\n3. Retrieving short-term memory...")
    retrieved = memory.get_short_term_state(session_id, user_id)
    if retrieved:
        print(f"   State: {retrieved.workflow_state}")
        print(f"   Agent outputs: {retrieved.agent_outputs}")

    print("\n4. Clearing short-term memory...")
    cleared = memory.clear_short_term(session_id, user_id)
    print(f"   Cleared: {cleared}")


def example_2_long_term_memory():
    """Example 2: Long-term memory (transactions & summaries)."""
    print("\n1. Storing transactions...")

    memory = get_memory_manager()
    user_id = "demo_user"

    transactions = [
        TransactionRecord(
            user_id=user_id,
            session_id="ltm-session",
            transaction_id=f"txn_{i}",
            date="2024-02-10",
            description="Salary",
            amount=5000.0,
            category="Income",
            is_anomaly=False,
            risk_score=0.0,
            created_at="2024-02-10T00:00:00",
        )
        for i in range(3)
    ]

    count = 0
    for txn in transactions:
        if memory.store_transaction(txn):
            count += 1
    print(f"   Stored {count} transactions")

    print("\n2. Retrieving user transactions...")
    retrieved = memory.get_user_transactions(user_id, limit=10)
    print(f"   Retrieved {len(retrieved)} transactions")
    for txn in retrieved[:2]:
        print(f"     - {txn.date}: {txn.description} = ${txn.amount:.2f}")


def example_3_monthly_summaries():
    """Example 3: Monthly summaries."""
    print("\n1. Storing monthly summaries...")

    memory = get_memory_manager()
    user_id = "demo_user"

    summaries = [
        MonthlySummary(
            user_id=user_id,
            month="2024-02",
            total_income=5500.0,
            total_expense=3200.0,
            savings_rate=42.0,
            category_breakdown={
                "Housing": 1500,
                "Food": 600,
                "Transport": 300,
                "Utilities": 200,
                "Entertainment": 150,
                "Healthcare": 100,
                "Other": 350,
            },
            transaction_count=30,
            anomaly_count=1,
            risk_alerts=0,
            created_at="2024-02-28T23:59:59",
        ),
        MonthlySummary(
            user_id=user_id,
            month="2024-01",
            total_income=5000.0,
            total_expense=3500.0,
            savings_rate=30.0,
            category_breakdown={
                "Housing": 1500,
                "Food": 650,
                "Transport": 350,
                "Utilities": 250,
                "Entertainment": 200,
                "Healthcare": 150,
                "Other": 400,
            },
            transaction_count=28,
            anomaly_count=2,
            risk_alerts=1,
            created_at="2024-01-31T23:59:59",
        ),
    ]

    count = 0
    for s in summaries:
        if memory.store_monthly_summary(s):
            count += 1
    print(f"   Stored {count} monthly summaries")

    print("\n2. Retrieving monthly summaries...")
    retrieved = memory.get_monthly_summaries(user_id, months=6)
    print(f"   Retrieved {len(retrieved)} summaries")
    for s in retrieved:
        print(
            f"     - {s.month}: income=${s.total_income:.0f}, expense=${s.total_expense:.0f}, savings={s.savings_rate:.0f}%"
        )


def example_4_retrieval_agent():
    """Example 4: Retrieval agent for historical context."""
    print("\n1. Executing retrieval query (monthly trends)...")

    memory = get_memory_manager()
    retrieval = RetrievalAgent()
    user_id = "demo_user"

    # Store some data first
    for month in ["2024-01", "2024-02"]:
        summary = MonthlySummary(
            user_id=user_id,
            month=month,
            total_income=5000.0,
            total_expense=3500.0,
            savings_rate=30.0,
            category_breakdown={"Food": 500, "Housing": 1500, "Transport": 300},
            transaction_count=25,
            anomaly_count=1,
            risk_alerts=0,
            created_at=f"{month}-28T00:00:00",
        )
        memory.store_monthly_summary(summary)

    request = RetrievalRequest(
        user_id=user_id,
        session_id="retrieve-session",
        months=2,
        include_trends=True,
    )
    context = retrieval.retrieve_historical_context(request)

    print(f"   Months analyzed: {context.months_analyzed}")
    print(f"   Average income: ${context.average_income:.2f}")
    print(f"   Average expense: ${context.average_expense:.2f}")
    print(f"   Savings trend: {context.savings_trend * 100:.1f}%")
    print(f"   Category trends: {context.category_trends}")


def example_5_context_compression():
    """Example 5: Context compression for LLM."""
    print("\n1. Compressing context for LLM...")

    compressor = get_context_compressor()

    historical = {
        "average_income": 5250.0,
        "average_expense": 3350.0,
        "category_trends": {
            "Housing": 3000.0,
            "Food": 950.0,
            "Transport": 550.0,
            "Utilities": 400,
            "Entertainment": 300,
        },
        "savings_trend": 0.36,
        "risk_alerts_count": 0,
        "period_start": "2024-01",
        "period_end": "2024-02",
    }

    compressed = compressor.compress_historical_context(
        user_id="demo_user",
        session_id="compress-session",
        historical_data=historical,
    )

    print("\nCompressed Context:")
    print(f"  avg_income: ${compressed.avg_income:.2f}")
    print(f"  avg_expense: ${compressed.avg_expense:.2f}")
    print(f"  top_categories: {compressed.top_categories}")
    print(f"  savings_trend: {compressed.savings_trend * 100:.1f}%")
    print(f"  risk_flags_count: {compressed.risk_flags_count}")
    print(f"  months_analyzed: 2")

    print("\n2. Token estimation...")
    tokens = compressor.estimate_tokens(compressed)
    print(f"   Estimated tokens: {tokens}")


def example_6_cross_user_access():
    """Example 6: User isolation and scoping."""
    print("\n1. Creating memory for user A...")

    memory = get_memory_manager()
    session_id = "shared-session"

    memory.update_short_term_state(
        session_id=session_id,
        user_id="user_a",
        workflow_state="COMPLETE",
        current_transactions=[],
        agent_outputs={},
    )
    print(f"   Created session for user_a")

    print("\n2. User B attempting to access user A's session...")
    try:
        memory.get_short_term_state(session_id, "user_b")
        print("   ERROR: Should have been blocked!")
    except UserScopeViolation as e:
        print(f"   [REJECTED] {e}")
        print(f"   Cross-user access correctly blocked!")

    print("\n3. Cleaning up...")
    memory.clear_short_term(session_id, "user_a")
    print(f"   Cleaned up test data")


def example_7_retrieval_privilege():
    """Example 7: Retrieval agent privilege enforcement."""
    print("\n1. Checking retrieval agent permissions...")

    priv = get_privilege_model()

    perms = priv.get_agent_permission("retrieval")
    print(f"   can_read_files: {perms.can_read_files}")
    print(f"   can_write_files: {perms.can_write_files}")
    print(f"   can_write_db: {perms.can_write_db}")
    print(f"   can_call_llm: {perms.can_call_llm}")
    print(f"   can_use_retrieval: {perms.can_use_retrieval}")

    print("\n2. Testing unauthorized action (retrieval trying to write)...")
    try:
        validate_agent_action("retrieval", ActionType.WRITE_DB, "test-session")
        print("   ERROR: Should have been blocked!")
    except SecurityException as e:
        print(f"   [BLOCKED] HIGH: Agent lacks permission for 'write_db'")

    print("\n3. Testing authorized action (retrieval using retrieval)...")
    try:
        validate_agent_action("retrieval", ActionType.USE_RETRIEVAL, "test-session")
        print(f"   [ALLOWED] Retrieval access: True")
    except SecurityException as e:
        print(f"   [BLOCKED] {e}")


def main():
    """Run all memory examples."""
    print("############################################################")
    print("# MEMORY ARCHITECTURE DEMONSTRATION - PHASE 3")
    print("############################################################")

    example_1_short_term_memory()
    example_2_long_term_memory()
    example_3_monthly_summaries()
    example_4_retrieval_agent()
    example_5_context_compression()
    example_6_cross_user_access()
    example_7_retrieval_privilege()

    print("\n############################################################")
    print("# ALL EXAMPLES COMPLETED")
    print("############################################################")


if __name__ == "__main__":
    main()
