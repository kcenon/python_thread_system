"""
Job abstraction with priority and cancellation support
"""

from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Any, Callable, Optional
import threading
import time

from thread_module.sync.cancellation_token import CancellationToken


class JobPriority(IntEnum):
    """
    Job priority levels.

    Higher numeric values indicate higher priority.
    """
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4


class JobState(IntEnum):
    """Job execution state"""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class Job:
    """
    A job represents a unit of work to be executed by the thread pool.

    Jobs support:
    - Priority-based execution
    - Cancellation via CancellationToken
    - State tracking
    - Execution time measurement

    Example:
        >>> def work(x, y):
        ...     return x + y
        >>> job = Job(func=work, args=(1, 2), priority=JobPriority.HIGH)
        >>> result = job.execute()
        >>> print(result)  # 3
    """

    # Required fields first
    func: Callable

    # Optional fields with defaults
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    cancellation_token: Optional[CancellationToken] = None
    name: Optional[str] = None

    # Internal state (not used for comparison)
    _state: JobState = field(default=JobState.PENDING, init=False, compare=False)
    _result: Any = field(default=None, init=False, compare=False)
    _exception: Optional[Exception] = field(default=None, init=False, compare=False)
    _start_time: Optional[float] = field(default=None, init=False, compare=False)
    _end_time: Optional[float] = field(default=None, init=False, compare=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, compare=False)

    def __post_init__(self):
        """Initialize job name if not provided"""
        if self.name is None:
            self.name = f"{self.func.__name__}_{id(self)}"

    @property
    def state(self) -> JobState:
        """Get current job state (thread-safe)"""
        with self._lock:
            return self._state

    @state.setter
    def state(self, value: JobState) -> None:
        """Set job state (thread-safe)"""
        with self._lock:
            self._state = value

    @property
    def result(self) -> Any:
        """Get job result (only valid if state is COMPLETED)"""
        with self._lock:
            return self._result

    @property
    def exception(self) -> Optional[Exception]:
        """Get exception if job failed"""
        with self._lock:
            return self._exception

    @property
    def execution_time(self) -> Optional[float]:
        """Get execution time in seconds (None if not yet executed)"""
        with self._lock:
            if self._start_time is None:
                return None
            end = self._end_time if self._end_time else time.time()
            return end - self._start_time

    def is_cancelled(self) -> bool:
        """Check if job has been cancelled"""
        return (self.state == JobState.CANCELLED or
                (self.cancellation_token and self.cancellation_token.is_cancelled()))

    def execute(self) -> Any:
        """
        Execute the job.

        Returns:
            The result of the job function

        Raises:
            Exception: If the job function raises an exception
        """
        # Check cancellation before starting
        if self.is_cancelled():
            self.state = JobState.CANCELLED
            raise RuntimeError(f"Job {self.name} was cancelled before execution")

        self.state = JobState.RUNNING
        self._start_time = time.time()

        try:
            # Execute the function
            result = self.func(*self.args, **self.kwargs)

            # Check cancellation after execution
            if self.is_cancelled():
                self.state = JobState.CANCELLED
                raise RuntimeError(f"Job {self.name} was cancelled during execution")

            with self._lock:
                self._result = result
                self._end_time = time.time()

            self.state = JobState.COMPLETED
            return result

        except Exception as e:
            with self._lock:
                self._exception = e
                self._end_time = time.time()

            if self.is_cancelled():
                self.state = JobState.CANCELLED
            else:
                self.state = JobState.FAILED
            raise

    def cancel(self) -> bool:
        """
        Request cancellation of this job.

        Returns:
            True if cancellation request was accepted, False if job already completed/failed
        """
        with self._lock:
            if self._state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
                return False

            if self.cancellation_token:
                self.cancellation_token.cancel()

            self._state = JobState.CANCELLED
            return True

    def __repr__(self) -> str:
        """String representation of the job"""
        return (f"Job(name={self.name}, priority={self.priority.name}, "
                f"state={self.state.name}, execution_time={self.execution_time})")

    def __lt__(self, other: 'Job') -> bool:
        """
        Compare jobs for priority queue (higher priority comes first).

        Note: This inverts the natural ordering so that higher priority values
        are treated as "less than" for use with heapq (min-heap).
        """
        if not isinstance(other, Job):
            return NotImplemented
        # Invert comparison: higher priority number = higher priority = "smaller" in heap
        return self.priority > other.priority
