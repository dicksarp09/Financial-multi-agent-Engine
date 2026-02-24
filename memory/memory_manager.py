from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
import sqlite3
from datetime import datetime, timedelta
import json
from enum import Enum


class DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    start_date: str
    end_date: str


class ShortTermState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    session_id: str
    user_id: str
    workflow_state: str
    current_transactions: List[Dict] = Field(default_factory=list)
    agent_outputs: Dict[str, Dict] = Field(default_factory=dict)
    pending_approval: Optional[str] = None
    created_at: str
    updated_at: str


class MonthlySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: str
    month: str  # YYYY-MM format
    total_income: float
    total_expense: float
    savings_rate: float
    category_breakdown: Dict[str, float]
    transaction_count: int
    anomaly_count: int
    risk_alerts: int
    created_at: str


class TrendStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: str
    category: str
    month: str
    average_amount: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    percent_change: float
    created_at: str


class CategorizationHistory(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: str
    session_id: Optional[str]
    transaction_id: str
    description: str
    assigned_category: str
    confidence: float
    source: str  # "rule", "llm", "manual"
    created_at: str


class TransactionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: str
    session_id: str
    transaction_id: str
    date: str
    description: str
    amount: float
    category: Optional[str] = None
    is_anomaly: bool = False
    risk_score: Optional[float] = None
    created_at: str


class MemoryException(Exception):
    """Base exception for memory operations."""

    pass


class UserScopeViolation(Exception):
    """Raised when cross-user access is attempted."""

    pass


class MemoryManager:
    """
    Memory management with strict user isolation.

    Two layers:
    - SHORT-TERM MEMORY (STM): Per-session state
    - LONG-TERM MEMORY (LTM): Historical data
    """

    def __init__(self, db_path: str = "event_log.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        """Initialize all memory tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Short-term memory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS short_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                workflow_state TEXT NOT NULL,
                current_transactions TEXT,
                agent_outputs TEXT,
                pending_approval TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Long-term memory tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                is_anomaly INTEGER DEFAULT 0,
                risk_score REAL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, transaction_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                month TEXT NOT NULL,
                total_income REAL NOT NULL,
                total_expense REAL NOT NULL,
                savings_rate REAL NOT NULL,
                category_breakdown TEXT NOT NULL,
                transaction_count INTEGER NOT NULL,
                anomaly_count INTEGER DEFAULT 0,
                risk_alerts INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, month)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                month TEXT NOT NULL,
                average_amount REAL NOT NULL,
                trend_direction TEXT NOT NULL,
                percent_change REAL NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, category, month)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorization_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                transaction_id TEXT NOT NULL,
                description TEXT NOT NULL,
                assigned_category TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, transaction_id)
            )
        """)

        # User index for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_stm_user ON short_term_memory(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_summaries_user ON monthly_summaries(user_id)"
        )

        conn.commit()
        conn.close()

    # ==================== SHORT-TERM MEMORY ====================

    def get_short_term_state(
        self, session_id: str, user_id: str
    ) -> Optional[ShortTermState]:
        """
        Get short-term memory state for a session.

        Args:
            session_id: Session identifier
            user_id: User identifier (for validation)

        Returns:
            ShortTermState or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT session_id, user_id, workflow_state, current_transactions, 
                   agent_outputs, pending_approval, created_at, updated_at
            FROM short_term_memory
            WHERE session_id = ?
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Validate user scope
        if row[1] != user_id:
            raise UserScopeViolation(
                f"Cross-user access: requested user={user_id}, actual user={row[1]}"
            )

        return ShortTermState(
            session_id=row[0],
            user_id=row[1],
            workflow_state=row[2],
            current_transactions=json.loads(row[3]) if row[3] else [],
            agent_outputs=json.loads(row[4]) if row[4] else {},
            pending_approval=row[5],
            created_at=row[6],
            updated_at=row[7],
        )

    def update_short_term_state(
        self,
        session_id: str,
        user_id: str,
        workflow_state: Optional[str] = None,
        current_transactions: Optional[List[Dict]] = None,
        agent_outputs: Optional[Dict[str, Dict]] = None,
        pending_approval: Optional[str] = None,
    ) -> ShortTermState:
        """
        Update short-term memory state.

        Args:
            session_id: Session identifier
            user_id: User identifier (must match existing record)
            workflow_state: New workflow state
            current_transactions: Transaction list
            agent_outputs: Agent output dictionary
            pending_approval: Pending approval ID

        Returns:
            Updated ShortTermState
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        # Check if exists
        cursor.execute(
            "SELECT user_id FROM short_term_memory WHERE session_id = ?", (session_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # Validate user scope
            if existing[0] != user_id:
                raise UserScopeViolation(
                    f"Cross-user update attempt: {user_id} != {existing[0]}"
                )

            # Build update query
            updates = ["updated_at = ?"]
            params = [now]

            if workflow_state is not None:
                updates.append("workflow_state = ?")
                params.append(workflow_state)
            if current_transactions is not None:
                updates.append("current_transactions = ?")
                params.append(json.dumps(current_transactions))
            if agent_outputs is not None:
                updates.append("agent_outputs = ?")
                params.append(json.dumps(agent_outputs))
            if pending_approval is not None:
                updates.append("pending_approval = ?")
                params.append(pending_approval)

            params.append(session_id)

            cursor.execute(
                f"""
                UPDATE short_term_memory 
                SET {", ".join(updates)}
                WHERE session_id = ?
            """,
                params,
            )
        else:
            # Create new
            cursor.execute(
                """
                INSERT INTO short_term_memory 
                (session_id, user_id, workflow_state, current_transactions, agent_outputs, pending_approval, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    user_id,
                    workflow_state or "INIT",
                    json.dumps(current_transactions or []),
                    json.dumps(agent_outputs or {}),
                    pending_approval,
                    now,
                    now,
                ),
            )

        conn.commit()
        conn.close()

        return self.get_short_term_state(session_id, user_id)

    def clear_short_term(self, session_id: str, user_id: str) -> bool:
        """
        Clear short-term memory for a session.

        Args:
            session_id: Session to clear
            user_id: User identifier (for validation)

        Returns:
            True if cleared
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id FROM short_term_memory WHERE session_id = ?", (session_id,)
        )
        existing = cursor.fetchone()

        if existing:
            if existing[0] != user_id:
                raise UserScopeViolation(f"Cross-user clear attempt")
            cursor.execute(
                "DELETE FROM short_term_memory WHERE session_id = ?", (session_id,)
            )
            conn.commit()
            conn.close()
            return True

        conn.close()
        return False

    # ==================== LONG-TERM MEMORY ====================

    def store_transaction(self, transaction: TransactionRecord) -> bool:
        """
        Store a transaction in long-term memory.

        Args:
            transaction: Transaction to store

        Returns:
            True if stored
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO transactions 
                (user_id, session_id, transaction_id, date, description, amount, category, is_anomaly, risk_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    transaction.user_id,
                    transaction.session_id,
                    transaction.transaction_id,
                    transaction.date,
                    transaction.description,
                    transaction.amount,
                    transaction.category,
                    1 if transaction.is_anomaly else 0,
                    transaction.risk_score,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            result = True
        except sqlite3.IntegrityError:
            result = False
        finally:
            conn.close()

        return result

    def get_user_transactions(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000,
    ) -> List[TransactionRecord]:
        """
        Get user transactions within date range.

        Args:
            user_id: User identifier
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            limit: Max records

        Returns:
            List of transactions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM transactions WHERE user_id = ?"
        params = [user_id]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            TransactionRecord(
                user_id=r[1],
                session_id=r[2],
                transaction_id=r[3],
                date=r[4],
                description=r[5],
                amount=r[6],
                category=r[7],
                is_anomaly=bool(r[8]),
                risk_score=r[9],
                created_at=r[10],
            )
            for r in rows
        ]

    def store_monthly_summary(self, summary: MonthlySummary) -> bool:
        """
        Store monthly summary.

        Args:
            summary: MonthlySummary to store

        Returns:
            True if stored
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO monthly_summaries 
                (user_id, month, total_income, total_expense, savings_rate, category_breakdown, transaction_count, anomaly_count, risk_alerts, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    summary.user_id,
                    summary.month,
                    summary.total_income,
                    summary.total_expense,
                    summary.savings_rate,
                    json.dumps(summary.category_breakdown),
                    summary.transaction_count,
                    summary.anomaly_count,
                    summary.risk_alerts,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            result = True
        except sqlite3.IntegrityError:
            result = False
        finally:
            conn.close()

        return result

    def get_monthly_summaries(
        self, user_id: str, months: int = 6
    ) -> List[MonthlySummary]:
        """
        Get recent monthly summaries.

        Args:
            user_id: User identifier
            months: Number of months to retrieve

        Returns:
            List of monthly summaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id, month, total_income, total_expense, savings_rate, 
                   category_breakdown, transaction_count, anomaly_count, risk_alerts, created_at
            FROM monthly_summaries
            WHERE user_id = ?
            ORDER BY month DESC
            LIMIT ?
        """,
            (user_id, months),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            MonthlySummary(
                user_id=r[0],
                month=r[1],
                total_income=r[2],
                total_expense=r[3],
                savings_rate=r[4],
                category_breakdown=json.loads(r[5]),
                transaction_count=r[6],
                anomaly_count=r[7],
                risk_alerts=r[8],
                created_at=r[9],
            )
            for r in rows
        ]

    def store_categorization(self, history: CategorizationHistory) -> bool:
        """
        Store categorization history.

        Args:
            history: CategorizationHistory to store

        Returns:
            True if stored
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO categorization_history 
                (user_id, session_id, transaction_id, description, assigned_category, confidence, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    history.user_id,
                    history.session_id,
                    history.transaction_id,
                    history.description,
                    history.assigned_category,
                    history.confidence,
                    history.source,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            result = True
        except sqlite3.IntegrityError:
            result = False
        finally:
            conn.close()

        return result

    def get_category_history(
        self, user_id: str, category: Optional[str] = None, limit: int = 100
    ) -> List[CategorizationHistory]:
        """
        Get categorization history.

        Args:
            user_id: User identifier
            category: Optional category filter
            limit: Max records

        Returns:
            List of categorization history
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM categorization_history WHERE user_id = ?"
        params = [user_id]

        if category:
            query += " AND assigned_category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            CategorizationHistory(
                user_id=r[1],
                session_id=r[2],
                transaction_id=r[3],
                description=r[4],
                assigned_category=r[5],
                confidence=r[6],
                source=r[7],
                created_at=r[8],
            )
            for r in rows
        ]


_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global memory manager instance."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager
