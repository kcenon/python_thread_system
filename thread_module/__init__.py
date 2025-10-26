"""
Thread System Module

A Python thread management system based on concurrent.futures with job abstractions,
priority support, and cancellation capabilities.
"""

from thread_module.core.thread_pool import ThreadPool
from thread_module.core.async_thread_pool import AsyncThreadPool
from thread_module.scheduling.scheduled_thread_pool import ScheduledThreadPool
from thread_module.jobs.job import Job, JobPriority, JobState
from thread_module.sync.cancellation_token import CancellationToken

__version__ = "0.2.0"

__all__ = [
    "ThreadPool",
    "AsyncThreadPool",
    "ScheduledThreadPool",
    "Job",
    "JobPriority",
    "JobState",
    "CancellationToken",
]
