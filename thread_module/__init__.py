"""
Thread System Module

A Python thread management system based on concurrent.futures with job abstractions,
priority support, and cancellation capabilities.
"""

from thread_module.core.thread_pool import ThreadPool
from thread_module.core.async_thread_pool import AsyncThreadPool
from thread_module.core.bounded_thread_pool import BoundedThreadPool, QueueFullError
from thread_module.scheduling.scheduled_thread_pool import ScheduledThreadPool
from thread_module.jobs.job import Job, JobPriority, JobState
from thread_module.sync.cancellation_token import CancellationToken
from thread_module.reliability.retry_policy import RetryPolicy, RetryableJob, add_retry_methods
from thread_module.workflows.dependencies import DependentJob, JobGroup, add_workflow_methods

# Add methods to ThreadPool
add_retry_methods()
add_workflow_methods()

__version__ = "0.3.0"

__all__ = [
    "ThreadPool",
    "AsyncThreadPool",
    "BoundedThreadPool",
    "ScheduledThreadPool",
    "Job",
    "JobPriority",
    "JobState",
    "CancellationToken",
    "RetryPolicy",
    "RetryableJob",
    "DependentJob",
    "JobGroup",
    "QueueFullError",
]
