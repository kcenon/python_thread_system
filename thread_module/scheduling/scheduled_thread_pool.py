"""
Scheduled thread pool with periodic and delayed execution
"""

import sched
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional

from thread_module.core.thread_pool import ThreadPool
from thread_module.jobs.job import JobPriority


class ScheduledThreadPool(ThreadPool):
    """
    Thread pool with scheduling capabilities.

    Supports:
    - Periodic execution (every N seconds)
    - Delayed execution (after N seconds)
    - Scheduled execution (at specific datetime)

    Example:
        >>> pool = ScheduledThreadPool(max_workers=4)
        >>> job_id = pool.schedule_periodic(cleanup, interval=60.0)
        >>> pool.schedule_at(backup, when=datetime(2025, 1, 1, 2, 0))
        >>> pool.schedule_delayed(notify, delay=10.0)
    """

    def __init__(self, *args, **kwargs):
        """Initialize ScheduledThreadPool"""
        super().__init__(*args, **kwargs)

        # Scheduler for timing
        self._scheduler = sched.scheduler(time.time, time.sleep)

        # Track scheduled jobs
        self._scheduled_jobs = {}
        self._scheduled_jobs_lock = threading.Lock()

        # Scheduler thread
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(
            target=self._run_scheduler,
            name=f"{self._thread_name_prefix}-Scheduler",
            daemon=True
        )
        self._scheduler_thread.start()

    def schedule_periodic(
        self,
        func: Callable,
        interval: float,
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Execute function periodically at fixed interval.

        Args:
            func: Function to execute
            interval: Interval in seconds between executions
            *args: Positional arguments for func
            priority: Job priority
            name: Optional job name
            **kwargs: Keyword arguments for func

        Returns:
            Job ID that can be used to cancel the schedule

        Example:
            >>> pool = ScheduledThreadPool(max_workers=4)
            >>> job_id = pool.schedule_periodic(cleanup_temp_files, interval=60.0)
            >>> # Later: pool.cancel_scheduled(job_id)
        """
        if interval <= 0:
            raise ValueError("Interval must be positive")

        job_id = f"periodic_{id(func)}_{time.time()}"
        job_name = name or f"periodic_{func.__name__}"

        def recurring():
            """Recurring wrapper"""
            with self._scheduled_jobs_lock:
                if job_id not in self._scheduled_jobs:
                    return  # Job was cancelled

            # Submit to thread pool
            self.submit(
                func,
                *args,
                priority=priority,
                name=f"{job_name}_{time.time()}",
                **kwargs
            )

            # Schedule next execution
            with self._scheduled_jobs_lock:
                if job_id in self._scheduled_jobs:
                    self._scheduler.enter(interval, 1, recurring)

        # Schedule first execution
        self._scheduler.enter(interval, 1, recurring)

        with self._scheduled_jobs_lock:
            self._scheduled_jobs[job_id] = {
                "type": "periodic",
                "interval": interval,
                "func": func,
                "name": job_name
            }

        return job_id

    def schedule_at(
        self,
        func: Callable,
        when: datetime,
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Execute function at specific datetime.

        Args:
            func: Function to execute
            when: Datetime when to execute
            *args: Positional arguments for func
            priority: Job priority
            name: Optional job name
            **kwargs: Keyword arguments for func

        Returns:
            Job ID that can be used to cancel the schedule

        Raises:
            ValueError: If when is in the past

        Example:
            >>> pool = ScheduledThreadPool(max_workers=4)
            >>> backup_time = datetime(2025, 1, 1, 2, 0, 0)
            >>> pool.schedule_at(backup_database, when=backup_time)
        """
        delay = (when - datetime.now()).total_seconds()
        if delay < 0:
            raise ValueError("Cannot schedule in the past")

        job_id = f"once_{id(func)}_{when.timestamp()}"
        job_name = name or f"scheduled_{func.__name__}"

        def execute():
            """One-time execution wrapper"""
            self.submit(
                func,
                *args,
                priority=priority,
                name=job_name,
                **kwargs
            )

            with self._scheduled_jobs_lock:
                self._scheduled_jobs.pop(job_id, None)

        # Schedule execution
        self._scheduler.enter(delay, 1, execute)

        with self._scheduled_jobs_lock:
            self._scheduled_jobs[job_id] = {
                "type": "once",
                "when": when,
                "func": func,
                "name": job_name
            }

        return job_id

    def schedule_delayed(
        self,
        func: Callable,
        delay: float,
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Execute function after delay seconds.

        Args:
            func: Function to execute
            delay: Delay in seconds
            *args: Positional arguments for func
            priority: Job priority
            name: Optional job name
            **kwargs: Keyword arguments for func

        Returns:
            Job ID that can be used to cancel the schedule

        Example:
            >>> pool = ScheduledThreadPool(max_workers=4)
            >>> pool.schedule_delayed(send_notification, delay=10.0, user_id=123)
        """
        when = datetime.now() + timedelta(seconds=delay)
        return self.schedule_at(func, when, *args, priority=priority, name=name, **kwargs)

    def cancel_scheduled(self, job_id: str) -> bool:
        """
        Cancel a scheduled job.

        Args:
            job_id: Job ID returned by schedule_* methods

        Returns:
            True if job was cancelled, False if not found

        Example:
            >>> job_id = pool.schedule_periodic(cleanup, interval=60.0)
            >>> pool.cancel_scheduled(job_id)
            True
        """
        with self._scheduled_jobs_lock:
            if job_id in self._scheduled_jobs:
                self._scheduled_jobs.pop(job_id)
                return True
            return False

    def get_scheduled_jobs(self) -> dict:
        """
        Get information about all scheduled jobs.

        Returns:
            Dictionary mapping job IDs to job information

        Example:
            >>> jobs = pool.get_scheduled_jobs()
            >>> for job_id, info in jobs.items():
            ...     print(f"{job_id}: {info['type']} - {info['name']}")
        """
        with self._scheduled_jobs_lock:
            return self._scheduled_jobs.copy()

    def _run_scheduler(self):
        """Background scheduler thread"""
        while self._scheduler_running:
            # Run scheduler with short blocking
            self._scheduler.run(blocking=False)
            time.sleep(0.1)

    def shutdown(self, wait: bool = True, cancel_pending: bool = False):
        """Shutdown thread pool and scheduler"""
        # Stop scheduler
        self._scheduler_running = False

        if self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=1.0)

        # Cancel all scheduled jobs
        with self._scheduled_jobs_lock:
            self._scheduled_jobs.clear()

        # Shutdown thread pool
        super().shutdown(wait=wait, cancel_pending=cancel_pending)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown(wait=True)
        return False
