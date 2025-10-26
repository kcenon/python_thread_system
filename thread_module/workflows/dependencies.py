"""Job dependency and workflow management"""

import time
from typing import Optional, Callable, List
from thread_module.jobs.job import Job, JobState
from thread_module.core.thread_pool import ThreadPool


class DependentJob(Job):
    """Job with dependency support"""

    def __init__(self, func: Callable, depends_on: Optional[List[Job]] = None, **kwargs):
        super().__init__(func, **kwargs)
        self.depends_on = depends_on or []

    def can_execute(self) -> bool:
        """Check if all dependencies completed successfully"""
        return all(dep.state == JobState.COMPLETED for dep in self.depends_on)

    def wait_for_dependencies(self, timeout: Optional[float] = None):
        """Block until dependencies complete"""
        start = time.time()
        while not self.can_execute():
            if timeout and (time.time() - start) > timeout:
                raise TimeoutError("Dependencies not met")
            # Check if any dependency failed
            if any(dep.state == JobState.FAILED for dep in self.depends_on):
                raise RuntimeError("Dependency failed")
            time.sleep(0.01)


class JobGroup:
    """Group of related jobs"""

    def __init__(self, name: str, pool: ThreadPool):
        self.name = name
        self.pool = pool
        self.jobs: List[Job] = []

    def submit(self, func: Callable, *args, **kwargs) -> Job:
        """Submit job to this group"""
        job = self.pool.submit(func, *args, name=f"{self.name}/{kwargs.get('name', func.__name__)}", **kwargs)
        self.jobs.append(job)
        return job

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for all jobs in group"""
        start = time.time()
        while any(j.state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) for j in self.jobs):
            if timeout and (time.time() - start) > timeout:
                return False
            time.sleep(0.01)
        return True

    def cancel_all(self):
        """Cancel all pending jobs in group"""
        for job in self.jobs:
            job.cancel()

    @property
    def statistics(self) -> dict:
        """Get group statistics"""
        return {
            "total": len(self.jobs),
            "completed": sum(1 for j in self.jobs if j.state == JobState.COMPLETED),
            "failed": sum(1 for j in self.jobs if j.state == JobState.FAILED),
            "cancelled": sum(1 for j in self.jobs if j.state == JobState.CANCELLED),
            "pending": sum(1 for j in self.jobs if j.state == JobState.PENDING),
            "running": sum(1 for j in self.jobs if j.state == JobState.RUNNING),
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wait()
        return False


# Add methods to ThreadPool
def add_workflow_methods():
    """Add workflow methods to ThreadPool"""
    from thread_module.core.thread_pool import ThreadPool

    def submit_with_deps(self, func: Callable, *args, depends_on: Optional[List[Job]] = None, **kwargs) -> DependentJob:
        """Submit job with dependencies"""
        from thread_module.jobs.job import JobPriority
        priority = kwargs.pop('priority', JobPriority.NORMAL)
        cancellation_token = kwargs.pop('cancellation_token', None)
        name = kwargs.pop('name', None)

        job = DependentJob(
            func=lambda: func(*args, **kwargs),
            depends_on=depends_on,
            priority=priority,
            cancellation_token=cancellation_token,
            name=name
        )

        # Wrap to wait for dependencies
        original_func = job.func

        def execute_with_deps():
            job.wait_for_dependencies(timeout=None)
            return original_func()

        job.func = execute_with_deps
        return self.submit_job(job)

    def create_group(self, name: str) -> JobGroup:
        """Create a job group"""
        return JobGroup(name, self)

    ThreadPool.submit_with_deps = submit_with_deps
    ThreadPool.create_group = create_group
