from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import json


class CompressedContext(BaseModel):
    """Compressed context for LLM injection."""

    model_config = ConfigDict(extra="forbid", strict=True)

    avg_income: float
    avg_expense: float
    top_categories: Dict[str, float]
    savings_trend: float
    risk_flags_count: int
    period: str
    compressed_at: str


class ContextSnapshot(BaseModel):
    """Snapshot of context used for decisions."""

    model_config = ConfigDict(extra="forbid", strict=True)

    snapshot_id: str
    user_id: str
    session_id: str
    compressed_context: str  # JSON string
    source_months: int
    created_at: str


class ContextCompressor:
    """
    Context compression before LLM usage.

    Never passes raw transaction history.
    Generates structured summaries only.
    """

    def __init__(self, max_token_equivalent: int = 500):
        self.max_token_equivalent = max_token_equivalent

    def compress_historical_context(
        self,
        user_id: str,
        session_id: str,
        historical_data: Dict[str, Any],
        current_month_data: Optional[Dict[str, Any]] = None,
    ) -> CompressedContext:
        """
        Compress historical data into structured summary.

        Args:
            user_id: User identifier
            session_id: Session identifier
            historical_data: Data from retrieval agent
            current_month_data: Optional current month data

        Returns:
            CompressedContext for LLM
        """
        avg_income = historical_data.get("average_income", 0.0)
        avg_expense = historical_data.get("average_expense", 0.0)
        category_trends = historical_data.get("category_trends", {})
        savings_trend = historical_data.get("savings_trend", 0.0)
        risk_alerts = historical_data.get("risk_alerts_count", 0)

        if current_month_data:
            current_breakdown = current_month_data.get("category_breakdown", {})
            for cat, amount in current_breakdown.items():
                if cat in category_trends:
                    category_trends[cat] = (category_trends[cat] + amount) / 2
                else:
                    category_trends[cat] = amount

            avg_income = (avg_income + current_month_data.get("total_income", 0)) / 2
            avg_expense = (avg_expense + current_month_data.get("total_expense", 0)) / 2
            risk_alerts += current_month_data.get("risk_alerts", 0)

        sorted_categories = sorted(
            category_trends.items(), key=lambda x: x[1], reverse=True
        )
        top_categories = dict(sorted_categories[:5])

        period = f"{historical_data.get('period_start', '')} to {historical_data.get('period_end', '')}"

        return CompressedContext(
            avg_income=round(avg_income, 2),
            avg_expense=round(avg_expense, 2),
            top_categories={k: round(v, 2) for k, v in top_categories.items()},
            savings_trend=round(savings_trend, 3),
            risk_flags_count=risk_alerts,
            period=period,
            compressed_at=datetime.utcnow().isoformat(),
        )

    def to_json_string(self, context: CompressedContext) -> str:
        """
        Convert compressed context to JSON string.

        Args:
            context: CompressedContext

        Returns:
            JSON string for LLM
        """
        return json.dumps(context.model_dump(), sort_keys=True)

    def to_llm_prompt(
        self, context: CompressedContext, include_risk_warning: bool = True
    ) -> str:
        """
        Format compressed context for LLM prompt.

        Args:
            context: CompressedContext
            include_risk_warning: Include risk flag warning

        Returns:
            Formatted prompt section
        """
        lines = [
            "## Historical Context Summary",
            "",
            f"**Period:** {context.period}",
            f"**Average Income:** ${context.avg_income:,.2f}",
            f"**Average Expenses:** ${context.avg_expense:,.2f}",
            f"**Savings Trend:** {context.savings_trend:+.1%}",
            "",
            "**Top Categories:**",
        ]

        for cat, amount in context.top_categories.items():
            lines.append(f"  - {cat}: ${amount:,.2f}")

        if include_risk_warning and context.risk_flags_count > 0:
            lines.extend(
                [
                    "",
                    f"⚠️ **Risk Alerts:** {context.risk_flags_count} flagged transactions in recent months",
                ]
            )

        lines.extend(["", f"_Compressed at: {context.compressed_at}_"])

        return "\n".join(lines)

    def estimate_tokens(self, context: CompressedContext) -> int:
        """
        Estimate token count for compressed context.

        Args:
            context: CompressedContext

        Returns:
            Estimated token count
        """
        json_str = self.to_json_string(context)
        return len(json_str) // 4

    def is_within_limit(self, context: CompressedContext) -> bool:
        """
        Check if context is within token limit.

        Args:
            context: CompressedContext

        Returns:
            True if within limit
        """
        return self.estimate_tokens(context) <= self.max_token_equivalent


_global_context_compressor: Optional[ContextCompressor] = None


def get_context_compressor(max_token_equivalent: int = 500) -> ContextCompressor:
    """Get global context compressor instance."""
    global _global_context_compressor
    if _global_context_compressor is None:
        _global_context_compressor = ContextCompressor(max_token_equivalent)
    return _global_context_compressor
