"""
Retry logic with exponential backoff
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Type

from thread_module.jobs.job import Job, JobState


@dataclass
class RetryPolicy:
    """
    Configuration for retry behavior.

    Example:
        >>> policy = RetryPolicy(
        ...     max_attempts=5,
        ...     backoff_factor=2.0,
        ...     retry_on=(TimeoutError, ConnectionError)
        ... )
    """

    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    retry_on: tuple[Type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable[[Exception, int], None]] = None


class RetryableJob(Job):
    """
    Job with built-in retry logic and exponential backoff.

    Automatically retries failed executions with configurable backoff.

    Example:
        >>> def unstable_api_call():
        ...     # May fail transiently
        ...     return fetch_data()
        >>>
        >>> job = RetryableJob(
        ...     func=unstable_api_call,
        ...     retry_policy=RetryPolicy(max_attempts=5)
        ... )
        >>> result = job.execute()
    """

    def __init__(
        self,
        func: Callable,
        retry_policy: Optional[RetryPolicy] = None,
        **kwargs
    ):
        """
        Initialize retryable job.

        Args:
            func: Function to execute
            retry_policy: Retry configuration
            **kwargs: Additional Job parameters
        """
        super().__init__(func, **kwargs)
        self.retry_policy = retry_policy or RetryPolicy()
        self.attempt_count = 0
        self.retry_history: list[tuple[int, Exception, float]] = []

    def execute(self):
        """
        Execute with automatic retry on failure.

        Returns:
            Result of successful execution

        Raises:
            Exception: Last exception if all retries exhausted
        """
        last_exception = None

        while self.attempt_count < self.retry_policy.max_attempts:
            self.attempt_count += 1

            try:
                # Try to execute
                result = super().execute()
                return result

            except self.retry_policy.retry_on as e:
                last_exception = e

                # Calculate backoff delay
                delay = min(
                    self.retry_policy.initial_delay *
                    (self.retry_policy.backoff_factor ** (self.attempt_count - 1)),
                    self.retry_policy.max_delay
                )

                # Record retry
                self.retry_history.append((self.attempt_count, e, delay))

                # Invoke callback if provided
                if self.retry_policy.on_retry:
                    try:
                        self.retry_policy.on_retry(e, self.attempt_count)
                    except Exception:
                        pass  # Ignore callback errors

                # Last attempt?
                if self.attempt_count >= self.retry_policy.max_attempts:
                    break

                # Wait before retry (unless cancelled)
                if not self.is_cancelled():
                    time.sleep(delay)

            except Exception as e:
                # Exception not in retry_on list - fail immediately
                last_exception = e
                self.retry_history.append((self.attempt_count, e, 0.0))
                break

        # All retries failed or non-retryable exception
        if last_exception:
            raise last_exception

    def __repr__(self) -> str:
        """String representation with retry info"""
        return (f"RetryableJob(name={self.name}, attempts={self.attempt_count}/"
                f"{self.retry_policy.max_attempts}, state={self.state.name})")


# Extension methods for ThreadPool
def add_retry_methods():
    """Add retry methods to ThreadPool class"""
    from thread_module.core.thread_pool import ThreadPool

    def submit_with_retry(
        self,
        func: Callable,
        *args,
        retry_policy: Optional[RetryPolicy] = None,
        **kwargs
    ) -> RetryableJob:
        """
        Submit job with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            retry_policy: Retry configuration
            **kwargs: Keyword arguments

        Returns:
            RetryableJob instance

        Example:
            >>> pool = ThreadPool(max_workers=4)
            >>> job = pool.submit_with_retry(
            ...     fetch_data,
            ...     url,
            ...     retry_policy=RetryPolicy(max_attempts=5)
            ... )
        """
        # Extract Job-specific kwargs
        priority = kwargs.pop('priority', None)
        cancellation_token = kwargs.pop('cancellation_token', None)
        name = kwargs.pop('name', None)

        # Create retryable job
        job = RetryableJob(
            func=lambda: func(*args, **kwargs),
            retry_policy=retry_policy,
            priority=priority,
            cancellation_token=cancellation_token,
            name=name
        )

        return self.submit_job(job)

    # Monkey-patch ThreadPool
    ThreadPool.submit_with_retry = submit_with_retry
