import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path


LOG_DB_PATH = "event_log.db"
LOG_JSON_PATH = "event_log.json"


@dataclass
class LogEntry:
    timestamp: str
    session_id: str
    state: str
    agent_name: str
    input_payload: str
    output_payload: str
    error_flag: bool = False
    token_usage: Optional[int] = None


class LoggingSystem:
    def __init__(self, db_path: str = LOG_DB_PATH, json_path: str = LOG_JSON_PATH):
        self.db_path = db_path
        self.json_path = json_path
        self._init_database()
        self._init_json_log()

    def _init_database(self):
        """Initialize SQLite database with events table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                state TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                input_payload TEXT NOT NULL,
                output_payload TEXT NOT NULL,
                error_flag INTEGER NOT NULL DEFAULT 0,
                token_usage INTEGER,
                UNIQUE(timestamp, session_id, agent_name)
            )
        """)
        conn.commit()
        conn.close()

    def _init_json_log(self):
        """Initialize JSON log file if it doesn't exist."""
        if not os.path.exists(self.json_path):
            with open(self.json_path, "w") as f:
                json.dump([], f)

    def log_event(
        self,
        session_id: str,
        state: str,
        agent_name: str,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        error_flag: bool = False,
        token_usage: Optional[int] = None,
    ) -> LogEntry:
        """Log an event to both SQLite and JSON."""
        timestamp = datetime.utcnow().isoformat()

        entry = LogEntry(
            timestamp=timestamp,
            session_id=session_id,
            state=state,
            agent_name=agent_name,
            input_payload=json.dumps(input_payload, sort_keys=True),
            output_payload=json.dumps(output_payload, sort_keys=True),
            error_flag=error_flag,
            token_usage=token_usage,
        )

        self._log_to_sqlite(entry)
        self._log_to_json(entry)

        return entry

    def _log_to_sqlite(self, entry: LogEntry):
        """Append event to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO events (timestamp, session_id, state, agent_name, input_payload, output_payload, error_flag, token_usage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.timestamp,
                    entry.session_id,
                    entry.state,
                    entry.agent_name,
                    entry.input_payload,
                    entry.output_payload,
                    1 if entry.error_flag else 0,
                    entry.token_usage,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def _log_to_json(self, entry: LogEntry):
        """Append event to JSON file."""
        with open(self.json_path, "r") as f:
            logs = json.load(f)

        logs.append(asdict(entry))

        with open(self.json_path, "w") as f:
            json.dump(logs, f, indent=2)

    def get_session_events(self, session_id: str) -> List[LogEntry]:
        """Get all events for a specific session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT timestamp, session_id, state, agent_name, input_payload, output_payload, error_flag, token_usage
            FROM events
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """,
            (session_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            LogEntry(
                timestamp=row[0],
                session_id=row[1],
                state=row[2],
                agent_name=row[3],
                input_payload=row[4],
                output_payload=row[5],
                error_flag=bool(row[6]),
                token_usage=row[7],
            )
            for row in rows
        ]

    def replay_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Replay all events for a session in order."""
        events = self.get_session_events(session_id)

        replay_data = []
        for event in events:
            replay_data.append(
                {
                    "timestamp": event.timestamp,
                    "state": event.state,
                    "agent": event.agent_name,
                    "input": json.loads(event.input_payload),
                    "output": json.loads(event.output_payload),
                    "error": event.error_flag,
                }
            )

        return replay_data

    def get_session_count(self) -> int:
        """Get total number of unique sessions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM events")
        count = cursor.fetchone()[0]
        conn.close()
        return count


_global_logger: Optional[LoggingSystem] = None


def get_logger() -> LoggingSystem:
    """Get global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = LoggingSystem()
    return _global_logger


def log_event(
    session_id: str,
    state: str,
    agent_name: str,
    input_payload: Dict[str, Any],
    output_payload: Dict[str, Any],
    error_flag: bool = False,
    token_usage: Optional[int] = None,
) -> LogEntry:
    """Convenience function to log an event."""
    return get_logger().log_event(
        session_id=session_id,
        state=state,
        agent_name=agent_name,
        input_payload=input_payload,
        output_payload=output_payload,
        error_flag=error_flag,
        token_usage=token_usage,
    )


def replay_session(session_id: str) -> List[Dict[str, Any]]:
    """Convenience function to replay a session."""
    return get_logger().replay_session(session_id)
