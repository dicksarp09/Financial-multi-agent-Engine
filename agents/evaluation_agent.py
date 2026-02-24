from typing import Dict, Any, List
from schemas import TransactionRecord, AnomalyAlert


class EvaluationAgent:
    """Agent responsible for evaluating financial health and risk."""

    def __init__(self):
        self.name = "evaluation_agent"

    def evaluate_financial_health(
        self,
        total_income: float,
        total_expense: float,
        savings_rate: float,
        anomalies: List[AnomalyAlert],
        high_risk_count: int,
    ) -> Dict[str, Any]:
        """
        Evaluate overall financial health.

        Args:
            total_income: Total income
            total_expense: Total expenses
            savings_rate: Savings rate percentage
            anomalies: List of detected anomalies
            high_risk_count: Count of high-risk transactions

        Returns:
            Financial health evaluation
        """
        health_score = 100.0
        issues: List[str] = []
        recommendations: List[str] = []

        if savings_rate < 0:
            health_score -= 30
            issues.append("Negative savings rate - spending exceeds income")
            recommendations.append("Reduce expenses or increase income immediately")
        elif savings_rate < 10:
            health_score -= 20
            issues.append("Low savings rate below 10%")
            recommendations.append("Aim for at least 10-20% savings")
        elif savings_rate < 20:
            health_score -= 10
            recommendations.append("Good savings rate, aim for 20%+")
        else:
            recommendations.append("Excellent savings rate!")

        if high_risk_count > 0:
            health_score -= min(20, high_risk_count * 5)
            issues.append(f"{high_risk_count} high-risk transactions detected")
            recommendations.append("Review high-risk transactions for potential fraud")

        if len(anomalies) > 0:
            health_score -= min(15, len(anomalies) * 3)
            issues.append(f"{len(anomalies)} anomalous transactions detected")
            recommendations.append("Verify unusual transactions")

        expense_to_income_ratio = 0.0
        if total_income > 0:
            expense_to_income_ratio = (total_expense / total_income) * 100

        if expense_to_income_ratio > 100:
            health_score -= 25
            issues.append("Expenses exceed income")

        health_score = max(0.0, min(100.0, health_score))

        health_grade = "F"
        if health_score >= 90:
            health_grade = "A"
        elif health_score >= 80:
            health_grade = "B"
        elif health_score >= 70:
            health_grade = "C"
        elif health_score >= 60:
            health_grade = "D"

        return {
            "health_score": round(health_score, 1),
            "health_grade": health_grade,
            "issues": issues,
            "recommendations": recommendations,
            "expense_to_income_ratio": round(expense_to_income_ratio, 1),
            "savings_rate": savings_rate,
            "risk_level": "HIGH"
            if health_score < 60
            else "MEDIUM"
            if health_score < 80
            else "LOW",
        }

    def execute(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the evaluation agent.

        Args:
            session_id: Session identifier
            input_data: Input data containing analysis results

        Returns:
            Financial health evaluation
        """
        total_income = input_data.get("total_income", 0.0)
        total_expense = input_data.get("total_expense", 0.0)
        savings_rate = input_data.get("savings_rate", 0.0)

        anomalies_data = input_data.get("anomalies", [])
        anomalies = [AnomalyAlert(**a) for a in anomalies_data]

        high_risk_count = input_data.get("high_risk_count", 0)

        evaluation = self.evaluate_financial_health(
            total_income=total_income,
            total_expense=total_expense,
            savings_rate=savings_rate,
            anomalies=anomalies,
            high_risk_count=high_risk_count,
        )

        return evaluation
