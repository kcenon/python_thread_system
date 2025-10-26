"""Bounded thread pool with queue size limits"""

import time
from typing import Callable, Optional
from thread_module.core.thread_pool import ThreadPool
from thread_module.jobs.job import Job, JobPriority
from thread_module.sync.cancellation_token import CancellationToken


class QueueFullError(Exception):
    """Raised when queue is full and on_queue_full='reject'"""
    pass


class BoundedThreadPool(ThreadPool):
    """
    Thread pool with bounded queue.

    Prevents unlimited queue growth by:
    - Blocking when queue is full (on_queue_full='block')
    - Rejecting new submissions (on_queue_full='reject')
    """

    def __init__(
        self,
        max_workers: int,
        max_queue_size: int,
        on_queue_full: str = "block",
        **kwargs
    ):
        """
        Initialize bounded thread pool.

        Args:
            max_workers: Maximum worker threads
            max_queue_size: Maximum queued jobs
            on_queue_full: 'block' or 'reject'
        """
        super().__init__(max_workers, **kwargs)
        self.max_queue_size = max_queue_size
        self.on_queue_full = on_queue_full

    def submit(
        self,
        func: Callable,
        *args,
        block: bool = True,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Job:
        """
        Submit with queue size check.

        Args:
            func: Function to execute
            *args: Positional arguments
            block: Whether to block if queue full
            timeout: Max time to wait if blocking
            **kwargs: Keyword arguments

        Returns:
            Job instance

        Raises:
            QueueFullError: If queue full and on_queue_full='reject'
        """
        # Check queue size
        while len(self._job_queue) >= self.max_queue_size:
            if self.on_queue_full == "reject" or not block:
                raise QueueFullError(
                    f"Queue full ({len(self._job_queue)}/{self.max_queue_size})"
                )

            # Block mode
            start = time.time()
            if timeout and (time.time() - start) > timeout:
                raise QueueFullError("Timeout waiting for queue space")
            time.sleep(0.01)

        return super().submit(func, *args, **kwargs)
