from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import json


class ReadTransactionsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    file_path: str = Field(..., description="Path to the transaction file")


class TransactionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    date: str = Field(..., description="Transaction date in ISO format")
    description: str = Field(..., description="Transaction description")
    amount: float = Field(
        ...,
        description="Transaction amount (positive for income, negative for expense)",
    )
    category: Optional[str] = Field(default=None, description="Transaction category")
    transaction_id: Optional[str] = Field(
        default=None, description="Unique transaction identifier"
    )

    @field_validator("amount")
    @classmethod
    def amount_must_be_finite(cls, v: float) -> float:
        if not isinstance(v, (int, float)) or not float("-inf") < v < float("inf"):
            raise ValueError("Amount must be a finite number")
        return float(v)


class CategorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    transactions: List[TransactionRecord] = Field(
        ..., description="List of transactions to categorize"
    )


class BudgetSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    category: str = Field(..., description="Category name")
    suggested_budget: float = Field(..., description="Suggested budget amount")
    reasoning: str = Field(..., description="Reasoning for the budget suggestion")

    @field_validator("suggested_budget")
    @classmethod
    def budget_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Budget must be non-negative")
        return v


class AnomalyAlert(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    transaction_id: str = Field(..., description="ID of the anomalous transaction")
    reason: str = Field(..., description="Reason for anomaly flag")
    risk_score: float = Field(..., description="Risk score (0-1)")

    @field_validator("risk_score")
    @classmethod
    def risk_score_must_be_valid(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Risk score must be between 0 and 1")
        return v


class FinancialReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    total_income: float = Field(..., description="Total income")
    total_expense: float = Field(..., description="Total expenses")
    category_breakdown: Dict[str, float] = Field(
        ..., description="Breakdown by category"
    )
    savings_rate: float = Field(..., description="Savings rate as percentage")
    budget_suggestions: List[BudgetSuggestionOutput] = Field(
        ..., description="Budget suggestions"
    )
    anomalies: List[AnomalyAlert] = Field(
        default_factory=list, description="Detected anomalies"
    )

    @field_validator("savings_rate")
    @classmethod
    def savings_rate_must_be_valid(cls, v: float) -> float:
        if not -100 <= v <= 100:
            raise ValueError("Savings rate must be between -100 and 100")
        return v


class CategoryBreakdownInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    transactions: List[TransactionRecord] = Field(
        ..., description="List of categorized transactions"
    )


class BudgetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    category_spend: Dict[str, float] = Field(
        ..., description="Current spend by category"
    )
    total_income: float = Field(..., description="Total monthly income")
    savings_target: float = Field(..., description="Target savings rate percentage")

    @field_validator("total_income", "savings_target")
    @classmethod
    def values_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v


class RiskScoreInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    transaction: TransactionRecord = Field(..., description="Transaction to score")


class AnomalyDetectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    transactions: List[TransactionRecord] = Field(
        ..., description="Transactions to analyze"
    )


class LogEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    timestamp: str
    session_id: str
    state: str
    agent_name: str
    input_payload: str = Field(..., description="JSON string of input")
    output_payload: str = Field(..., description="JSON string of output")
    error_flag: bool = False
    token_usage: Optional[int] = None


def serialize_payload(data: dict) -> str:
    """Serialize payload to JSON string."""
    return json.dumps(data, sort_keys=True)


def deserialize_payload(json_str: str) -> dict:
    """Deserialize JSON string to dict."""
    return json.loads(json_str)
