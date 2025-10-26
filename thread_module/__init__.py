"""
Thread System Module

A Python thread management system based on concurrent.futures with job abstractions,
priority support, and cancellation capabilities.
"""

from thread_module.core.thread_pool import ThreadPool
from thread_module.jobs.job import Job, JobPriority, JobState
from thread_module.sync.cancellation_token import CancellationToken

__version__ = "0.1.0"

__all__ = [
    "ThreadPool",
    "Job",
    "JobPriority",
    "JobState",
    "CancellationToken",
]
