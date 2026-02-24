from enum import Enum
from typing import Dict, Optional, List
from pydantic import BaseModel, Field, ConfigDict
import sqlite3
from datetime import datetime
import json


class ApprovalStatus(Enum):
    """Approval request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalType(Enum):
    """Type of approval required."""

    HIGH_VALUE_TRANSACTION = "high_value_transaction"
    ANOMALY_DETECTED = "anomaly_detected"
    HIGH_RISK_TRANSACTION = "high_risk_transaction"
    BUDGET_OVERRIDE = "budget_override"
    SYSTEM_ACTION = "system_action"


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    session_id: str = Field(..., description="Session identifier")
    request_id: str = Field(..., description="Unique request ID")
    approval_type: ApprovalType = Field(..., description="Type of approval")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    reason: str = Field(..., description="Reason for approval")
    details: Dict = Field(default_factory=dict, description="Additional details")
    requested_at: str = Field(..., description="Request timestamp")
    approved_at: Optional[str] = Field(default=None, description="Approval timestamp")
    approved_by: Optional[str] = Field(default=None, description="Approver ID")
    approver_comment: Optional[str] = Field(
        default=None, description="Approver comment"
    )


class ApprovalThreshold(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    approval_type: ApprovalType
    threshold_value: float
    enabled: bool = True


DEFAULT_THRESHOLDS = [
    ApprovalThreshold(
        approval_type=ApprovalType.HIGH_VALUE_TRANSACTION,
        threshold_value=500.0,
        enabled=True,
    ),
    ApprovalThreshold(
        approval_type=ApprovalType.ANOMALY_DETECTED, threshold_value=0.8, enabled=True
    ),
    ApprovalThreshold(
        approval_type=ApprovalType.HIGH_RISK_TRANSACTION,
        threshold_value=0.7,
        enabled=True,
    ),
]


class ApprovalException(Exception):
    """Raised when approval is required but not granted."""

    def __init__(self, request_id: str, message: str):
        self.request_id = request_id
        super().__init__(message)


class ApprovalManager:
    """
    Human approval management system.

    Features:
    - Threshold-based approval triggers
    - Immutable approval decisions
    - Persistent state across crashes
    - Audit logging
    """

    def __init__(
        self,
        db_path: str = "event_log.db",
        thresholds: Optional[List[ApprovalThreshold]] = None,
    ):
        self.db_path = db_path
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self._init_approval_table()

    def _init_approval_table(self):
        """Initialize approval requests table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                approval_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reason TEXT NOT NULL,
                details TEXT,
                requested_at TEXT NOT NULL,
                approved_at TEXT,
                approved_by TEXT,
                approver_comment TEXT,
                UNIQUE(request_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_approvals 
            ON approval_requests(session_id, status)
        """)

        conn.commit()
        conn.close()

    def check_threshold(self, approval_type: ApprovalType, value: float) -> bool:
        """
        Check if a value exceeds a threshold.

        Args:
            approval_type: Type of approval
            value: Value to check

        Returns:
            True if approval is required
        """
        for threshold in self.thresholds:
            if threshold.approval_type == approval_type and threshold.enabled:
                return value > threshold.threshold_value
        return False

    def requires_approval(self, approval_type: ApprovalType, value: float) -> bool:
        """Check if approval is required for given type and value."""
        return self.check_threshold(approval_type, value)

    def request_approval(
        self,
        session_id: str,
        approval_type: ApprovalType,
        reason: str,
        details: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Request human approval.

        Args:
            session_id: Current session
            approval_type: Type of approval needed
            reason: Reason for approval
            details: Additional details
            request_id: Optional request ID (generated if not provided)

        Returns:
            ApprovalRequest
        """
        import uuid

        request = ApprovalRequest(
            session_id=session_id,
            request_id=request_id or str(uuid.uuid4()),
            approval_type=approval_type,
            status=ApprovalStatus.PENDING,
            reason=reason,
            details=details or {},
            requested_at=datetime.utcnow().isoformat(),
        )

        self._persist_request(request)

        return request

    def _persist_request(self, request: ApprovalRequest):
        """Persist approval request to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO approval_requests 
                (session_id, request_id, approval_type, status, reason, details, requested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    request.session_id,
                    request.request_id,
                    request.approval_type.value,
                    request.status.value,
                    request.reason,
                    json.dumps(request.details),
                    request.requested_at,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def approve(
        self, request_id: str, approved_by: str, comment: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Approve a request.

        Args:
            request_id: Request ID to approve
            approved_by: ID of approver
            comment: Optional comment

        Returns:
            Updated ApprovalRequest

        Raises:
            ApprovalException: If request not found
        """
        return self._update_status(
            request_id, ApprovalStatus.APPROVED, approved_by, comment
        )

    def reject(
        self, request_id: str, approved_by: str, comment: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Reject a request.

        Args:
            request_id: Request ID to reject
            approved_by: ID of rejecter
            comment: Optional comment

        Returns:
            Updated ApprovalRequest

        Raises:
            ApprovalException: If request not found
        """
        return self._update_status(
            request_id, ApprovalStatus.REJECTED, approved_by, comment
        )

    def cancel(self, request_id: str) -> ApprovalRequest:
        """
        Cancel a pending request.

        Args:
            request_id: Request ID to cancel

        Returns:
            Updated ApprovalRequest
        """
        return self._update_status(request_id, ApprovalStatus.CANCELLED, None, None)

    def _update_status(
        self,
        request_id: str,
        status: ApprovalStatus,
        approved_by: Optional[str],
        comment: Optional[str],
    ) -> ApprovalRequest:
        """Update request status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT session_id, approval_type, reason, details, requested_at, status
            FROM approval_requests
            WHERE request_id = ?
        """,
            (request_id,),
        )

        row = cursor.fetchone()

        if not row:
            conn.close()
            raise ApprovalException(request_id, "Request not found")

        current_status = row[5]
        if current_status != ApprovalStatus.PENDING.value:
            conn.close()
            raise ApprovalException(request_id, f"Request already {current_status}")

        approved_at = (
            datetime.utcnow().isoformat()
            if status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]
            else None
        )

        cursor.execute(
            """
            UPDATE approval_requests
            SET status = ?, approved_at = ?, approved_by = ?, approver_comment = ?
            WHERE request_id = ?
        """,
            (status.value, approved_at, approved_by, comment, request_id),
        )

        conn.commit()
        conn.close()

        return ApprovalRequest(
            session_id=row[0],
            request_id=request_id,
            approval_type=ApprovalType(row[1]),
            status=status,
            reason=row[2],
            details=json.loads(row[3]) if row[3] else {},
            requested_at=row[4],
            approved_at=approved_at,
            approved_by=approved_by,
            approver_comment=comment,
        )

    def get_pending_requests(self, session_id: str) -> List[ApprovalRequest]:
        """Get all pending requests for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, request_id, approval_type, status, reason, details, requested_at
            FROM approval_requests
            WHERE session_id = ? AND status = 'pending'
            ORDER BY requested_at ASC
        """,
            (session_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            ApprovalRequest(
                session_id=row[0],
                request_id=row[1],
                approval_type=ApprovalType(row[2]),
                status=ApprovalStatus(row[3]),
                reason=row[4],
                details=json.loads(row[5]) if row[5] else {},
                requested_at=row[6],
            )
            for row in rows
        ]

    def get_request_status(self, request_id: str) -> Optional[ApprovalStatus]:
        """Get current status of a request."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT status FROM approval_requests WHERE request_id = ?
        """,
            (request_id,),
        )

        row = cursor.fetchone()
        conn.close()

        return ApprovalStatus(row[0]) if row else None

    def is_approved(self, request_id: str) -> bool:
        """Check if a request is approved."""
        status = self.get_request_status(request_id)
        return status == ApprovalStatus.APPROVED if status else False


_global_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """Get global approval manager instance."""
    global _global_approval_manager
    if _global_approval_manager is None:
        _global_approval_manager = ApprovalManager()
    return _global_approval_manager


def request_approval(
    session_id: str,
    approval_type: ApprovalType,
    reason: str,
    details: Optional[Dict] = None,
) -> ApprovalRequest:
    """Convenience function to request approval."""
    return get_approval_manager().request_approval(
        session_id, approval_type, reason, details
    )


def approve_request(
    request_id: str, approved_by: str, comment: Optional[str] = None
) -> ApprovalRequest:
    """Convenience function to approve a request."""
    return get_approval_manager().approve(request_id, approved_by, comment)


def reject_request(
    request_id: str, approved_by: str, comment: Optional[str] = None
) -> ApprovalRequest:
    """Convenience function to reject a request."""
    return get_approval_manager().reject(request_id, approved_by, comment)
