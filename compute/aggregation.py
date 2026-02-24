from typing import Dict, List
from dataclasses import dataclass
from schemas import TransactionRecord


@dataclass(frozen=True)
class TotalsResult:
    total_income: float
    total_expense: float
    net_savings: float


@dataclass(frozen=True)
class CategoryBreakdownResult:
    breakdown: Dict[str, float]
    uncategorized_total: float


def compute_totals(transactions: List[TransactionRecord]) -> TotalsResult:
    """
    Compute total income and expenses from transactions.

    Args:
        transactions: List of transaction records

    Returns:
        TotalsResult with total_income, total_expense, net_savings
    """
    if not transactions:
        return TotalsResult(total_income=0.0, total_expense=0.0, net_savings=0.0)

    total_income = 0.0
    total_expense = 0.0

    for txn in transactions:
        amount = float(txn.amount)
        if amount > 0:
            total_income += amount
        else:
            total_expense += abs(amount)

    net_savings = total_income - total_expense

    return TotalsResult(
        total_income=total_income, total_expense=total_expense, net_savings=net_savings
    )


def compute_category_breakdown(
    transactions: List[TransactionRecord],
) -> CategoryBreakdownResult:
    """
    Compute spending breakdown by category.

    Args:
        transactions: List of transaction records

    Returns:
        CategoryBreakdownResult with breakdown dict and uncategorized total
    """
    breakdown: Dict[str, float] = {}
    uncategorized_total = 0.0

    for txn in transactions:
        amount = float(txn.amount)
        if amount < 0:
            expense = abs(amount)
            category = txn.category if txn.category else "Uncategorized"

            if category in breakdown:
                breakdown[category] = breakdown[category] + expense
            else:
                breakdown[category] = expense

            if not txn.category:
                uncategorized_total += expense

    return CategoryBreakdownResult(
        breakdown=breakdown, uncategorized_total=uncategorized_total
    )


def compute_savings_rate(total_income: float, total_expense: float) -> float:
    """
    Compute savings rate as percentage.

    Args:
        total_income: Total income
        total_expense: Total expenses

    Returns:
        Savings rate as percentage
    """
    if total_income <= 0:
        return 0.0

    savings = total_income - total_expense
    savings_rate = (savings / total_income) * 100.0

    return savings_rate
