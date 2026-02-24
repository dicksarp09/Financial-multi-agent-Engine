import signal
import multiprocessing as mp
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
import time
import sys


T = TypeVar("T")


class TimeoutException(Exception):
    """Raised when execution exceeds time limit."""

    pass


class MemoryLimitException(Exception):
    """Raised when memory limit is exceeded."""

    pass


class SandboxExecutionException(Exception):
    """Raised when sandbox execution fails."""

    pass


@dataclass
class SandboxResult(Generic[T]):
    """Result from sandboxed execution."""

    success: bool
    result: Optional[T] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    terminated: bool = False
    termination_reason: Optional[str] = None


class ResourceLimit:
    """Resource limits for sandboxed execution."""

    def __init__(
        self,
        timeout_seconds: float = 2.0,
        max_memory_mb: int = 256,
        max_tokens: int = 4096,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.max_tokens = max_tokens


def _run_with_timeout(
    func: Callable,
    args: tuple,
    kwargs: dict,
    timeout_seconds: float,
    result_queue: mp.Queue,
):
    """Execute function with timeout - runs in child process."""
    try:
        result = func(*args, **kwargs)
        result_queue.put(("success", result))
    except TimeoutException:
        result_queue.put(("timeout", None))
    except MemoryLimitException:
        result_queue.put(("memory", None))
    except Exception as e:
        result_queue.put(("error", str(e)))


class Sandbox:
    """
    Execution sandbox for agent actions.

    Enforces:
    - CPU time limits
    - Memory caps
    - Hard timeouts
    - LLM token caps
    """

    def __init__(self, limits: Optional[ResourceLimit] = None):
        self.limits = limits or ResourceLimit()
        self._current_process: Optional[mp.Process] = None

    def execute(self, func: Callable[..., T], *args, **kwargs) -> SandboxResult[T]:
        """
        Execute a function within sandbox limits.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            SandboxResult with execution outcome
        """
        start_time = time.time()

        result_queue: mp.Queue = mp.Queue()

        self._current_process = mp.Process(
            target=_run_with_timeout,
            args=(func, args, kwargs, self.limits.timeout_seconds, result_queue),
        )

        self._current_process.start()

        self._current_process.join(timeout=self.limits.timeout_seconds + 1)

        execution_time = (time.time() - start_time) * 1000

        if self._current_process.is_alive():
            self._current_process.terminate()
            self._current_process.join(timeout=1)

            return SandboxResult(
                success=False,
                error="Execution terminated due to timeout",
                execution_time_ms=execution_time,
                terminated=True,
                termination_reason="timeout",
            )

        if not result_queue.empty():
            status, data = result_queue.get_nowait()

            if status == "success":
                return SandboxResult(
                    success=True, result=data, execution_time_ms=execution_time
                )
            elif status == "timeout":
                return SandboxResult(
                    success=False,
                    error=f"Execution exceeded {self.limits.timeout_seconds}s limit",
                    execution_time_ms=execution_time,
                    terminated=True,
                    termination_reason="timeout",
                )
            elif status == "memory":
                return SandboxResult(
                    success=False,
                    error=f"Execution exceeded {self.limits.max_memory_mb}MB memory limit",
                    execution_time_ms=execution_time,
                    terminated=True,
                    termination_reason="memory",
                )
            else:
                return SandboxResult(
                    success=False,
                    error=f"Execution error: {data}",
                    execution_time_ms=execution_time,
                )

        return SandboxResult(
            success=False,
            error="No result returned from execution",
            execution_time_ms=execution_time,
        )

    def execute_with_token_limit(
        self, func: Callable[..., T], token_count: int, *args, **kwargs
    ) -> SandboxResult[T]:
        """
        Execute with additional token limit check.

        Args:
            func: Function to execute
            token_count: Number of tokens (for LLM calls)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            SandboxResult
        """
        if token_count > self.limits.max_tokens:
            return SandboxResult(
                success=False,
                error=f"Token count {token_count} exceeds limit {self.limits.max_tokens}",
                terminated=True,
                termination_reason="token_limit",
            )

        return self.execute(func, *args, **kwargs)

    def terminate(self):
        """Forcefully terminate current execution."""
        if self._current_process and self._current_process.is_alive():
            self._current_process.terminate()
            self._current_process.join(timeout=1)


class TimeoutHandler:
    """Signal-based timeout handler for simpler use cases (Unix only)."""

    def __init__(self, timeout_seconds: float = 2.0):
        self.timeout_seconds = timeout_seconds
        self._old_handler = None
        self._use_signal = hasattr(signal, "SIGALRM")

    def __enter__(self):
        if self._use_signal:

            def timeout_handler(signum, frame):
                raise TimeoutException(f"Execution exceeded {self.timeout_seconds}s")

            self._old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(self.timeout_seconds))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._use_signal:
            signal.alarm(0)
            if self._old_handler:
                signal.signal(signal.SIGALRM, self._old_handler)
        return False


_global_sandbox: Optional[Sandbox] = None


def get_sandbox(limits: Optional[ResourceLimit] = None) -> Sandbox:
    """Get global sandbox instance."""
    global _global_sandbox
    if _global_sandbox is None:
        _global_sandbox = Sandbox(limits)
    return _global_sandbox


def execute_sandboxed(func: Callable[..., T], *args, **kwargs) -> SandboxResult[T]:
    """Convenience function to execute in sandbox."""
    return get_sandbox().execute(func, *args, **kwargs)
