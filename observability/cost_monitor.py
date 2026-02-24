from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import sqlite3
import json


@dataclass
class CostMetrics:
    """Cost metrics for a session."""

    session_id: str
    agent_name: str
    tokens_in: int = 0
    tokens_out: int = 0
    total_tokens: int = 0
    cost_reason: str = ""
    timestamp: str = ""


@dataclass
class CostThresholds:
    """Configurable cost thresholds."""

    daily_limit: float = 100.0
    monthly_limit: float = 1000.0
    alert_percentage: float = 0.8  # Alert at 80% of limit


class CostMonitor:
    """
    Track and monitor costs for LLM usage.

    Metrics tracked:
    - Tokens consumed per LLM call
    - Cost per agent
    - Cost per workflow stage
    - Total session cost
    """

    def __init__(
        self, thresholds: CostThresholds = None, db_path: str = "event_log.db"
    ):
        self.thresholds = thresholds or CostThresholds()
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        """Initialize cost tracking table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                tokens_in INTEGER NOT NULL DEFAULT 0,
                tokens_out INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                cost_reason TEXT,
                model_name TEXT,
                timestamp TEXT NOT NULL,
                UNIQUE(session_id, agent_name, timestamp)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                threshold_type TEXT NOT NULL,
                current_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                resolved INTEGER DEFAULT 0,
                UNIQUE(session_id, alert_type, timestamp)
            )
        """)

        conn.commit()
        conn.close()

    def record_llm_call(
        self,
        session_id: str,
        user_id: str,
        agent_name: str,
        tokens_in: int,
        tokens_out: int,
        cost_reason: str = "",
        model_name: str = "llama-3.1-8b-instant",
    ) -> CostMetrics:
        """Record an LLM call cost."""
        # Pricing: $0.00006 per 1K input tokens, $0.0006 per 1K output tokens (example)
        input_cost = (tokens_in / 1000) * 0.00006
        output_cost = (tokens_out / 1000) * 0.0006
        total_cost = input_cost + output_cost

        metrics = CostMetrics(
            session_id=session_id,
            agent_name=agent_name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            total_tokens=tokens_in + tokens_out,
            cost_reason=cost_reason,
            timestamp=datetime.utcnow().isoformat(),
        )

        self._save_metrics(
            session_id,
            user_id,
            agent_name,
            tokens_in,
            tokens_out,
            cost_reason,
            model_name,
        )

        self._check_daily_limit(user_id, total_cost)

        return metrics

    def _save_metrics(
        self,
        session_id: str,
        user_id: str,
        agent_name: str,
        tokens_in: int,
        tokens_out: int,
        cost_reason: str,
        model_name: str,
    ):
        """Save cost metrics to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO cost_metrics 
                (session_id, user_id, agent_name, tokens_in, tokens_out, total_tokens, cost_reason, model_name, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    user_id,
                    agent_name,
                    tokens_in,
                    tokens_out,
                    tokens_in + tokens_out,
                    cost_reason,
                    model_name,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_session_cost(self, session_id: str) -> Dict[str, Any]:
        """Get total cost for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT agent_name, SUM(tokens_in), SUM(tokens_out), SUM(total_tokens), COUNT(*)
            FROM cost_metrics
            WHERE session_id = ?
            GROUP BY agent_name
        """,
            (session_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        total_tokens = sum(r[3] for r in rows)
        total_cost = (total_tokens / 1000) * 0.0003  # Approximate average

        by_agent = {
            r[0]: {
                "tokens_in": r[1],
                "tokens_out": r[2],
                "total_tokens": r[3],
                "calls": r[4],
            }
            for r in rows
        }

        return {
            "session_id": session_id,
            "total_tokens": total_tokens,
            "estimated_cost": round(total_cost, 6),
            "by_agent": by_agent,
        }

    def get_user_daily_cost(self, user_id: str) -> float:
        """Get daily cost for user."""
        today = datetime.utcnow().date().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SUM(total_tokens) FROM cost_metrics
            WHERE user_id = ? AND timestamp >= ?
        """,
            (user_id, today),
        )

        row = cursor.fetchone()
        conn.close()

        tokens = row[0] if row[0] else 0
        return (tokens / 1000) * 0.0003

    def get_user_monthly_cost(self, user_id: str) -> float:
        """Get monthly cost for user."""
        first_of_month = datetime.utcnow().replace(day=1).date().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SUM(total_tokens) FROM cost_metrics
            WHERE user_id = ? AND timestamp >= ?
        """,
            (user_id, first_of_month),
        )

        row = cursor.fetchone()
        conn.close()

        tokens = row[0] if row[0] else 0
        return (tokens / 1000) * 0.0003

    def _check_daily_limit(self, user_id: str, additional_cost: float):
        """Check if adding cost would exceed daily limit."""
        current_daily = self.get_user_daily_cost(user_id)
        projected = current_daily + additional_cost

        if projected > self.thresholds.daily_limit * self.thresholds.alert_percentage:
            self._create_alert(
                user_id=user_id,
                session_id="",
                alert_type="daily_limit_warning",
                threshold_type="daily",
                current_value=projected,
                threshold_value=self.thresholds.daily_limit,
            )

    def _create_alert(
        self,
        user_id: str,
        session_id: str,
        alert_type: str,
        threshold_type: str,
        current_value: float,
        threshold_value: float,
    ):
        """Create a cost alert."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO cost_alerts 
                (session_id, user_id, alert_type, threshold_type, current_value, threshold_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    user_id,
                    alert_type,
                    threshold_type,
                    current_value,
                    threshold_value,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_alerts(self, user_id: str, unresolved_only: bool = True) -> List[Dict]:
        """Get cost alerts for user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT session_id, alert_type, threshold_type, current_value, threshold_value, timestamp, resolved
            FROM cost_alerts
            WHERE user_id = ?
        """
        if unresolved_only:
            query += " AND resolved = 0"

        cursor.execute(query, (user_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "session_id": r[0],
                "alert_type": r[1],
                "threshold_type": r[2],
                "current_value": r[3],
                "threshold_value": r[4],
                "timestamp": r[5],
                "resolved": bool(r[6]),
            }
            for r in rows
        ]


_global_cost_monitor: Optional[CostMonitor] = None


def get_cost_monitor(thresholds: CostThresholds = None) -> CostMonitor:
    """Get global cost monitor instance."""
    global _global_cost_monitor
    if _global_cost_monitor is None:
        _global_cost_monitor = CostMonitor(thresholds)
    return _global_cost_monitor
