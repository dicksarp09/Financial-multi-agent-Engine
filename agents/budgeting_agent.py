from typing import Dict, Any, List
from schemas import TransactionRecord
from compute.budget_allocator import suggest_budget_from_breakdown


class BudgetingAgent:
    """Agent responsible for creating budget suggestions."""

    def __init__(self):
        self.name = "budgeting_agent"

    def create_budget(
        self,
        category_breakdown: Dict[str, float],
        total_income: float,
        savings_target: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Create budget suggestions based on spending and income.

        Args:
            category_breakdown: Current spending by category
            total_income: Total monthly income
            savings_target: Target savings rate percentage

        Returns:
            Budget suggestions
        """
        if total_income <= 0:
            raise ValueError("Total income must be positive for budgeting")

        result = suggest_budget_from_breakdown(
            category_breakdown=category_breakdown,
            total_income=total_income,
            savings_target=savings_target,
        )

        return {
            "income_level": result.income_level,
            "savings_target_met": result.savings_target_met,
            "savings_target": savings_target,
            "suggestions": [s.model_dump() for s in result.allocations],
            "total_suggested": sum(s.suggested_budget for s in result.allocations),
        }

    def execute(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the budgeting agent.

        Args:
            session_id: Session identifier
            input_data: Input data containing breakdown and totals

        Returns:
            Budget suggestions
        """
        category_breakdown = input_data.get("category_breakdown", {})
        total_income = input_data.get("total_income", 0.0)
        savings_target = input_data.get("savings_target", 20.0)

        budget = self.create_budget(category_breakdown, total_income, savings_target)

        return budget
