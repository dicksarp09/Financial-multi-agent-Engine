from typing import Dict, Any, List
from schemas import FinancialReport, BudgetSuggestionOutput, AnomalyAlert


class ReportingAgent:
    """Agent responsible for generating final financial reports."""

    def __init__(self):
        self.name = "reporting_agent"

    def generate_report(
        self,
        total_income: float,
        total_expense: float,
        category_breakdown: Dict[str, float],
        savings_rate: float,
        budget_suggestions: List[BudgetSuggestionOutput],
        anomalies: List[AnomalyAlert],
    ) -> FinancialReport:
        """
        Generate comprehensive financial report.

        Args:
            total_income: Total income
            total_expense: Total expenses
            category_breakdown: Spending by category
            savings_rate: Savings rate
            budget_suggestions: Budget suggestions
            anomalies: Detected anomalies

        Returns:
            FinancialReport object
        """
        return FinancialReport(
            total_income=total_income,
            total_expense=total_expense,
            category_breakdown=category_breakdown,
            savings_rate=savings_rate,
            budget_suggestions=budget_suggestions,
            anomalies=anomalies,
        )

    def format_report_text(self, report: FinancialReport) -> str:
        """
        Format report as human-readable text.

        Args:
            report: FinancialReport object

        Returns:
            Formatted report string
        """
        lines = [
            "=" * 50,
            "FINANCIAL REPORT",
            "=" * 50,
            "",
            f"Total Income:    ${report.total_income:,.2f}",
            f"Total Expenses:  ${report.total_expense:,.2f}",
            f"Net Savings:     ${report.total_income - report.total_expense:,.2f}",
            f"Savings Rate:    {report.savings_rate:.1f}%",
            "",
            "Category Breakdown:",
            "-" * 30,
        ]

        for category, amount in sorted(report.category_breakdown.items()):
            percentage = (
                (amount / report.total_expense * 100) if report.total_expense > 0 else 0
            )
            lines.append(f"  {category:20s} ${amount:>10,.2f} ({percentage:>5.1f}%)")

        if report.budget_suggestions:
            lines.extend(
                [
                    "",
                    "Budget Suggestions:",
                    "-" * 30,
                ]
            )
            for suggestion in report.budget_suggestions:
                lines.append(
                    f"  {suggestion.category:20s} ${suggestion.suggested_budget:>10,.2f}"
                )
                lines.append(f"    -> {suggestion.reasoning}")

        if report.anomalies:
            lines.extend(
                [
                    "",
                    "Anomalies Detected:",
                    "-" * 30,
                ]
            )
            for anomaly in report.anomalies:
                lines.append(f"  ID: {anomaly.transaction_id}")
                lines.append(f"    Reason: {anomaly.reason}")
                lines.append(f"    Risk Score: {anomaly.risk_score:.2f}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)

    def execute(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the reporting agent.

        Args:
            session_id: Session identifier
            input_data: Input data containing all analysis results

        Returns:
            Complete report
        """
        total_income = input_data.get("total_income", 0.0)
        total_expense = input_data.get("total_expense", 0.0)
        category_breakdown = input_data.get("category_breakdown", {})
        savings_rate = input_data.get("savings_rate", 0.0)

        suggestions_data = input_data.get("budget_suggestions", [])
        budget_suggestions = [BudgetSuggestionOutput(**s) for s in suggestions_data]

        anomalies_data = input_data.get("anomalies", [])
        anomalies = [AnomalyAlert(**a) for a in anomalies_data]

        report = self.generate_report(
            total_income=total_income,
            total_expense=total_expense,
            category_breakdown=category_breakdown,
            savings_rate=savings_rate,
            budget_suggestions=budget_suggestions,
            anomalies=anomalies,
        )

        report_text = self.format_report_text(report)

        return {"report": report.model_dump(), "report_text": report_text}
