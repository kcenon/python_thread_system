"""
AsyncIO integration for ThreadPool
"""

import asyncio
from typing import Any, Callable, Iterable, Optional, AsyncGenerator
from concurrent.futures import Future

from thread_module.core.thread_pool import ThreadPool
from thread_module.jobs.job import Job, JobPriority, JobState
from thread_module.sync.cancellation_token import CancellationToken


class AsyncThreadPool(ThreadPool):
    """
    Thread pool with async/await support.

    Bridges synchronous thread pool with asyncio event loop,
    allowing async code to submit CPU-bound work to threads.

    Example:
        >>> async def main():
        ...     pool = AsyncThreadPool(max_workers=4)
        ...     result = await pool.submit_async(cpu_bound_work, data)
        ...     results = await pool.map_async(process, items)
    """

    def __init__(self, *args, **kwargs):
        """Initialize AsyncThreadPool"""
        super().__init__(*args, **kwargs)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop"""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create new one
                self._loop = asyncio.new_event_loop()
        return self._loop

    async def submit_async(
        self,
        func: Callable,
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        cancellation_token: Optional[CancellationToken] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Submit synchronous function and return awaitable result.

        Args:
            func: Synchronous function to execute
            *args: Positional arguments for func
            priority: Job priority
            cancellation_token: Optional cancellation token
            name: Optional job name
            **kwargs: Keyword arguments for func

        Returns:
            Result of the function execution

        Raises:
            Exception: If the function raises an exception

        Example:
            >>> async def main():
            ...     pool = AsyncThreadPool(max_workers=4)
            ...     result = await pool.submit_async(cpu_work, 10, 20)
            ...     print(result)  # 30
        """
        loop = self._get_loop()
        future = loop.create_future()

        def wrapper():
            """Wrapper to bridge thread execution to async future"""
            try:
                result = func(*args, **kwargs)
                loop.call_soon_threadsafe(future.set_result, result)
            except Exception as e:
                loop.call_soon_threadsafe(future.set_exception, e)

        # Submit to thread pool
        self.submit(
            wrapper,
            priority=priority,
            cancellation_token=cancellation_token,
            name=name or f"async_{func.__name__}"
        )

        return await future

    async def map_async(
        self,
        func: Callable,
        iterable: Iterable,
        priority: JobPriority = JobPriority.NORMAL
    ) -> list:
        """
        Map function over iterable asynchronously.

        Args:
            func: Function to apply to each item
            iterable: Iterable of items to process
            priority: Job priority for all tasks

        Returns:
            List of results in same order as input

        Example:
            >>> async def main():
            ...     pool = AsyncThreadPool(max_workers=4)
            ...     results = await pool.map_async(lambda x: x*2, range(10))
            ...     print(results)  # [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
        """
        tasks = [
            self.submit_async(func, item, priority=priority)
            for item in iterable
        ]
        return await asyncio.gather(*tasks)

    async def as_completed_async(
        self,
        jobs: list[Job],
        timeout: Optional[float] = None
    ) -> AsyncGenerator[Job, None]:
        """
        Async generator yielding jobs as they complete.

        Args:
            jobs: List of jobs to monitor
            timeout: Optional timeout in seconds

        Yields:
            Completed jobs in completion order

        Example:
            >>> async def main():
            ...     pool = AsyncThreadPool(max_workers=4)
            ...     jobs = [pool.submit(work, i) for i in range(10)]
            ...     async for job in pool.as_completed_async(jobs):
            ...         print(f"Job {job.name} completed: {job.result}")
        """
        pending = list(jobs)
        start_time = asyncio.get_event_loop().time()

        while pending:
            # Check timeout
            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    raise asyncio.TimeoutError("Timeout waiting for jobs")

            # Find completed jobs
            completed = [
                job for job in pending
                if job.state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED)
            ]

            # Yield completed jobs
            for job in completed:
                pending.remove(job)
                yield job

            # Short sleep to avoid busy waiting
            if pending:
                await asyncio.sleep(0.01)

    async def wait_all_async(self, timeout: Optional[float] = None) -> bool:
        """
        Async version of wait_all().

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if all jobs completed, False if timeout

        Example:
            >>> async def main():
            ...     pool = AsyncThreadPool(max_workers=4)
            ...     for i in range(10):
            ...         pool.submit(work, i)
            ...     await pool.wait_all_async()
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            metrics = self.get_metrics()
            if metrics.active_jobs == 0 and metrics.pending_jobs == 0:
                return True

            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    return False

            await asyncio.sleep(0.01)

    async def shutdown_async(self, wait: bool = True, cancel_pending: bool = False):
        """
        Async version of shutdown().

        Args:
            wait: If True, wait for all active jobs to complete
            cancel_pending: If True, cancel all pending jobs
        """
        if wait:
            await self.wait_all_async()

        self.shutdown(wait=False, cancel_pending=cancel_pending)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown_async(wait=True)
        return False
