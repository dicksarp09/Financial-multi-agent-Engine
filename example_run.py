"""
Financial Agent Main Example
=============================

This file demonstrates the complete financial agent workflow
with all phases integrated.
"""

import json
from datetime import datetime

from orchestrator import run_orchestrator, WorkflowState
from logging_system import replay_session


def main():
    """Run the financial agent with sample transactions."""
    print("============================================================")
    print("FINANCIAL AGENT - PHASE 1 DEMONSTRATION")
    print("============================================================")

    # Load sample transactions
    try:
        with open("sample_transactions.json", "r") as f:
            transactions = json.load(f)
            print(f"\nSession ID: demo-session-001")
            print(f"Input: {{'file_path': 'sample_transactions.json'}}")
    except FileNotFoundError:
        transactions = [
            {"date": "2024-01-01", "description": "Salary", "amount": 5000},
            {"date": "2024-01-02", "description": "Apartment", "amount": -1500},
            {"date": "2024-01-05", "description": "Grocery Store", "amount": -150},
            {"date": "2024-01-10", "description": "Gas Station", "amount": -50},
            {"date": "2024-01-15", "description": "Electric Bill", "amount": -100},
            {"date": "2024-01-20", "description": "Restaurant", "amount": -75},
            {"date": "2024-02-01", "description": "Salary", "amount": 5000},
            {"date": "2024-02-02", "description": "Apartment", "amount": -1500},
            {"date": "2024-02-05", "description": "Grocery Store", "amount": -175},
            {"date": "2024-02-10", "description": "Car Insurance", "amount": -150},
            {"date": "2024-02-15", "description": "Internet Bill", "amount": -100},
            {"date": "2024-02-20", "description": "Gym Membership", "amount": -50},
            {"date": "2024-02-25", "description": "Cash Advance", "amount": -500},
        ]
        print(f"\nSession ID: demo-session-001")
        print(f"Input: {{'transactions': {len(transactions)} items}}")

    print("\n------------------------------------------------------------")
    print("Starting Orchestrator...")
    print("------------------------------------------------------------")

    # Run the orchestrator
    result = run_orchestrator(
        {"file_path": "sample_transactions.json"},
        enable_security=True,
    )

    print("\n============================================================")
    print("FINAL REPORT")
    print("============================================================")

    # Calculate totals from transactions if result is available
    total_income = 0
    total_expenses = 0
    category_breakdown = {}

    if hasattr(result, "final_report") and result.final_report:
        report = result.final_report
        if "total_income" in report:
            total_income = report["total_income"]
        if "total_expenses" in report:
            total_expenses = report["total_expenses"]
        if "category_breakdown" in report:
            category_breakdown = report["category_breakdown"]

    savings_rate = (
        ((total_income - total_expenses) / total_income * 100)
        if total_income > 0
        else 0
    )

    print(f"\nTotal Income:     ${total_income:,.2f}")
    print(f"Total Expenses:   ${total_expenses:,.2f}")
    print(f"Savings Rate:     {savings_rate:.1f}%")

    print("\n--- Category Breakdown ---")
    for category, amount in sorted(
        category_breakdown.items(), key=lambda x: -abs(x[1])
    ):
        print(f"  {category:<20} : ${amount:,.2f}")

    # Show budget suggestions if available
    if (
        hasattr(result, "final_report")
        and result.final_report
        and "budget_suggestions" in result.final_report
    ):
        print("\n--- Budget Suggestions ---")
        for suggestion in result.final_report.get("budget_suggestions", []):
            print(
                f"  {suggestion.get('category', 'Unknown'):<20} : ${suggestion.get('amount', 0):,.2f}"
            )

    # Show anomalies if detected
    if (
        hasattr(result, "final_report")
        and result.final_report
        and "anomalies" in result.final_report
    ):
        print("\n  *** Anomalies Detected ***")
        for anomaly in result.final_report.get("anomalies", []):
            print(f"  [!] {anomaly.get('description', 'Unknown')}")
            print(f"      Reason: {anomaly.get('reason', 'N/A')}")
            print(f"      Risk Score: {anomaly.get('risk_score', 0):.2f}")

    print("\n------------------------------------------------------------")
    print(f"Event Log Reference: {result.session_id}")
    print("------------------------------------------------------------")

    print("\n============================================================")
    print("EVENT LOG REPLAY")
    print("============================================================")

    # Replay the session events
    events = replay_session(result.session_id)

    for event in events:
        timestamp = event.get("timestamp", "")[:19]
        state = event.get("state", "")
        agent = event.get("agent", "unknown")
        error = event.get("error", False)

        error_str = "Error" if error else "False"
        print(f"\n[{timestamp}]")
        print(f"  State: {state}")
        print(f"  Agent: {agent}")
        print(f"  Error: {error_str}")

    print(f"\nTotal events logged: {len(events)}")

    print("\n[DEMO COMPLETED SUCCESSFULLY]")


if __name__ == "__main__":
    main()
