from typing import Dict, Any, List, Optional
import re
import sqlite3
import json
from datetime import datetime


PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "ssn": r"\b\d{3}[-]?\d{2}[-]?\d{4}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "bank_account": r"\b\d{8,17}\b",
}


class ComplianceLogger:
    """
    Immutable compliance logging with PII detection.

    Logs:
    - Transaction categorization
    - Budget decisions
    - Human approvals
    - LLM outputs

    Features:
    - PII detection and redaction
    - Append-only storage
    - Audit trail
    """

    def __init__(self, db_path: str = "event_log.db"):
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        """Initialize compliance logging table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id TEXT NOT NULL UNIQUE,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                log_type TEXT NOT NULL,
                raw_data TEXT,
                redacted_data TEXT,
                pii_detected INTEGER DEFAULT 0,
                pii_types TEXT,
                timestamp TEXT NOT NULL,
                UNIQUE(session_id, log_type, timestamp)
            )
        """)
        conn.commit()
        conn.close()

    def detect_pii(self, data: str) -> List[str]:
        """Detect PII in data."""
        detected = []
        for pii_type, pattern in PII_PATTERNS.items():
            if re.search(pattern, data, re.IGNORECASE):
                detected.append(pii_type)
        return detected

    def redact_pii(self, data: str) -> str:
        """Redact PII from data."""
        redacted = data

        for pii_type, pattern in PII_PATTERNS.items():
            if pii_type == "credit_card":
                redacted = re.sub(
                    pattern, lambda m: "[CC_REDACTED]", redacted, flags=re.IGNORECASE
                )
            elif pii_type == "ssn":
                redacted = re.sub(
                    pattern, lambda m: "[SSN_REDACTED]", redacted, flags=re.IGNORECASE
                )
            elif pii_type == "email":
                redacted = re.sub(pattern, lambda m: "[EMAIL_REDACTED]", redacted)
            elif pii_type == "phone":
                redacted = re.sub(pattern, lambda m: "[PHONE_REDACTED]", redacted)

        return redacted

    def log(
        self,
        session_id: str,
        user_id: str,
        agent_name: str,
        log_type: str,
        raw_data: Dict[str, Any],
        include_raw: bool = False,
    ) -> str:
        """
        Log with automatic PII detection and redaction.

        Args:
            session_id: Session identifier
            user_id: User identifier
            agent_name: Agent that produced the log
            log_type: Type of log (categorization, budget, approval, llm_output)
            raw_data: Data to log
            include_raw: Whether to include raw data (default False for security)

        Returns:
            Log ID
        """
        import uuid

        log_id = str(uuid.uuid4())

        raw_json = json.dumps(raw_data, sort_keys=True) if raw_data else ""

        pii_types = self.detect_pii(raw_json)
        redacted = self.redact_pii(raw_json)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO compliance_logs 
                (log_id, session_id, user_id, agent_name, log_type, raw_data, redacted_data, pii_detected, pii_types, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    log_id,
                    session_id,
                    user_id,
                    agent_name,
                    log_type,
                    raw_json if include_raw else None,
                    redacted,
                    1 if pii_types else 0,
                    json.dumps(pii_types),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return log_id

    def log_categorization(
        self,
        session_id: str,
        user_id: str,
        transaction_id: str,
        description: str,
        category: str,
        confidence: float,
    ):
        """Log categorization decision."""
        return self.log(
            session_id=session_id,
            user_id=user_id,
            agent_name="categorization",
            log_type="categorization",
            raw_data={
                "transaction_id": transaction_id,
                "description": description,
                "category": category,
                "confidence": confidence,
            },
        )

    def log_budget_decision(
        self,
        session_id: str,
        user_id: str,
        category: str,
        suggested: float,
        reasoning: str,
    ):
        """Log budget decision."""
        return self.log(
            session_id=session_id,
            user_id=user_id,
            agent_name="budgeting",
            log_type="budget_decision",
            raw_data={
                "category": category,
                "suggested_budget": suggested,
                "reasoning": reasoning,
            },
        )

    def log_approval(
        self,
        session_id: str,
        user_id: str,
        request_id: str,
        decision: str,
        approver: str,
    ):
        """Log human approval."""
        return self.log(
            session_id=session_id,
            user_id="system",
            agent_name="approval_manager",
            log_type="approval",
            raw_data={
                "request_id": request_id,
                "decision": decision,
                "approver": approver,
            },
        )

    def log_llm_output(
        self, session_id: str, user_id: str, agent_name: str, prompt: str, response: str
    ):
        """Log LLM output."""
        return self.log(
            session_id=session_id,
            user_id=user_id,
            agent_name=agent_name,
            log_type="llm_output",
            raw_data={"prompt_length": len(prompt), "response_length": len(response)},
        )

    def get_logs(
        self, session_id: str, log_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """Get compliance logs for session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if log_type:
            cursor.execute(
                """
                SELECT log_id, session_id, user_id, agent_name, log_type, redacted_data, pii_detected, pii_types, timestamp
                FROM compliance_logs
                WHERE session_id = ? AND log_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (session_id, log_type, limit),
            )
        else:
            cursor.execute(
                """
                SELECT log_id, session_id, user_id, agent_name, log_type, redacted_data, pii_detected, pii_types, timestamp
                FROM compliance_logs
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (session_id, limit),
            )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "log_id": r[0],
                "session_id": r[1],
                "user_id": r[2],
                "agent": r[3],
                "type": r[4],
                "data": json.loads(r[5]) if r[5] else None,
                "pii_detected": bool(r[6]),
                "pii_types": json.loads(r[7]) if r[7] else [],
                "timestamp": r[8],
            }
            for r in rows
        ]

    def audit_trail(self, session_id: str) -> List[Dict]:
        """Get complete audit trail for session."""
        return self.get_logs(session_id, limit=1000)


_global_compliance_logger: Optional[ComplianceLogger] = None


def get_compliance_logger() -> ComplianceLogger:
    """Get global compliance logger instance."""
    global _global_compliance_logger
    if _global_compliance_logger is None:
        _global_compliance_logger = ComplianceLogger()
    return _global_compliance_logger
