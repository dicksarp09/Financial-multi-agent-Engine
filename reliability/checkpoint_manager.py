from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
import json


@dataclass
class Checkpoint:
    """Checkpoint containing session state."""

    session_id: str
    user_id: str
    current_state: str
    completed_agents: List[str]
    partial_outputs: Dict[str, Any]
    iteration: int
    timestamp: str
    is_complete: bool = False


class CheckpointManager:
    """
    Manages checkpointing for session recovery.

    Saves state after each successful agent execution.
    Allows resume from last checkpoint on crash.
    """

    def __init__(self, db_path: str = "event_log.db"):
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        """Initialize checkpoint table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                current_state TEXT NOT NULL,
                completed_agents TEXT NOT NULL,
                partial_outputs TEXT NOT NULL,
                iteration INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                is_complete INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def save_checkpoint(
        self,
        session_id: str,
        user_id: str,
        current_state: str,
        completed_agents: List[str],
        partial_outputs: Dict[str, Any],
        iteration: int,
        is_complete: bool = False,
    ) -> bool:
        """
        Save checkpoint for session.

        Args:
            session_id: Session identifier
            user_id: User identifier
            current_state: Current workflow state
            completed_agents: List of completed agent names
            partial_outputs: Agent outputs
            iteration: Current iteration
            is_complete: Whether workflow is complete

        Returns:
            True if saved
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO checkpoints 
                (session_id, user_id, current_state, completed_agents, partial_outputs, iteration, timestamp, is_complete)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    user_id,
                    current_state,
                    json.dumps(completed_agents),
                    json.dumps(partial_outputs),
                    iteration,
                    datetime.utcnow().isoformat(),
                    1 if is_complete else 0,
                ),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def load_checkpoint(self, session_id: str) -> Optional[Checkpoint]:
        """
        Load checkpoint for session.

        Args:
            session_id: Session identifier

        Returns:
            Checkpoint or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, user_id, current_state, completed_agents, partial_outputs, iteration, timestamp, is_complete
            FROM checkpoints
            WHERE session_id = ?
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Checkpoint(
            session_id=row[0],
            user_id=row[1],
            current_state=row[2],
            completed_agents=json.loads(row[3]),
            partial_outputs=json.loads(row[4]),
            iteration=row[5],
            timestamp=row[6],
            is_complete=bool(row[7]),
        )

    def has_checkpoint(self, session_id: str) -> bool:
        """Check if checkpoint exists for session."""
        checkpoint = self.load_checkpoint(session_id)
        return checkpoint is not None and not checkpoint.is_complete

    def get_incomplete_sessions(self) -> List[str]:
        """Get list of incomplete session IDs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id FROM checkpoints WHERE is_complete = 0
        """)
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def mark_complete(self, session_id: str) -> bool:
        """Mark session as complete."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE checkpoints SET is_complete = 1, timestamp = ?
                WHERE session_id = ?
            """,
                (datetime.utcnow().isoformat(), session_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def delete_checkpoint(self, session_id: str) -> bool:
        """Delete checkpoint for session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM checkpoints WHERE session_id = ?", (session_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def get_checkpoint_history(self, user_id: str, limit: int = 10) -> List[Checkpoint]:
        """Get checkpoint history for user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, user_id, current_state, completed_agents, partial_outputs, iteration, timestamp, is_complete
            FROM checkpoints
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (user_id, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            Checkpoint(
                session_id=r[0],
                user_id=r[1],
                current_state=r[2],
                completed_agents=json.loads(r[3]),
                partial_outputs=json.loads(r[4]),
                iteration=r[5],
                timestamp=r[6],
                is_complete=bool(r[7]),
            )
            for r in rows
        ]


_global_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get global checkpoint manager instance."""
    global _global_checkpoint_manager
    if _global_checkpoint_manager is None:
        _global_checkpoint_manager = CheckpointManager()
    return _global_checkpoint_manager
