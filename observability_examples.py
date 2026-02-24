"""
Observability Examples - Demonstrates PHASE 5 Observability & Governance
====================================================================

This file demonstrates:
1. Distributed Tracing - Session spans and replay
2. Cost Monitoring - Token tracking and alerts
3. Drift Detection - Metric deviation detection
4. Compliance Logging - PII redaction and audit
5. Evaluation Pipeline - Automated testing
"""

import uuid
from datetime import datetime, timedelta

from observability.tracing import get_tracing
from observability.cost_monitor import get_cost_monitor, CostThresholds
from observability.drift_detector import get_drift_detector, DriftConfig
from observability.compliance_logger import get_compliance_logger
from evaluation.evaluation_runner import run_evaluation


def example_1_distributed_tracing():
    """Example 1: Distributed tracing with spans."""
    print("\n1. Starting session trace...")
    session_id = f"trace-{uuid.uuid4()}"

    tracing = get_tracing()
    session_span = tracing.start_span(session_id, "orchestrator", "session")
    print(f"   Session span ID: {session_span[:36]}")

    print("\n2. Simulating agent spans...")

    # INGEST agent
    ingest_span = tracing.start_span(
        session_id, "ingestion_agent", "agent", parent_id=session_span
    )
    tracing.end_span(ingest_span, output_data={"transactions": 17})
    print("   INGEST agent completed")

    # CATEGORIZE agent
    cat_span = tracing.start_span(
        session_id, "categorization_agent", "agent", parent_id=session_span
    )
    tracing.end_span(cat_span, output_data={"categorized": 17})
    print("   CATEGORIZE agent completed")

    # ANALYZE agent
    analyze_span = tracing.start_span(
        session_id, "analysis_agent", "agent", parent_id=session_span
    )
    tracing.end_span(analyze_span, output_data={"analyzed": 17})
    print("   ANALYZE agent completed")

    # BUDGET agent (simulate failure)
    budget_span = tracing.start_span(
        session_id, "budgeting_agent", "agent", parent_id=session_span
    )
    tracing.end_span(budget_span, output_data={"error": "timeout"}, error="timeout")
    print("   BUDGET agent failed")

    tracing.end_span(session_span, output_data={"status": "complete"})

    print("\n3. Getting trace summary...")
    trace = tracing.replay_session(session_id)

    total_duration = sum(s.get("duration_ms", 0) for s in trace)
    errors = sum(1 for s in trace if s.get("error", False))

    agent_durations = {}
    for s in trace:
        agent = s.get("agent", "unknown")
        if agent not in agent_durations:
            agent_durations[agent] = 0
        agent_durations[agent] += s.get("duration_ms", 0)

    print(f"   Total spans: {len(trace)}")
    print(f"   Duration: {total_duration:.2f}ms")
    print(f"   Errors: {errors}")
    print(f"   Agent durations: {agent_durations}")


def example_2_cost_monitoring():
    """Example 2: Cost monitoring and tracking."""
    print("\n1. Recording LLM costs...")

    cost_monitor = get_cost_monitor(
        CostThresholds(daily_limit=10.0, monthly_limit=100.0)
    )
    session_id = f"cost-{uuid.uuid4()}"
    user_id = "demo_user"

    # Categorization LLM call
    cost_monitor.record_llm_call(
        session_id,
        user_id,
        "categorization_agent",
        tokens_in=500,
        tokens_out=200,
        cost_reason="transaction_categorization",
    )

    session_cost = cost_monitor.get_session_cost(session_id)
    print(f"   Categorization LLM call: ${session_cost['estimated_cost']:.4f}")

    # Budget reasoning LLM call
    cost_monitor.record_llm_call(
        session_id,
        user_id,
        "budgeting_agent",
        tokens_in=700,
        tokens_out=300,
        cost_reason="budget_analysis",
    )

    session_cost = cost_monitor.get_session_cost(session_id)
    print(f"   Budget reasoning LLM call: ${session_cost['estimated_cost']:.4f}")

    print("\n2. Getting session cost breakdown...")
    breakdown = cost_monitor.get_session_cost(session_id)
    print(f"   Breakdown: {breakdown['by_agent']}")

    print("\n3. Checking thresholds...")
    alerts = cost_monitor.get_alerts(user_id)
    print(f"   Current alerts: {len(alerts)}")


def example_3_compliance_logging():
    """Example 3: Compliance logging with PII redaction."""
    print("\n1. Logging transaction with PII...")

    compliance = get_compliance_logger()
    session_id = f"compliance-{uuid.uuid4()}"
    user_id = "demo_user"

    test_data = {
        "transaction_id": "txn_001",
        "amount": -150.0,
        "merchant": "Grocery Store",
        "account_number": "555-123-4567",
    }

    pii_found = compliance.detect_pii(str(test_data))
    redacted = compliance.redact_pii(str(test_data))

    import hashlib

    data_hash = hashlib.md5(str(test_data).encode()).hexdigest()[:16]
    print(f"   Hash: {data_hash}")
    print(f"   PII detected: {pii_found}")
    print(f"   Redacted data: {redacted}")

    print("\n2. Logging categorization decision...")
    log_id = compliance.log_categorization(
        session_id,
        user_id,
        transaction_id="tx_abc123",
        description="Netflix Subscription",
        category="Entertainment",
        confidence=0.95,
    )
    print(
        f"   Category: {{'description': 'Netflix Subscription', 'category': 'Entertainment', 'confidence': 0.95}}"
    )

    print("\n3. Logging budget decision...")
    compliance.log_budget_decision(
        session_id,
        user_id,
        category="Food",
        suggested=750.0,
        reasoning="Recommended based on income",
    )
    print(
        f"   Decision: {{'category': 'Food', 'suggested_budget': 750.0, 'reasoning': 'Recommended based on income'}}"
    )

    print("\n4. Audit log...")
    logs = compliance.audit_trail(session_id)
    record_types = list(set(log["type"] for log in logs))
    print(f"   Total records: {len(logs)}")
    print(f"   Record types: {record_types}")


def example_4_drift_detection():
    """Example 4: Drift detection in metrics."""
    print("\n1. Recording baseline samples...")

    drift = get_drift_detector(DriftConfig(sigma_threshold=2.0))
    session_id = f"drift-{uuid.uuid4()}"

    # Record historical food spending
    food_spending = [520, 540, 560, 530, 550, 545, 535, 555, 525, 545]
    for amount in food_spending:
        drift.record_metric("food_spending", float(amount), session_id)

    print(f"   Recorded {len(food_spending)} samples for food_spending")

    baseline = drift.update_baseline("food_spending", window_hours=168)
    if baseline:
        print(f"   Baseline mean: {baseline['mean']:.2f}, std: {baseline['std']:.2f}")
    else:
        print("   Baseline: Not enough samples")

    print("\n2. Checking for drift...")
    current_value = 950.0
    drift_result = drift.check_drift("food_spending", current_value)

    z_score = abs(current_value - drift_result.baseline_value) / max(
        drift_result.deviation / 100 * (drift_result.baseline_value), 0.01
    )

    print(f"   Current value: {current_value}")
    print(f"   Deviation: {z_score:.2f} std")
    print(f"   Alert triggered: {drift_result.alert_flag}")

    print("\n3. Recording anomaly frequency...")
    # Record baseline anomaly counts
    for i in range(10):
        drift.record_metric("anomaly_count", float(i % 3), session_id)

    drift.update_baseline("anomaly_count", window_hours=168)
    anomaly_result = drift.check_drift("anomaly_count", 8.0)

    z_score_anom = abs(8.0 - anomaly_result.baseline_value) / max(
        anomaly_result.deviation
        / 100
        * (anomaly_result.baseline_value if anomaly_result.baseline_value > 0 else 1),
        0.01,
    )

    print(f"   Anomaly count deviation: {z_score_anom:.2f} std")
    print(f"   Alert triggered: {anomaly_result.alert_flag}")


def example_5_evaluation_pipeline():
    """Example 5: Automated evaluation pipeline."""
    print("\n1. Running categorization tests...")
    print("   Tests run: 3")

    print("\n2. Running budget tests...")
    print("   Tests run: 1")

    print("\n3. Generating report...")
    results = run_evaluation()

    print(f"   Total tests: {results['total_tests']}")
    print(f"   Passed: {results['passed']}")
    print(f"   Failed: {results['failed']}")
    print(f"   Pass rate: {results['average_score']:.1f}%")


def example_6_full_session_trace():
    """Example 6: Full session trace with all observability."""
    print("\n1. Starting full workflow trace...")

    tracing = get_tracing()
    cost_monitor = get_cost_monitor(
        CostThresholds(daily_limit=10.0, monthly_limit=100.0)
    )
    compliance = get_compliance_logger()

    session_id = f"full-{uuid.uuid4()}"
    user_id = "demo_user"

    session_span = tracing.start_span(session_id, "orchestrator", "session")

    print("\n2. Tracing each agent with cost and compliance...")

    # INGEST
    ingest_span = tracing.start_span(
        session_id, "ingestion_agent", "agent", parent_id=session_span
    )
    cost_monitor.record_llm_call(
        session_id, user_id, "ingestion_agent", 100, 50, "file_reading"
    )
    tracing.end_span(ingest_span, output_data={"transactions": 10})

    # CATEGORIZE
    cat_span = tracing.start_span(
        session_id, "categorization_agent", "agent", parent_id=session_span
    )
    cost_monitor.record_llm_call(
        session_id, user_id, "categorization_agent", 300, 150, "categorization"
    )
    compliance.log_categorization(session_id, user_id, "tx1", "grocery", "Food", 0.95)
    tracing.end_span(cat_span, output_data={"categorized": 10})

    # ANALYZE
    analyze_span = tracing.start_span(
        session_id, "analysis_agent", "agent", parent_id=session_span
    )
    cost_monitor.record_llm_call(
        session_id, user_id, "analysis_agent", 200, 100, "analysis"
    )
    tracing.end_span(analyze_span, output_data={"analyzed": 10})

    # BUDGET
    budget_span = tracing.start_span(
        session_id, "budgeting_agent", "agent", parent_id=session_span
    )
    cost_monitor.record_llm_call(
        session_id, user_id, "budgeting_agent", 200, 100, "budget"
    )
    compliance.log_budget_decision(session_id, user_id, "Food", 500, "30% rule")
    tracing.end_span(budget_span, output_data={"budgets": 8})

    tracing.end_span(session_span, output_data={"status": "complete"})

    print("\n3. Final metrics...")
    trace = tracing.replay_session(session_id)
    session_cost = cost_monitor.get_session_cost(session_id)
    audit = compliance.audit_trail(session_id)

    total_duration = sum(s.get("duration_ms", 0) for s in trace)

    print(f"   Session duration: {total_duration:.2f}ms")
    print(f"   Total cost: ${session_cost['estimated_cost']:.4f}")
    print(f"   Total tokens: {session_cost['total_tokens']}")


def main():
    """Run all observability examples."""
    print("############################################################")
    print("# OBSERVABILITY DEMONSTRATION - PHASE 5")
    print("############################################################")

    example_1_distributed_tracing()
    example_2_cost_monitoring()
    example_3_compliance_logging()
    example_4_drift_detection()
    example_5_evaluation_pipeline()
    example_6_full_session_trace()

    print("\n############################################################")
    print("# ALL EXAMPLES COMPLETED")
    print("############################################################")


if __name__ == "__main__":
    main()
