"""
Thread pool implementation based on concurrent.futures with priority support
"""

from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import Any, Callable, Optional
import threading
import heapq
import time

from thread_module.jobs.job import Job, JobPriority, JobState
from thread_module.sync.cancellation_token import CancellationToken


@dataclass
class ThreadPoolMetrics:
    """Thread pool performance metrics"""
    total_jobs_submitted: int = 0
    total_jobs_completed: int = 0
    total_jobs_failed: int = 0
    total_jobs_cancelled: int = 0
    active_jobs: int = 0
    pending_jobs: int = 0


class ThreadPool:
    """
    A thread pool that wraps concurrent.futures.ThreadPoolExecutor with:
    - Priority-based job execution
    - Job abstraction with cancellation support
    - Performance metrics
    - Graceful shutdown

    Example:
        >>> pool = ThreadPool(max_workers=4)
        >>> def work(x):
        ...     return x * 2
        >>> job = pool.submit(work, 5, priority=JobPriority.HIGH)
        >>> result = job.result()
        >>> print(result)  # 10
        >>> pool.shutdown()
    """

    def __init__(self,
                 max_workers: Optional[int] = None,
                 thread_name_prefix: str = "ThreadPool"):
        """
        Initialize thread pool.

        Args:
            max_workers: Maximum number of worker threads (None = CPU count + 4)
            thread_name_prefix: Prefix for worker thread names
        """
        self._max_workers = max_workers
        self._thread_name_prefix = thread_name_prefix
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix
        )

        # Priority queue for jobs (min-heap, lower priority value = higher priority)
        self._job_queue: list[Job] = []
        self._queue_lock = threading.Lock()
        self._queue_cv = threading.Condition(self._queue_lock)

        # Metrics
        self._metrics = ThreadPoolMetrics()
        self._metrics_lock = threading.Lock()

        # Dispatcher thread
        self._running = True
        self._dispatcher_thread = threading.Thread(
            target=self._dispatch_jobs,
            name=f"{thread_name_prefix}-Dispatcher",
            daemon=True
        )
        self._dispatcher_thread.start()

    def submit(self,
               func: Callable,
               *args,
               priority: JobPriority = JobPriority.NORMAL,
               cancellation_token: Optional[CancellationToken] = None,
               name: Optional[str] = None,
               **kwargs) -> Job:
        """
        Submit a job to the thread pool.

        Args:
            func: Callable to execute
            *args: Positional arguments for func
            priority: Job priority
            cancellation_token: Optional cancellation token
            name: Optional job name
            **kwargs: Keyword arguments for func

        Returns:
            Job object that can be used to track execution

        Example:
            >>> job = pool.submit(lambda x: x*2, 5, priority=JobPriority.HIGH)
            >>> result = job.result
        """
        job = Job(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            cancellation_token=cancellation_token,
            name=name
        )

        with self._queue_cv:
            heapq.heappush(self._job_queue, job)
            self._queue_cv.notify()

        with self._metrics_lock:
            self._metrics.total_jobs_submitted += 1
            self._metrics.pending_jobs += 1

        return job

    def submit_job(self, job: Job) -> Job:
        """
        Submit a pre-created Job object.

        Args:
            job: Job to execute

        Returns:
            The same job object (for chaining)
        """
        with self._queue_cv:
            heapq.heappush(self._job_queue, job)
            self._queue_cv.notify()

        with self._metrics_lock:
            self._metrics.total_jobs_submitted += 1
            self._metrics.pending_jobs += 1

        return job

    def _dispatch_jobs(self) -> None:
        """
        Dispatcher thread that pulls jobs from priority queue and submits to executor.
        """
        while self._running:
            job: Optional[Job] = None

            with self._queue_cv:
                # Wait for jobs or shutdown
                while self._running and not self._job_queue:
                    self._queue_cv.wait(timeout=0.1)

                if not self._running:
                    break

                if self._job_queue:
                    job = heapq.heappop(self._job_queue)

            if job is None:
                continue

            # Check if job was cancelled before execution
            if job.is_cancelled():
                with self._metrics_lock:
                    self._metrics.total_jobs_cancelled += 1
                    self._metrics.pending_jobs -= 1
                continue

            # Update metrics
            with self._metrics_lock:
                self._metrics.pending_jobs -= 1
                self._metrics.active_jobs += 1

            # Submit to executor
            def execute_and_track(j: Job):
                try:
                    j.execute()
                    with self._metrics_lock:
                        self._metrics.total_jobs_completed += 1
                except Exception:
                    if j.state == JobState.CANCELLED:
                        with self._metrics_lock:
                            self._metrics.total_jobs_cancelled += 1
                    else:
                        with self._metrics_lock:
                            self._metrics.total_jobs_failed += 1
                finally:
                    with self._metrics_lock:
                        self._metrics.active_jobs -= 1

            self._executor.submit(execute_and_track, job)

    def get_metrics(self) -> ThreadPoolMetrics:
        """
        Get current thread pool metrics.

        Returns:
            Copy of current metrics
        """
        with self._metrics_lock:
            return ThreadPoolMetrics(
                total_jobs_submitted=self._metrics.total_jobs_submitted,
                total_jobs_completed=self._metrics.total_jobs_completed,
                total_jobs_failed=self._metrics.total_jobs_failed,
                total_jobs_cancelled=self._metrics.total_jobs_cancelled,
                active_jobs=self._metrics.active_jobs,
                pending_jobs=self._metrics.pending_jobs
            )

    def wait_all(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all submitted jobs to complete.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if all jobs completed, False if timeout occurred
        """
        start_time = time.time()

        while True:
            metrics = self.get_metrics()
            if metrics.active_jobs == 0 and metrics.pending_jobs == 0:
                return True

            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            time.sleep(0.01)

    def shutdown(self, wait: bool = True, cancel_pending: bool = False) -> None:
        """
        Shutdown the thread pool.

        Args:
            wait: If True, wait for all active jobs to complete
            cancel_pending: If True, cancel all pending jobs in queue
        """
        # Stop dispatcher
        with self._queue_cv:
            self._running = False
            self._queue_cv.notify_all()

        if self._dispatcher_thread.is_alive():
            self._dispatcher_thread.join(timeout=1.0)

        # Cancel pending jobs if requested
        if cancel_pending:
            with self._queue_lock:
                for job in self._job_queue:
                    job.cancel()
                self._job_queue.clear()

        # Shutdown executor
        self._executor.shutdown(wait=wait)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown(wait=True)
        return False

    def __repr__(self) -> str:
        """String representation"""
        metrics = self.get_metrics()
        return (f"ThreadPool(max_workers={self._max_workers}, "
                f"active={metrics.active_jobs}, "
                f"pending={metrics.pending_jobs}, "
                f"completed={metrics.total_jobs_completed})")
