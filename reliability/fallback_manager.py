from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
import json
from enum import Enum


class FallbackType(Enum):
    """Types of fallback strategies."""

    RULE_BASED = "rule_based"
    DETERMINISTIC = "deterministic"
    CACHED = "cached"
    MINIMAL = "minimal"


@dataclass
class FallbackEvent:
    """Record of a fallback activation."""

    timestamp: str
    session_id: str
    agent_name: str
    original_error: str
    fallback_type: FallbackType
    fallback_executed: str
    success: bool


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""

    enable_rule_based_fallback: bool = True
    enable_deterministic_fallback: bool = True
    enable_cached_fallback: bool = True
    enable_minimal_fallback: bool = True


class FallbackManager:
    """
    Manages fallback strategies for graceful degradation.

    When agents fail, provides alternative execution paths.
    Always ensures a valid response is returned.
    """

    def __init__(self, config: FallbackConfig = None, db_path: str = "event_log.db"):
        self.config = config or FallbackConfig()
        self.db_path = db_path
        self._fallback_handlers: Dict[str, Dict[FallbackType, Callable]] = {}
        self._init_table()

    def _init_table(self):
        """Initialize fallback events table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fallback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                original_error TEXT,
                fallback_type TEXT NOT NULL,
                fallback_executed TEXT,
                success INTEGER NOT NULL,
                UNIQUE(session_id, agent_name, timestamp)
            )
        """)
        conn.commit()
        conn.close()

    def register_fallback(
        self, agent_name: str, fallback_type: FallbackType, handler: Callable
    ):
        """Register a fallback handler for an agent."""
        if agent_name not in self._fallback_handlers:
            self._fallback_handlers[agent_name] = {}
        self._fallback_handlers[agent_name][fallback_type] = handler

    def execute_fallback(
        self,
        agent_name: str,
        session_id: str,
        original_error: Exception,
        fallback_type: FallbackType,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute fallback strategy.

        Args:
            agent_name: Agent that failed
            session_id: Current session
            original_error: The error that triggered fallback
            fallback_type: Type of fallback to execute
            context: Context data for fallback

        Returns:
            Fallback result
        """
        fallback_result = None
        success = False

        handler = self._get_handler(agent_name, fallback_type)

        if handler:
            try:
                fallback_result = handler(context)
                success = True
            except Exception as e:
                fallback_result = {"error": str(e)}
        else:
            fallback_result = self._get_default_fallback(fallback_type, context)

        self._log_fallback(
            session_id=session_id,
            agent_name=agent_name,
            original_error=str(original_error),
            fallback_type=fallback_type,
            fallback_executed=json.dumps(fallback_result),
            success=success,
        )

        return {
            "fallback_type": fallback_type.value,
            "fallback_result": fallback_result,
            "degraded_mode": True,
            "fallback_reason": str(original_error)[:200],
        }

    def _get_handler(
        self, agent_name: str, fallback_type: FallbackType
    ) -> Optional[Callable]:
        """Get registered fallback handler."""
        if agent_name in self._fallback_handlers:
            return self._fallback_handlers[agent_name].get(fallback_type)
        return None

    def _get_default_fallback(
        self, fallback_type: FallbackType, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get default fallback based on type."""
        if fallback_type == FallbackType.RULE_BASED:
            return self._rule_based_fallback(context)
        elif fallback_type == FallbackType.DETERMINISTIC:
            return self._deterministic_fallback(context)
        elif fallback_type == FallbackType.CACHED:
            return self._cached_fallback(context)
        else:
            return self._minimal_fallback(context)

    def _rule_based_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based categorization fallback."""
        transactions = context.get("transactions", [])

        keyword_categories = {
            "grocery": "Food",
            "restaurant": "Food",
            "coffee": "Food",
            "uber": "Transportation",
            "lyft": "Transportation",
            "gas": "Transportation",
            "rent": "Housing",
            "mortgage": "Housing",
            "electric": "Utilities",
            "water": "Utilities",
            "internet": "Utilities",
            "netflix": "Entertainment",
            "spotify": "Entertainment",
            "doctor": "Healthcare",
            "pharmacy": "Healthcare",
            "salary": "Income",
            "payroll": "Income",
            "deposit": "Income",
        }

        categorized = []
        for txn in transactions:
            desc_lower = txn.get("description", "").lower()
            category = "Other"

            for keyword, cat in keyword_categories.items():
                if keyword in desc_lower:
                    category = cat
                    break

            if txn.get("amount", 0) > 0:
                category = "Income"

            categorized.append({**txn, "category": category, "fallback": "rule_based"})

        return {"transactions": categorized, "fallback_type": "rule_based"}

    def _deterministic_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic budget calculation fallback."""
        income = context.get("total_income", 0)
        breakdown = context.get("category_breakdown", {})

        if income > 0:
            suggestions = []
            percentages = {
                "Housing": 0.30,
                "Food": 0.20,
                "Transportation": 0.15,
                "Utilities": 0.10,
                "Healthcare": 0.05,
                "Entertainment": 0.05,
                "Savings": 0.10,
                "Other": 0.05,
            }

            for cat, pct in percentages.items():
                suggestions.append(
                    {
                        "category": cat,
                        "suggested_budget": round(income * pct, 2),
                        "reasoning": f"Default {int(pct * 100)}% allocation",
                        "fallback": "deterministic",
                    }
                )

            return {"suggestions": suggestions, "fallback_type": "deterministic"}

        return {"suggestions": [], "fallback_type": "deterministic"}

    def _cached_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Cached data fallback."""
        user_id = context.get("user_id", "unknown")

        return {
            "cached": True,
            "user_id": user_id,
            "message": "Using cached summary data",
            "fallback_type": "cached",
        }

    def _minimal_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Minimal fallback - always returns valid response."""
        return {
            "total_income": context.get("total_income", 0),
            "total_expense": context.get("total_expense", 0),
            "category_breakdown": context.get("category_breakdown", {}),
            "savings_rate": context.get("savings_rate", 0),
            "budget_suggestions": [],
            "anomalies": [],
            "fallback_type": "minimal",
            "degraded_mode": True,
            "note": "System operating in minimal mode due to errors",
        }

    def _log_fallback(
        self,
        session_id: str,
        agent_name: str,
        original_error: str,
        fallback_type: FallbackType,
        fallback_executed: str,
        success: bool,
    ):
        """Log fallback event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO fallback_events 
                (session_id, agent_name, timestamp, original_error, fallback_type, fallback_executed, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    agent_name,
                    datetime.utcnow().isoformat(),
                    original_error[:500],
                    fallback_type.value,
                    fallback_executed[:1000],
                    1 if success else 0,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def get_fallback_history(self, session_id: str) -> List[FallbackEvent]:
        """Get fallback history for session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, agent_name, timestamp, original_error, fallback_type, fallback_executed, success
            FROM fallback_events
            WHERE session_id = ?
            ORDER BY timestamp DESC
        """,
            (session_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            FallbackEvent(
                timestamp=r[2],
                session_id=r[0],
                agent_name=r[1],
                original_error=r[3] or "",
                fallback_type=FallbackType(r[4]),
                fallback_executed=r[5],
                success=bool(r[6]),
            )
            for r in rows
        ]


_global_fallback_manager: Optional[FallbackManager] = None


def get_fallback_manager(config: FallbackConfig = None) -> FallbackManager:
    """Get global fallback manager instance."""
    global _global_fallback_manager
    if _global_fallback_manager is None:
        _global_fallback_manager = FallbackManager(config)
    return _global_fallback_manager
