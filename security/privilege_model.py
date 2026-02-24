from enum import Enum
from typing import Dict, Optional, List
from pydantic import BaseModel, Field, ConfigDict
import sqlite3
from datetime import datetime


class ActionType(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    WRITE_DB = "write_db"
    CALL_LLM = "call_llm"
    USE_RETRIEVAL = "use_retrieval"
    EXECUTE_TOOL = "execute_tool"
    APPROVE_ACTION = "approve_action"


class AgentPermission(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    can_read_files: bool = Field(
        default=False, description="Can read files from filesystem"
    )
    can_write_files: bool = Field(
        default=False, description="Can write files to filesystem"
    )
    can_write_db: bool = Field(default=False, description="Can write to database")
    can_call_llm: bool = Field(default=False, description="Can call LLM API")
    can_use_retrieval: bool = Field(default=False, description="Can use retrieval/RAG")
    allowed_file_paths: List[str] = Field(
        default_factory=list, description="Whitelisted file paths"
    )
    max_llm_tokens: int = Field(
        default=0, description="Max tokens for LLM calls (0=disabled)"
    )

    def can_perform(self, action: ActionType) -> bool:
        """Check if this permission allows the given action."""
        action_map = {
            ActionType.READ_FILE: self.can_read_files,
            ActionType.WRITE_FILE: self.can_write_files,
            ActionType.WRITE_DB: self.can_write_db,
            ActionType.CALL_LLM: self.can_call_llm,
            ActionType.USE_RETRIEVAL: self.can_use_retrieval,
        }
        return action_map.get(action, False)

    def can_read_path(self, file_path: str) -> bool:
        """Check if a specific file path can be read."""
        if not self.can_read_files:
            return False
        if not self.allowed_file_paths:
            return True
        return any(file_path.startswith(allowed) for allowed in self.allowed_file_paths)


AGENT_PERMISSIONS: Dict[str, AgentPermission] = {
    "orchestrator": AgentPermission(
        can_read_files=True,
        can_write_files=False,
        can_write_db=False,
        can_call_llm=False,
        can_use_retrieval=False,
        allowed_file_paths=[],
        max_llm_tokens=0,
    ),
    "ingestion": AgentPermission(
        can_read_files=True,
        can_write_files=True,
        can_write_db=True,
        can_call_llm=False,
        can_use_retrieval=False,
        allowed_file_paths=["*.json", "*.csv"],
        max_llm_tokens=0,
    ),
    "categorization": AgentPermission(
        can_read_files=True,
        can_write_files=False,
        can_write_db=False,
        can_call_llm=True,
        can_use_retrieval=False,
        allowed_file_paths=[],
        max_llm_tokens=2048,
    ),
    "analysis": AgentPermission(
        can_read_files=True,
        can_write_files=False,
        can_write_db=False,
        can_call_llm=False,
        can_use_retrieval=False,
        allowed_file_paths=[],
        max_llm_tokens=0,
    ),
    "budgeting": AgentPermission(
        can_read_files=True,
        can_write_files=False,
        can_write_db=False,
        can_call_llm=True,
        can_use_retrieval=True,
        allowed_file_paths=[],
        max_llm_tokens=1024,
    ),
    "evaluation": AgentPermission(
        can_read_files=True,
        can_write_files=False,
        can_write_db=False,
        can_call_llm=False,
        can_use_retrieval=True,
        allowed_file_paths=[],
        max_llm_tokens=0,
    ),
    "reporting": AgentPermission(
        can_read_files=True,
        can_write_files=True,
        can_write_db=False,
        can_call_llm=False,
        can_use_retrieval=False,
        allowed_file_paths=[],
        max_llm_tokens=0,
    ),
    "retrieval": AgentPermission(
        can_read_files=False,
        can_write_files=False,
        can_write_db=False,
        can_call_llm=False,
        can_use_retrieval=True,
        allowed_file_paths=[],
        max_llm_tokens=0,
    ),
}


class SecurityException(Exception):
    """Raised when an agent attempts an unauthorized action."""

    def __init__(self, agent_name: str, action: ActionType, message: str = ""):
        self.agent_name = agent_name
        self.action = action
        self.message = (
            message
            or f"Agent '{agent_name}' is not authorized to perform '{action.value}'"
        )
        super().__init__(self.message)


class PrivilegeModel:
    """Manages agent permissions and validates actions."""

    def __init__(self, db_path: str = "event_log.db"):
        self.db_path = db_path
        self._init_security_table()

    def _init_security_table(self):
        """Initialize security events table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                action_attempted TEXT NOT NULL,
                decision TEXT NOT NULL,
                severity_level INTEGER NOT NULL,
                details TEXT,
                UNIQUE(timestamp, session_id, agent_name, action_attempted)
            )
        """)
        conn.commit()
        conn.close()

    def get_agent_permission(self, agent_name: str) -> AgentPermission:
        """Get permissions for an agent."""
        return AGENT_PERMISSIONS.get(agent_name, AgentPermission())

    def validate_agent_action(
        self,
        agent_name: str,
        action: ActionType,
        session_id: str,
        details: Optional[Dict] = None,
    ) -> bool:
        """
        Validate if an agent can perform an action.

        Args:
            agent_name: Name of the agent
            action: The action to validate
            session_id: Current session ID
            details: Additional details about the action

        Returns:
            True if authorized

        Raises:
            SecurityException: If action is not authorized
        """
        permission = self.get_agent_permission(agent_name)

        if permission.can_perform(action):
            self._log_security_event(
                session_id=session_id,
                agent_name=agent_name,
                violation_type="none",
                action_attempted=action.value,
                decision="allowed",
                severity_level=0,
                details=details,
            )
            return True

        self._log_security_event(
            session_id=session_id,
            agent_name=agent_name,
            violation_type="unauthorized_action",
            action_attempted=action.value,
            decision="denied",
            severity_level=3,
            details=details,
        )

        raise SecurityException(agent_name, action)

    def validate_llm_call(
        self, agent_name: str, session_id: str, token_count: int
    ) -> bool:
        """
        Validate LLM call with token limit check.

        Args:
            agent_name: Name of the agent
            session_id: Current session ID
            token_count: Number of tokens in the request

        Returns:
            True if authorized

        Raises:
            SecurityException: If not authorized or token limit exceeded
        """
        permission = self.get_agent_permission(agent_name)

        if not permission.can_call_llm:
            self._log_security_event(
                session_id=session_id,
                agent_name=agent_name,
                violation_type="unauthorized_llm_call",
                action_attempted=ActionType.CALL_LLM.value,
                decision="denied",
                severity_level=3,
                details={"reason": "LLM calls disabled for this agent"},
            )
            raise SecurityException(agent_name, ActionType.CALL_LLM)

        if permission.max_llm_tokens > 0 and token_count > permission.max_llm_tokens:
            self._log_security_event(
                session_id=session_id,
                agent_name=agent_name,
                violation_type="token_limit_exceeded",
                action_attempted=ActionType.CALL_LLM.value,
                decision="denied",
                severity_level=2,
                details={
                    "token_count": token_count,
                    "max_allowed": permission.max_llm_tokens,
                },
            )
            raise SecurityException(
                agent_name,
                ActionType.CALL_LLM,
                f"Token count {token_count} exceeds limit {permission.max_llm_tokens}",
            )

        self._log_security_event(
            session_id=session_id,
            agent_name=agent_name,
            violation_type="none",
            action_attempted=ActionType.CALL_LLM.value,
            decision="allowed",
            severity_level=0,
            details={"token_count": token_count},
        )

        return True

    def validate_file_read(
        self, agent_name: str, file_path: str, session_id: str
    ) -> bool:
        """Validate file read access."""
        permission = self.get_agent_permission(agent_name)

        if not permission.can_read_files:
            self._log_security_event(
                session_id=session_id,
                agent_name=agent_name,
                violation_type="unauthorized_file_read",
                action_attempted=ActionType.READ_FILE.value,
                decision="denied",
                severity_level=3,
                details={"file_path": file_path, "reason": "Read permission disabled"},
            )
            raise SecurityException(agent_name, ActionType.READ_FILE)

        if not permission.can_read_path(file_path):
            self._log_security_event(
                session_id=session_id,
                agent_name=agent_name,
                violation_type="path_violation",
                action_attempted=ActionType.READ_FILE.value,
                decision="denied",
                severity_level=3,
                details={"file_path": file_path, "reason": "Path not whitelisted"},
            )
            raise SecurityException(
                agent_name,
                ActionType.READ_FILE,
                f"Path '{file_path}' not in allowed paths",
            )

        self._log_security_event(
            session_id=session_id,
            agent_name=agent_name,
            violation_type="none",
            action_attempted=ActionType.READ_FILE.value,
            decision="allowed",
            severity_level=0,
            details={"file_path": file_path},
        )

        return True

    def _log_security_event(
        self,
        session_id: str,
        agent_name: str,
        violation_type: str,
        action_attempted: str,
        decision: str,
        severity_level: int,
        details: Optional[Dict] = None,
    ):
        """Log security event to database."""
        import json

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO security_events 
                (timestamp, session_id, agent_name, violation_type, action_attempted, decision, severity_level, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.utcnow().isoformat(),
                    session_id,
                    agent_name,
                    violation_type,
                    action_attempted,
                    decision,
                    severity_level,
                    json.dumps(details) if details else None,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()


_global_privilege_model: Optional[PrivilegeModel] = None


def get_privilege_model() -> PrivilegeModel:
    """Get global privilege model instance."""
    global _global_privilege_model
    if _global_privilege_model is None:
        _global_privilege_model = PrivilegeModel()
    return _global_privilege_model


def validate_agent_action(
    agent_name: str, action: ActionType, session_id: str, details: Optional[Dict] = None
) -> bool:
    """Convenience function to validate agent action."""
    return get_privilege_model().validate_agent_action(
        agent_name, action, session_id, details
    )
