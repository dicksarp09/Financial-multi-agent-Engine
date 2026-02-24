from typing import Dict, List
from dataclasses import dataclass
from schemas import BudgetSuggestionOutput


BUDGET_RULES = {
    "low_income": {
        "threshold": 3000,
        "rules": {
            "Housing": 0.30,
            "Food": 0.20,
            "Transportation": 0.15,
            "Utilities": 0.10,
            "Healthcare": 0.05,
            "Entertainment": 0.05,
            "Savings": 0.10,
            "Other": 0.05,
        },
    },
    "medium_income": {
        "threshold": 7000,
        "rules": {
            "Housing": 0.28,
            "Food": 0.18,
            "Transportation": 0.12,
            "Utilities": 0.08,
            "Healthcare": 0.05,
            "Entertainment": 0.08,
            "Savings": 0.15,
            "Other": 0.06,
        },
    },
    "high_income": {
        "threshold": float("inf"),
        "rules": {
            "Housing": 0.25,
            "Food": 0.15,
            "Transportation": 0.10,
            "Utilities": 0.06,
            "Healthcare": 0.05,
            "Entertainment": 0.10,
            "Savings": 0.20,
            "Other": 0.09,
        },
    },
}


@dataclass(frozen=True)
class BudgetAllocationResult:
    allocations: List[BudgetSuggestionOutput]
    income_level: str
    savings_target_met: bool


def determine_income_level(total_income: float) -> str:
    """
    Determine income level based on total income.

    Args:
        total_income: Monthly total income

    Returns:
        Income level: 'low_income', 'medium_income', or 'high_income'
    """
    if total_income < BUDGET_RULES["low_income"]["threshold"]:
        return "low_income"
    elif total_income < BUDGET_RULES["medium_income"]["threshold"]:
        return "medium_income"
    else:
        return "high_income"


def suggest_budget(
    category_spend: Dict[str, float], total_income: float, savings_target: float
) -> BudgetAllocationResult:
    """
    Suggest budget allocations based on income level and savings target.

    Args:
        category_spend: Current spending by category
        total_income: Total monthly income
        savings_target: Target savings rate percentage

    Returns:
        BudgetAllocationResult with budget suggestions
    """
    if total_income <= 0:
        raise ValueError("Total income must be positive")

    if savings_target < 0 or savings_target > 100:
        raise ValueError("Savings target must be between 0 and 100")

    income_level = determine_income_level(total_income)
    rules = BUDGET_RULES[income_level]["rules"]

    target_savings = total_income * (savings_target / 100.0)
    current_savings = total_income - sum(category_spend.values())
    savings_target_met = current_savings >= target_savings

    allocations = []

    for category, percentage in rules.items():
        suggested = total_income * percentage
        current = category_spend.get(category, 0.0)

        if category == "Savings":
            reasoning = f"Target savings of {savings_target}% = ${target_savings:.2f}"
        elif current > suggested:
            reasoning = f"Current ${current:.2f} exceeds suggested ${suggested:.2f}. Consider reducing."
        elif current < suggested * 0.5:
            reasoning = (
                f"Current ${current:.2f} is well below suggested ${suggested:.2f}"
            )
        else:
            reasoning = f"Within recommended range (${suggested * 0.8:.2f} - ${suggested * 1.2:.2f})"

        allocations.append(
            BudgetSuggestionOutput(
                category=category,
                suggested_budget=round(suggested, 2),
                reasoning=reasoning,
            )
        )

    return BudgetAllocationResult(
        allocations=allocations,
        income_level=income_level,
        savings_target_met=savings_target_met,
    )


def suggest_budget_from_breakdown(
    category_breakdown: Dict[str, float], total_income: float, savings_target: float
) -> BudgetAllocationResult:
    """
    Convenience function to suggest budget from category breakdown.

    Args:
        category_breakdown: Spending by category
        total_income: Total monthly income
        savings_target: Target savings rate percentage

    Returns:
        BudgetAllocationResult with budget suggestions
    """
    return suggest_budget(category_breakdown, total_income, savings_target)
