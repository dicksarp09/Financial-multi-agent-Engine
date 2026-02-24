from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
import json


class TerminationReason(Enum):
    """Reasons for forced termination."""

    MAX_ITERATIONS = "max_iterations"
    MAX_TOKENS = "max_tokens"
    MAX_RUNTIME = "max_runtime"
    ERROR = "error"


class SessionLimitExceeded(Exception):
    """Raised when session limits are exceeded."""

    def __init__(self, reason: TerminationReason, message: str):
        self.reason = reason
        super().__init__(message)


@dataclass
class SessionCaps:
    """Session limits configuration."""

    max_iterations: int = 12
    max_tokens: int = 100000
    max_runtime_seconds: int = 30


@dataclass
class SessionStats:
    """Runtime statistics for session."""

    session_id: str
    iteration: int = 0
    tokens_used: int = 0
    runtime_seconds: float = 0.0
    start_time: str = ""
    last_update: str = ""


class SessionGuard:
    """
    Enforces session limits and prevents unbounded execution.

    Tracks:
    - Iteration count
    - Token usage
    - Runtime

    Forces termination if limits exceeded.
    """

    def __init__(self, caps: SessionCaps = None, db_path: str = "event_log.db"):
        self.caps = caps or SessionCaps()
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        """Initialize session stats table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                iteration INTEGER NOT NULL DEFAULT 0,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                runtime_seconds REAL NOT NULL DEFAULT 0.0,
                start_time TEXT NOT NULL,
                last_update TEXT NOT NULL,
                termination_reason TEXT,
                UNIQUE(session_id)
            )
        """)
        conn.commit()
        conn.close()

    def start_session(self, session_id: str) -> SessionStats:
        """Initialize session tracking."""
        now = datetime.utcnow().isoformat()

        stats = SessionStats(
            session_id=session_id,
            iteration=0,
            tokens_used=0,
            runtime_seconds=0.0,
            start_time=now,
            last_update=now,
        )

        self._save_stats(stats)
        return stats

    def check_limits(self, stats: SessionStats, tokens_delta: int = 0) -> bool:
        """
        Check if session should continue.

        Args:
            stats: Current session stats
            tokens_delta: Additional tokens used this iteration

        Returns:
            True if within limits

        Raises:
            SessionLimitExceeded: If any limit exceeded
        """
        if stats.iteration >= self.caps.max_iterations:
            raise SessionLimitExceeded(
                TerminationReason.MAX_ITERATIONS,
                f"Max iterations {self.caps.max_iterations} exceeded",
            )

        projected_tokens = stats.tokens_used + tokens_delta
        if projected_tokens > self.caps.max_tokens:
            raise SessionLimitExceeded(
                TerminationReason.MAX_TOKENS,
                f"Max tokens {self.caps.max_tokens} would be exceeded",
            )

        if stats.runtime_seconds > self.caps.max_runtime_seconds:
            raise SessionLimitExceeded(
                TerminationReason.MAX_RUNTIME,
                f"Max runtime {self.caps.max_runtime_seconds}s exceeded",
            )

        return True

    def increment_iteration(
        self, stats: SessionStats, tokens_used: int = 0
    ) -> SessionStats:
        """
        Increment iteration counter and update stats.

        Args:
            stats: Current stats
            tokens_used: Tokens consumed this iteration

        Returns:
            Updated stats
        """
        stats.iteration += 1
        stats.tokens_used += tokens_used

        now = datetime.utcnow()
        if stats.start_time:
            start = datetime.fromisoformat(stats.start_time)
            stats.runtime_seconds = (now - start).total_seconds()

        stats.last_update = now.isoformat()

        self.check_limits(stats, tokens_used)
        self._save_stats(stats)

        return stats

    def get_stats(self, session_id: str) -> Optional[SessionStats]:
        """Get current session stats."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, iteration, tokens_used, runtime_seconds, start_time, last_update, termination_reason
            FROM session_stats
            WHERE session_id = ?
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return SessionStats(
            session_id=row[0],
            iteration=row[1],
            tokens_used=row[2],
            runtime_seconds=row[3],
            start_time=row[4],
            last_update=row[5],
        )

    def force_terminate(self, session_id: str, reason: TerminationReason):
        """Force session termination."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE session_stats 
                SET termination_reason = ?, last_update = ?
                WHERE session_id = ?
            """,
                (reason.value, datetime.utcnow().isoformat(), session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _save_stats(self, stats: SessionStats):
        """Save session stats to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO session_stats 
                (session_id, iteration, tokens_used, runtime_seconds, start_time, last_update)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    stats.session_id,
                    stats.iteration,
                    stats.tokens_used,
                    stats.runtime_seconds,
                    stats.start_time,
                    stats.last_update,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_termination_reason(self, session_id: str) -> Optional[str]:
        """Get reason for session termination."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT termination_reason FROM session_stats WHERE session_id = ?
        """,
            (session_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None


_global_session_guard: Optional[SessionGuard] = None


def get_session_guard(caps: SessionCaps = None) -> SessionGuard:
    """Get global session guard instance."""
    global _global_session_guard
    if _global_session_guard is None:
        _global_session_guard = SessionGuard(caps)
    return _global_session_guard
