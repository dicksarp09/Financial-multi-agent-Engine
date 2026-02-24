from typing import Dict, Any, List
from dataclasses import asdict
from schemas import TransactionRecord
from compute.aggregation import (
    compute_totals,
    compute_category_breakdown,
    compute_savings_rate,
)
from compute.anomaly_detection import detect_outliers
from compute.risk_scoring import compute_batch_risk_scores


class AnalysisAgent:
    """Agent responsible for analyzing transactions."""

    def __init__(self):
        self.name = "analysis_agent"

    def analyze(self, transactions: List[TransactionRecord]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis on transactions.

        Args:
            transactions: List of categorized transactions

        Returns:
            Analysis results including totals, breakdown, and anomalies
        """
        totals = compute_totals(transactions)
        breakdown = compute_category_breakdown(transactions)
        savings_rate = compute_savings_rate(totals.total_income, totals.total_expense)

        anomaly_result = detect_outliers(transactions, method="iqr")

        risk_scores = compute_batch_risk_scores(transactions)
        high_risk_transactions = [r for r in risk_scores if r.risk_score > 0.5]

        return {
            "total_income": totals.total_income,
            "total_expense": totals.total_expense,
            "net_savings": totals.net_savings,
            "savings_rate": savings_rate,
            "category_breakdown": breakdown.breakdown,
            "anomalies": [a.model_dump() for a in anomaly_result.anomalies],
            "high_risk_count": len(high_risk_transactions),
            "risk_scores": [asdict(r) for r in risk_scores[:10]],
        }

    def execute(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the analysis agent.

        Args:
            session_id: Session identifier
            input_data: Input data containing transactions

        Returns:
            Analysis results
        """
        transactions_data = input_data.get("transactions", [])

        transactions = [
            TransactionRecord(
                date=t["date"],
                description=t["description"],
                amount=t["amount"],
                category=t.get("category"),
                transaction_id=t.get("transaction_id"),
            )
            for t in transactions_data
        ]

        analysis = self.analyze(transactions)

        return analysis
