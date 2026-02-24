from typing import List, Tuple
from dataclasses import dataclass
from schemas import TransactionRecord, AnomalyAlert
import uuid


@dataclass(frozen=True)
class AnomalyDetectionResult:
    anomalies: List[AnomalyAlert]
    threshold_used: float
    method: str


def calculate_iqr(values: List[float]) -> Tuple[float, float, float]:
    """
    Calculate IQR (Interquartile Range) for outlier detection.

    Args:
        values: List of numeric values

    Returns:
        Tuple of (q1, q3, iqr)
    """
    if len(values) < 4:
        return 0.0, 0.0, 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)

    q1_idx = n // 4
    q3_idx = 3 * n // 4

    q1 = sorted_values[q1_idx]
    q3 = sorted_values[q3_idx]
    iqr = q3 - q1

    return q1, q3, iqr


def calculate_zscore(value: float, mean: float, std_dev: float) -> float:
    """
    Calculate z-score for a value.

    Args:
        value: The value to score
        mean: Mean of the distribution
        std_dev: Standard deviation

    Returns:
        Z-score
    """
    if std_dev == 0:
        return 0.0
    return (value - mean) / std_dev


def calculate_mean(values: List[float]) -> float:
    """Calculate mean of values."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_std_dev(values: List[float]) -> float:
    """Calculate standard deviation of values."""
    if len(values) < 2:
        return 0.0

    mean = calculate_mean(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance**0.5


def detect_outliers_iqr(
    transactions: List[TransactionRecord], multiplier: float = 1.5
) -> List[AnomalyAlert]:
    """
    Detect outliers using IQR method.

    Args:
        transactions: List of transactions to analyze
        multiplier: IQR multiplier (default 1.5)

    Returns:
        List of AnomalyAlert for detected outliers
    """
    expenses = [abs(txn.amount) for txn in transactions if txn.amount < 0]

    if len(expenses) < 4:
        return []

    q1, q3, iqr = calculate_iqr(expenses)

    if iqr == 0:
        return []

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    anomalies = []
    for txn in transactions:
        if txn.amount < 0:
            expense = abs(txn.amount)
            if expense > upper_bound:
                risk_score = min(
                    1.0,
                    (expense - upper_bound) / (upper_bound if upper_bound > 0 else 1),
                )
                txn_id = txn.transaction_id or str(uuid.uuid4())
                anomalies.append(
                    AnomalyAlert(
                        transaction_id=txn_id,
                        reason=f"Expense ${expense:.2f} exceeds IQR upper bound ${upper_bound:.2f}",
                        risk_score=risk_score,
                    )
                )

    return anomalies


def detect_outliers_zscore(
    transactions: List[TransactionRecord], threshold: float = 3.0
) -> List[AnomalyAlert]:
    """
    Detect outliers using Z-score method.

    Args:
        transactions: List of transactions to analyze
        threshold: Z-score threshold (default 3.0)

    Returns:
        List of AnomalyAlert for detected outliers
    """
    expenses = [abs(txn.amount) for txn in transactions if txn.amount < 0]

    if len(expenses) < 3:
        return []

    mean = calculate_mean(expenses)
    std_dev = calculate_std_dev(expenses)

    if std_dev == 0:
        return []

    anomalies = []
    for txn in transactions:
        if txn.amount < 0:
            expense = abs(txn.amount)
            zscore = abs(calculate_zscore(expense, mean, std_dev))

            if zscore > threshold:
                risk_score = min(1.0, zscore / (threshold * 2))
                txn_id = txn.transaction_id or str(uuid.uuid4())
                anomalies.append(
                    AnomalyAlert(
                        transaction_id=txn_id,
                        reason=f"Expense ${expense:.2f} has z-score {zscore:.2f} exceeding threshold {threshold}",
                        risk_score=risk_score,
                    )
                )

    return anomalies


def detect_outliers(
    transactions: List[TransactionRecord], method: str = "iqr"
) -> AnomalyDetectionResult:
    """
    Detect outliers in transactions using specified method.

    Args:
        transactions: List of transactions to analyze
        method: Detection method - 'iqr' or 'zscore'

    Returns:
        AnomalyDetectionResult with detected anomalies
    """
    if method.lower() == "iqr":
        anomalies = detect_outliers_iqr(transactions)
        return AnomalyDetectionResult(
            anomalies=anomalies, threshold_used=1.5, method="IQR"
        )
    elif method.lower() == "zscore":
        anomalies = detect_outliers_zscore(transactions)
        return AnomalyDetectionResult(
            anomalies=anomalies, threshold_used=3.0, method="Z-Score"
        )
    else:
        raise ValueError(f"Unknown method: {method}. Use 'iqr' or 'zscore'")
