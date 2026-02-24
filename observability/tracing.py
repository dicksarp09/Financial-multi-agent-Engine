from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
import json
import uuid


@dataclass
class Span:
    """Distributed tracing span."""

    span_id: str
    parent_id: Optional[str]
    session_id: str
    agent_name: str
    span_type: str  # "agent", "llm", "retrieval", "tool"
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tracing:
    """
    Distributed tracing for multi-agent system.

    Tracks:
    - Session root spans
    - Agent execution spans
    - LLM call spans
    - Retrieval call spans
    - Tool call spans
    """

    def __init__(self, db_path: str = "event_log.db"):
        self.db_path = db_path
        self._current_spans: Dict[str, Span] = {}
        self._init_table()

    def _init_table(self):
        """Initialize tracing table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                span_id TEXT NOT NULL UNIQUE,
                parent_id TEXT,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                span_type TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_ms REAL,
                input_data TEXT,
                output_data TEXT,
                error TEXT,
                correlation_id TEXT,
                metadata TEXT,
                UNIQUE(span_id, session_id)
            )
        """)
        conn.commit()
        conn.close()

    def start_span(
        self,
        session_id: str,
        agent_name: str,
        span_type: str,
        parent_id: Optional[str] = None,
        input_data: Optional[Dict] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Start a new tracing span."""
        span_id = str(uuid.uuid4())

        span = Span(
            span_id=span_id,
            parent_id=parent_id,
            session_id=session_id,
            agent_name=agent_name,
            span_type=span_type,
            start_time=datetime.utcnow().isoformat(),
            input_data=json.dumps(input_data) if input_data else None,
            correlation_id=correlation_id or str(uuid.uuid4()),
            metadata=metadata or {},
        )

        self._current_spans[span_id] = span
        return span_id

    def end_span(
        self,
        span_id: str,
        output_data: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> Span:
        """End a tracing span."""
        if span_id not in self._current_spans:
            raise ValueError(f"Span {span_id} not found")

        span = self._current_spans[span_id]
        span.end_time = datetime.utcnow().isoformat()

        start = datetime.fromisoformat(span.start_time)
        end = datetime.fromisoformat(span.end_time)
        span.duration_ms = (end - start).total_seconds() * 1000

        span.output_data = json.dumps(output_data) if output_data else None
        span.error = error

        self._save_span(span)
        del self._current_spans[span_id]

        return span

    def _save_span(self, span: Span):
        """Save span to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO traces 
                (span_id, parent_id, session_id, agent_name, span_type, start_time, end_time, duration_ms, input_data, output_data, error, correlation_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    span.span_id,
                    span.parent_id,
                    span.session_id,
                    span.agent_name,
                    span.span_type,
                    span.start_time,
                    span.end_time,
                    span.duration_ms,
                    span.input_data,
                    span.output_data,
                    span.error,
                    span.correlation_id,
                    json.dumps(span.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_session_spans(self, session_id: str) -> List[Span]:
        """Get all spans for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT span_id, parent_id, session_id, agent_name, span_type, start_time, end_time, duration_ms, input_data, output_data, error, correlation_id, metadata
            FROM traces
            WHERE session_id = ?
            ORDER BY start_time ASC
        """,
            (session_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            Span(
                span_id=r[0],
                parent_id=r[1],
                session_id=r[2],
                agent_name=r[3],
                span_type=r[4],
                start_time=r[5],
                end_time=r[6],
                duration_ms=r[7],
                input_data=r[8],
                output_data=r[9],
                error=r[10],
                correlation_id=r[11],
                metadata=json.loads(r[12]) if r[12] else {},
            )
            for r in rows
        ]

    def replay_session(self, session_id: str) -> List[Dict]:
        """Replay session with all spans."""
        spans = self.get_session_spans(session_id)

        replay = []
        for span in spans:
            replay.append(
                {
                    "span_id": span.span_id,
                    "parent_id": span.parent_id,
                    "agent": span.agent_name,
                    "type": span.span_type,
                    "start": span.start_time,
                    "duration_ms": span.duration_ms,
                    "input": json.loads(span.input_data) if span.input_data else None,
                    "output": json.loads(span.output_data)
                    if span.output_data
                    else None,
                    "error": span.error,
                }
            )

        return replay


_global_tracing: Optional[Tracing] = None


def get_tracing(db_path: str = "event_log.db") -> Tracing:
    """Get global tracing instance."""
    global _global_tracing
    if _global_tracing is None:
        _global_tracing = Tracing(db_path)
    return _global_tracing
