from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
import json


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, no calls allowed
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: float = 0.4  # 40% error rate triggers open
    success_threshold: float = 0.6  # 60% success rate closes
    rolling_window: int = 20  # Last N executions
    cooldown_seconds: int = 60  # Time before half-open
    test_requests: int = 3  # Test requests in half-open


@dataclass
class ExecutionRecord:
    """Record of a single execution."""

    timestamp: str
    success: bool
    error_type: Optional[str] = None


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for agent protection.

    Tracks error rate per agent over rolling window.
    If error rate exceeds threshold, opens circuit.
    After cooldown, allows limited test executions.
    """

    def __init__(
        self, config: CircuitBreakerConfig = None, db_path: str = "event_log.db"
    ):
        self.config = config or CircuitBreakerConfig()
        self.db_path = db_path
        self._state: Dict[str, CircuitState] = {}
        self._executions: Dict[str, List[ExecutionRecord]] = {}
        self._last_failure_time: Dict[str, datetime] = {}
        self._test_attempts: Dict[str, int] = {}
        self._init_table()

    def _init_table(self):
        """Initialize circuit breaker logging table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS circuit_breaker_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                previous_state TEXT,
                new_state TEXT,
                error_rate REAL,
                UNIQUE(agent_name, timestamp, event_type)
            )
        """)
        conn.commit()
        conn.close()

    def get_state(self, agent_name: str) -> CircuitState:
        """Get current state of circuit breaker for agent."""
        if agent_name not in self._state:
            self._state[agent_name] = CircuitState.CLOSED
            self._executions[agent_name] = []

        state = self._state[agent_name]

        if state == CircuitState.OPEN:
            if self._should_attempt_reset(agent_name):
                self._transition_to(agent_name, CircuitState.HALF_OPEN)

        return self._state[agent_name]

    def _should_attempt_reset(self, agent_name: str) -> bool:
        """Check if enough time has passed to attempt reset."""
        if agent_name not in self._last_failure_time:
            return False

        elapsed = datetime.utcnow() - self._last_failure_time[agent_name]
        return elapsed.total_seconds() >= self.config.cooldown_seconds

    def _transition_to(self, agent_name: str, new_state: CircuitState):
        """Transition to new state."""
        old_state = self._state.get(agent_name, CircuitState.CLOSED)

        if old_state != new_state:
            self._state[agent_name] = new_state
            self._log_event(agent_name, "state_change", old_state, new_state, None)

            if new_state == CircuitState.HALF_OPEN:
                self._test_attempts[agent_name] = 0

    def can_execute(self, agent_name: str) -> bool:
        """Check if execution is allowed."""
        state = self.get_state(agent_name)

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.OPEN:
            return False

        if state == CircuitState.HALF_OPEN:
            if self._test_attempts.get(agent_name, 0) < self.config.test_requests:
                self._test_attempts[agent_name] = (
                    self._test_attempts.get(agent_name, 0) + 1
                )
                return True
            return False

        return False

    def record_success(self, agent_name: str):
        """Record successful execution."""
        self._record_execution(agent_name, True)

        state = self.get_state(agent_name)

        if state == CircuitState.HALF_OPEN:
            error_rate = self._calculate_error_rate(agent_name)
            if error_rate < (1 - self.config.success_threshold):
                self._transition_to(agent_name, CircuitState.CLOSED)
        else:
            self._transition_to(agent_name, CircuitState.CLOSED)

    def record_failure(self, agent_name: str, error_type: str = None):
        """Record failed execution."""
        self._record_execution(agent_name, False, error_type)
        self._last_failure_time[agent_name] = datetime.utcnow()

        error_rate = self._calculate_error_rate(agent_name)

        if error_rate > self.config.failure_threshold:
            self._transition_to(agent_name, CircuitState.OPEN)
            self._log_event(
                agent_name, "circuit_opened", None, CircuitState.OPEN, error_rate
            )

    def _record_execution(self, agent_name: str, success: bool, error_type: str = None):
        """Record execution for error rate calculation."""
        if agent_name not in self._executions:
            self._executions[agent_name] = []

        record = ExecutionRecord(
            timestamp=datetime.utcnow().isoformat(),
            success=success,
            error_type=error_type,
        )

        self._executions[agent_name].append(record)

        if len(self._executions[agent_name]) > self.config.rolling_window:
            self._executions[agent_name] = self._executions[agent_name][
                -self.config.rolling_window :
            ]

    def _calculate_error_rate(self, agent_name: str) -> float:
        """Calculate error rate over rolling window."""
        if agent_name not in self._executions or not self._executions[agent_name]:
            return 0.0

        executions = self._executions[agent_name]
        failures = sum(1 for e in executions if not e.success)
        return failures / len(executions)

    def _log_event(
        self,
        agent_name: str,
        event_type: str,
        old_state: CircuitState,
        new_state: CircuitState,
        error_rate: float,
    ):
        """Log circuit breaker event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO circuit_breaker_events 
                (agent_name, timestamp, event_type, previous_state, new_state, error_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    agent_name,
                    datetime.utcnow().isoformat(),
                    event_type,
                    old_state.value if old_state else None,
                    new_state.value if new_state else None,
                    error_rate,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def get_stats(self, agent_name: str) -> Dict:
        """Get circuit breaker stats for agent."""
        return {
            "state": self.get_state(agent_name).value,
            "error_rate": round(self._calculate_error_rate(agent_name), 3),
            "total_executions": len(self._executions.get(agent_name, [])),
            "last_failure": self._last_failure_time.get(agent_name, None),
        }

    def reset(self, agent_name: str):
        """Manually reset circuit breaker."""
        self._state[agent_name] = CircuitState.CLOSED
        self._executions[agent_name] = []
        self._last_failure_time.pop(agent_name, None)
        self._test_attempts.pop(agent_name, None)


_global_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker(config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """Get global circuit breaker instance."""
    global _global_circuit_breaker
    if _global_circuit_breaker is None:
        _global_circuit_breaker = CircuitBreaker(config)
    return _global_circuit_breaker
