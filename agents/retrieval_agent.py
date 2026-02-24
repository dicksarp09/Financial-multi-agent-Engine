from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta
import json

from memory.memory_manager import get_memory_manager


class HistoricalContext(BaseModel):
    """Output schema for retrieval agent."""

    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: str
    months_analyzed: int
    average_income: float
    average_expense: float
    category_trends: Dict[str, float]
    savings_trend: float
    total_transactions: int
    risk_alerts_count: int
    period_start: str
    period_end: str


class RetrievalRequest(BaseModel):
    """Request schema for retrieval agent."""

    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: str
    session_id: str
    months: int = Field(default=6, ge=1, le=24)
    include_transactions: bool = False
    include_trends: bool = True


class RetrievalAgent:
    """
    Read-only retrieval agent for historical context.

    Capabilities:
    - Fetch prior months summaries
    - Fetch trend data
    - Return structured historical context

    Cannot:
    - Modify database
    - Trigger other agents
    - Execute arbitrary code
    """

    def __init__(self):
        self.name = "retrieval_agent"
        self.memory = get_memory_manager()

    def retrieve_historical_context(
        self, request: RetrievalRequest
    ) -> HistoricalContext:
        """
        Retrieve historical context for a user.

        Args:
            request: Retrieval request

        Returns:
            HistoricalContext with aggregated data
        """
        summaries = self.memory.get_monthly_summaries(request.user_id, request.months)

        if not summaries:
            return HistoricalContext(
                user_id=request.user_id,
                months_analyzed=0,
                average_income=0.0,
                average_expense=0.0,
                category_trends={},
                savings_trend=0.0,
                total_transactions=0,
                risk_alerts_count=0,
                period_start="",
                period_end="",
            )

        total_income = sum(s.total_income for s in summaries)
        total_expense = sum(s.total_expense for s in summaries)

        months_count = len(summaries)
        avg_income = total_income / months_count
        avg_expense = total_expense / months_count

        category_totals: Dict[str, float] = {}
        for summary in summaries:
            for cat, amount in summary.category_breakdown.items():
                category_totals[cat] = category_totals.get(cat, 0) + amount

        category_averages = {
            cat: amount / months_count for cat, amount in category_totals.items()
        }

        savings_rates = [s.savings_rate for s in summaries if s.savings_rate != 0]
        savings_trend = 0.0
        if len(savings_rates) >= 2:
            first_half = sum(savings_rates[: len(savings_rates) // 2]) / (
                len(savings_rates) // 2
            )
            second_half = sum(savings_rates[len(savings_rates) // 2 :]) / (
                len(savings_rates) - len(savings_rates) // 2
            )
            savings_trend = (second_half - first_half) / max(abs(first_half), 0.01)

        total_transactions = sum(s.transaction_count for s in summaries)
        risk_alerts = sum(s.risk_alerts for s in summaries)

        sorted_summaries = sorted(summaries, key=lambda x: x.month)

        return HistoricalContext(
            user_id=request.user_id,
            months_analyzed=months_count,
            average_income=round(avg_income, 2),
            average_expense=round(avg_expense, 2),
            category_trends={k: round(v, 2) for k, v in category_averages.items()},
            savings_trend=round(savings_trend, 3),
            total_transactions=total_transactions,
            risk_alerts_count=risk_alerts,
            period_start=sorted_summaries[0].month if sorted_summaries else "",
            period_end=sorted_summaries[-1].month if sorted_summaries else "",
        )

    def retrieve_transactions(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Retrieve transactions for a user.

        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            limit: Max records

        Returns:
            List of transaction records
        """
        transactions = self.memory.get_user_transactions(
            user_id=user_id, start_date=start_date, end_date=end_date, limit=limit
        )

        return [
            {
                "transaction_id": t.transaction_id,
                "date": t.date,
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
                "is_anomaly": t.is_anomaly,
                "risk_score": t.risk_score,
            }
            for t in transactions
        ]

    def execute(self, session_id: str, input_data: Dict) -> Dict:
        """
        Execute the retrieval agent.

        Args:
            session_id: Session identifier
            input_data: Input with user_id, months, etc.

        Returns:
            Retrieved context
        """
        user_id = input_data.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")

        months = input_data.get("months", 6)

        request = RetrievalRequest(
            user_id=user_id,
            session_id=session_id,
            months=months,
            include_transactions=input_data.get("include_transactions", False),
            include_trends=input_data.get("include_trends", True),
        )

        context = self.retrieve_historical_context(request)

        result = {
            "user_id": context.user_id,
            "months_analyzed": context.months_analyzed,
            "average_income": context.average_income,
            "average_expense": context.average_expense,
            "category_trends": context.category_trends,
            "savings_trend": context.savings_trend,
            "total_transactions": context.total_transactions,
            "risk_alerts_count": context.risk_alerts_count,
            "period_start": context.period_start,
            "period_end": context.period_end,
        }

        if request.include_transactions:
            result["transactions"] = self.retrieve_transactions(
                user_id=user_id, limit=50
            )

        return result
