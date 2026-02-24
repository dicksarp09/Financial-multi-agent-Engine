from typing import Callable, Any, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime
import time
import random
import sqlite3
import json
from enum import Enum


class RetryableError(Exception):
    """Base class for errors that can be retried."""

    pass


class LLMTimeoutError(RetryableError):
    """LLM API timeout."""

    pass


class DatabaseLockError(RetryableError):
    """Database lock contention."""

    pass


class NetworkError(RetryableError):
    """Network connectivity issue."""

    pass


class NonRetryableError(Exception):
    """Base class for errors that should not be retried."""

    pass


class SchemaValidationError(NonRetryableError):
    """Schema validation failure."""

    pass


class CorruptedDataError(NonRetryableError):
    """Corrupted input data."""

    pass


class LogicViolationError(NonRetryableError):
    """Business logic violation."""

    pass


class SecurityViolationError(NonRetryableError):
    """Security policy violation."""

    pass


class PermanentFailureError(Exception):
    """Raised when max retries exceeded."""

    def __init__(self, original_error: Exception, attempts: int, message: str = ""):
        self.original_error = original_error
        self.attempts = attempts
        self.message = (
            message or f"Permanent failure after {attempts} attempts: {original_error}"
        )
        super().__init__(self.message)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        super().__init__(f"Circuit breaker is open for agent: {agent_name}")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: float = 0.5
    retryable_errors: tuple = (RetryableError,)


@dataclass
class RetryAttempt:
    """Record of a retry attempt."""

    attempt_number: int
    timestamp: str
    error_type: str
    error_message: str
    delay_used: float
    success: bool


class RetryManager:
    """
    Manages retry logic with exponential backoff and jitter.

    Key principles:
    - Only retries RetryableError types
    - Exponential backoff with jitter
    - All attempts logged
    - PermanentFailureError after max retries
    """

    def __init__(
        self, config: Optional[RetryConfig] = None, db_path: str = "event_log.db"
    ):
        self.config = config or RetryConfig()
        self.db_path = db_path
        self._init_retry_table()

    def _init_retry_table(self):
        """Initialize retry attempt logging table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retry_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                delay_used REAL,
                success INTEGER NOT NULL,
                UNIQUE(session_id, agent_name, attempt_number)
            )
        """)
        conn.commit()
        conn.close()

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter.

        Formula: delay = base_delay * (2 ** attempt) + random_jitter
        """
        exponential_delay = self.config.base_delay * (2**attempt)
        jitter = random.uniform(0, self.config.jitter * self.config.base_delay)
        delay = exponential_delay + jitter
        return min(delay, self.config.max_delay)

    def is_retryable(self, error: Exception) -> bool:
        """Check if error is retryable."""
        return isinstance(error, self.config.retryable_errors)

    def execute_with_retry(
        self, func: Callable, session_id: str, agent_name: str, *args, **kwargs
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            session_id: Current session
            agent_name: Agent name
            *args, **kwargs: Arguments for func

        Returns:
            Result from func

        Raises:
            PermanentFailureError: If max retries exceeded
            NonRetryableError: If error is not retryable
        """
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = func(*args, **kwargs)

                if attempt > 0:
                    self._log_attempt(
                        session_id, agent_name, attempt, None, "", 0, True
                    )

                return result

            except NonRetryableError as e:
                self._log_attempt(
                    session_id, agent_name, attempt, type(e).__name__, str(e), 0, False
                )
                raise PermanentFailureError(e, attempt + 1, f"Non-retryable error: {e}")

            except self.config.retryable_errors as e:
                last_error = e

                if attempt < self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    self._log_attempt(
                        session_id,
                        agent_name,
                        attempt,
                        type(e).__name__,
                        str(e),
                        delay,
                        False,
                    )
                    time.sleep(delay)
                else:
                    self._log_attempt(
                        session_id,
                        agent_name,
                        attempt,
                        type(e).__name__,
                        str(e),
                        0,
                        False,
                    )

        raise PermanentFailureError(last_error, self.config.max_retries + 1)

    def _log_attempt(
        self,
        session_id: str,
        agent_name: str,
        attempt_number: int,
        error_type: str,
        error_message: str,
        delay_used: float,
        success: bool,
    ):
        """Log retry attempt to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO retry_attempts 
                (session_id, agent_name, attempt_number, timestamp, error_type, error_message, delay_used, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    agent_name,
                    attempt_number,
                    datetime.utcnow().isoformat(),
                    error_type,
                    error_message,
                    delay_used,
                    1 if success else 0,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def get_retry_history(self, session_id: str, agent_name: str) -> list:
        """Get retry history for an agent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT attempt_number, timestamp, error_type, delay_used, success
            FROM retry_attempts
            WHERE session_id = ? AND agent_name = ?
            ORDER BY attempt_number ASC
        """,
            (session_id, agent_name),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            RetryAttempt(
                attempt_number=r[0],
                timestamp=r[1],
                error_type=r[2],
                error_message="",
                delay_used=r[3],
                success=bool(r[4]),
            )
            for r in rows
        ]


_global_retry_manager: Optional[RetryManager] = None


def get_retry_manager(config: Optional[RetryConfig] = None) -> RetryManager:
    """Get global retry manager instance."""
    global _global_retry_manager
    if _global_retry_manager is None:
        _global_retry_manager = RetryManager(config)
    return _global_retry_manager
