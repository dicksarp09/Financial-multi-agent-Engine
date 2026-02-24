from typing import Dict
from dataclasses import dataclass
from schemas import TransactionRecord


RISK_CATEGORIES = {
    "gambling": 0.9,
    "cryptocurrency": 0.8,
    "loan": 0.7,
    "credit_card": 0.6,
    "subscription": 0.3,
    "utilities": 0.1,
    "food": 0.1,
    "transportation": 0.1,
    "housing": 0.1,
    "healthcare": 0.1,
    "entertainment": 0.2,
    "shopping": 0.3,
    "transfer": 0.4,
    "income": 0.0,
    "salary": 0.0,
}


@dataclass(frozen=True)
class RiskScoreResult:
    transaction_id: str
    risk_score: float
    risk_factors: Dict[str, float]
    category_override: str


def compute_risk_score(transaction: TransactionRecord) -> RiskScoreResult:
    """
    Compute risk score for a transaction.

    Args:
        transaction: Transaction to score

    Returns:
        RiskScoreResult with risk score and factors
    """
    risk_factors: Dict[str, float] = {}

    amount = float(transaction.amount)
    abs_amount = abs(amount)

    base_score = 0.0
    desc_lower = transaction.description.lower()

    if transaction.category:
        category_lower = transaction.category.lower()
        base_score = RISK_CATEGORIES.get(category_lower, 0.3)
        risk_factors["category_risk"] = base_score

    if abs_amount > 1000:
        large_transaction_boost = min(0.3, (abs_amount - 1000) / 10000)
        risk_factors["large_transaction"] = large_transaction_boost
        base_score += large_transaction_boost

    if abs_amount > 5000:
        very_large_boost = min(0.2, (abs_amount - 5000) / 25000)
        risk_factors["very_large_transaction"] = very_large_boost
        base_score += very_large_boost

    if amount < 0:
        high_risk_keywords = ["gambling", "casino", "lottery", "crypto"]
        for keyword in high_risk_keywords:
            if keyword in desc_lower:
                risk_factors[f"keyword_{keyword}"] = 0.5
                base_score = max(base_score, 0.8)

        debt_keywords = ["loan", "credit", "interest", "financing"]
        for keyword in debt_keywords:
            if keyword in desc_lower:
                risk_factors[f"keyword_{keyword}"] = 0.3
                base_score = max(base_score, 0.6)

    if amount > 0:
        income_keywords = ["salary", "payroll", "deposit", "refund"]
        for keyword in income_keywords:
            if keyword in desc_lower:
                base_score = 0.0
                risk_factors["income_detected"] = 1.0
                break

    final_score = min(1.0, max(0.0, base_score))

    txn_id = transaction.transaction_id or "unknown"

    category_override = (
        transaction.category if transaction.category else "Uncategorized"
    )

    return RiskScoreResult(
        transaction_id=txn_id,
        risk_score=round(final_score, 3),
        risk_factors=risk_factors,
        category_override=category_override,
    )


def compute_batch_risk_scores(
    transactions: list[TransactionRecord],
) -> list[RiskScoreResult]:
    """
    Compute risk scores for multiple transactions.

    Args:
        transactions: List of transactions to score

    Returns:
        List of RiskScoreResult
    """
    return [compute_risk_score(txn) for txn in transactions]
