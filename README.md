# Python Thread System

A Python thread management system based on `concurrent.futures` with job abstractions, priority support, and cancellation capabilities.

## Features

- **Priority-based Execution**: Jobs are executed based on priority levels (LOWEST, LOW, NORMAL, HIGH, HIGHEST)
- **Job Abstraction**: Clean abstraction for units of work with state tracking
- **Cancellation Support**: Cooperative cancellation using CancellationToken
- **Performance Metrics**: Track submitted, completed, failed, and cancelled jobs
- **Thread-safe**: All operations are thread-safe with proper synchronization
- **Context Manager**: Supports context manager protocol for automatic resource cleanup

## Installation

```bash
# Clone the repository
git clone https://github.com/kcenon/python_thread_system.git
cd python_thread_system

# Install in development mode
pip install -e .
```

## Quick Start

### Basic Usage

```python
from thread_module import ThreadPool, JobPriority

# Create a thread pool
pool = ThreadPool(max_workers=4)

# Submit a job
def work(x, y):
    return x + y

job = pool.submit(work, 5, 10, priority=JobPriority.HIGH)

# Wait for completion
pool.wait_all()

# Get result
print(job.result)  # 15

# Get metrics
metrics = pool.get_metrics()
print(f"Completed: {metrics.total_jobs_completed}")

# Cleanup
pool.shutdown()
```

### Using Context Manager

```python
from thread_module import ThreadPool

with ThreadPool(max_workers=4) as pool:
    results = []

    for i in range(10):
        job = pool.submit(lambda x: x * 2, i)
        results.append(job)

    pool.wait_all()

    for job in results:
        print(job.result)
```

### Job Cancellation

```python
from thread_module import ThreadPool, CancellationToken
import time

pool = ThreadPool(max_workers=2)
token = CancellationToken()

def long_running_work():
    for i in range(100):
        if token.is_cancelled():
            raise RuntimeError("Cancelled")
        time.sleep(0.1)
    return "completed"

job = pool.submit(long_running_work, cancellation_token=token)

# Cancel after 0.5 seconds
time.sleep(0.5)
token.cancel()

pool.wait_all()
print(job.state)  # JobState.CANCELLED

pool.shutdown()
```

### Priority Execution

```python
from thread_module import ThreadPool, JobPriority

pool = ThreadPool(max_workers=1)  # Single worker to see priority order

# Submit jobs with different priorities
pool.submit(print, "Low priority", priority=JobPriority.LOW)
pool.submit(print, "High priority", priority=JobPriority.HIGH)
pool.submit(print, "Highest priority", priority=JobPriority.HIGHEST)

pool.wait_all()
# Output:
# Highest priority
# High priority
# Low priority

pool.shutdown()
```

## Architecture

### Core Components

1. **ThreadPool** (`thread_module/core/thread_pool.py`)
   - Wraps `concurrent.futures.ThreadPoolExecutor`
   - Manages priority queue using `heapq`
   - Dispatches jobs to worker threads
   - Tracks performance metrics

2. **Job** (`thread_module/jobs/job.py`)
   - Represents a unit of work
   - Supports priority levels
   - Tracks execution state (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
   - Measures execution time

3. **CancellationToken** (`thread_module/sync/cancellation_token.py`)
   - Cooperative cancellation mechanism
   - Thread-safe using `threading.Event`
   - Supports callbacks on cancellation

### Job States

```
PENDING → RUNNING → COMPLETED
                 ↘ FAILED
                 ↘ CANCELLED
```

## API Reference

### ThreadPool

```python
ThreadPool(max_workers=None, thread_name_prefix="ThreadPool")
```

**Methods:**
- `submit(func, *args, priority=JobPriority.NORMAL, cancellation_token=None, name=None, **kwargs)` - Submit a job
- `submit_job(job)` - Submit a pre-created Job object
- `get_metrics()` - Get current metrics
- `wait_all(timeout=None)` - Wait for all jobs to complete
- `shutdown(wait=True, cancel_pending=False)` - Shutdown the pool

### Job

```python
Job(func, args=(), kwargs={}, priority=JobPriority.NORMAL,
    cancellation_token=None, name=None)
```

**Properties:**
- `state` - Current job state (JobState enum)
- `result` - Job result (only valid if COMPLETED)
- `exception` - Exception if job failed
- `execution_time` - Execution time in seconds

**Methods:**
- `execute()` - Execute the job (called by ThreadPool)
- `cancel()` - Request cancellation
- `is_cancelled()` - Check if cancelled

### CancellationToken

```python
CancellationToken()
```

**Methods:**
- `cancel()` - Request cancellation
- `is_cancelled()` - Check if cancelled
- `wait(timeout=None)` - Wait for cancellation
- `register_callback(callback)` - Register callback on cancellation

## Performance Considerations

### Python GIL Limitations

Python's Global Interpreter Lock (GIL) limits true parallelism for CPU-bound tasks. This thread system is most effective for:

- **I/O-bound tasks**: Network requests, file operations, database queries
- **Tasks with native code**: NumPy, Pandas operations that release the GIL
- **Concurrent coordination**: Managing multiple asynchronous operations

For CPU-bound tasks, consider using `multiprocessing` instead.

### Recommended Settings

```python
# For I/O-bound tasks
pool = ThreadPool(max_workers=100)  # Can handle many concurrent I/O operations

# For CPU-bound tasks
pool = ThreadPool(max_workers=4)   # Limited by CPU cores
```

## Testing

Run the test suite:

```bash
cd /Users/dongcheolshin/Sources/python_thread_system
PYTHONPATH=. python3 tests/test_thread_pool.py
```

Test coverage:
- ✅ Basic job execution
- ✅ Priority-based ordering
- ✅ Cancellation mechanism
- ✅ Metrics tracking
- ✅ Error handling
- ✅ Context manager
- ✅ Execution time measurement

## Comparison with C++ thread_system

This Python implementation provides a practical subset of the C++ `thread_system` features:

| Feature | C++ | Python | Notes |
|---------|-----|--------|-------|
| Thread Pool | ✅ | ✅ | Based on concurrent.futures |
| Priority Queues | ✅ | ✅ | Using heapq |
| Job Abstraction | ✅ | ✅ | With state tracking |
| Cancellation | ✅ | ✅ | Cooperative cancellation |
| Performance | 13M jobs/s | ~100K jobs/s | GIL limitation |
| Lock-free Queues | ✅ | ❌ | GIL provides implicit synchronization |
| Custom Allocators | ✅ | ❌ | Python manages memory |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

BSD 3-Clause License

Copyright (c) 2025, kcenon
All rights reserved.

## Author

- **kcenon** - [kcenon@naver.com](mailto:kcenon@naver.com)
- GitHub: [https://github.com/kcenon](https://github.com/kcenon)

## Related Projects

- [thread_system](https://github.com/kcenon/thread_system) - C++ version
- [python_logger_system](https://github.com/kcenon/python_logger_system) - Python logging system
- [python_container_system](https://github.com/kcenon/python_container_system) - Python container system
