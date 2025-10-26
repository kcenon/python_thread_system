"""
Tests for ThreadPool implementation
"""

import time
import threading
from thread_module import ThreadPool, Job, JobPriority, JobState, CancellationToken


def test_basic_execution():
    """Test basic job execution"""
    print("Test 1: Basic Execution")

    pool = ThreadPool(max_workers=2)

    def simple_work(x):
        return x * 2

    job = pool.submit(simple_work, 5)

    # Wait for completion
    time.sleep(0.1)

    assert job.state == JobState.COMPLETED
    assert job.result == 10
    print(f"  ✓ Job executed successfully: {job.result}")

    pool.shutdown()
    print()


def test_priority_execution():
    """Test priority-based execution"""
    print("Test 2: Priority Execution")

    pool = ThreadPool(max_workers=1)  # Single worker to test ordering
    results = []
    lock = threading.Lock()

    def record_work(value):
        with lock:
            results.append(value)
        time.sleep(0.01)
        return value

    # Submit jobs in reverse priority order
    pool.submit(record_work, 1, priority=JobPriority.LOWEST)
    pool.submit(record_work, 2, priority=JobPriority.LOW)
    pool.submit(record_work, 3, priority=JobPriority.NORMAL)
    pool.submit(record_work, 4, priority=JobPriority.HIGH)
    pool.submit(record_work, 5, priority=JobPriority.HIGHEST)

    # Wait for all to complete
    time.sleep(0.5)

    # Higher priority jobs should execute first
    print(f"  Execution order: {results}")
    assert results[0] == 5, f"Expected 5 first, got {results[0]}"
    print(f"  ✓ Highest priority executed first")

    pool.shutdown()
    print()


def test_cancellation():
    """Test job cancellation"""
    print("Test 3: Cancellation")

    pool = ThreadPool(max_workers=1)
    token = CancellationToken()

    def cancellable_work():
        for i in range(10):
            if token.is_cancelled():
                raise RuntimeError("Cancelled")
            time.sleep(0.01)
        return "completed"

    job = pool.submit(cancellable_work, cancellation_token=token)

    # Cancel after a short delay
    time.sleep(0.05)
    token.cancel()

    time.sleep(0.2)

    assert job.state == JobState.CANCELLED
    print(f"  ✓ Job cancelled successfully: state={job.state.name}")

    pool.shutdown()
    print()


def test_metrics():
    """Test thread pool metrics"""
    print("Test 4: Metrics")

    pool = ThreadPool(max_workers=4)

    def fast_work(x):
        return x

    # Submit multiple jobs
    jobs = [pool.submit(fast_work, i) for i in range(10)]

    pool.wait_all(timeout=1.0)

    metrics = pool.get_metrics()
    print(f"  Total submitted: {metrics.total_jobs_submitted}")
    print(f"  Total completed: {metrics.total_jobs_completed}")
    print(f"  Total failed: {metrics.total_jobs_failed}")
    print(f"  Active jobs: {metrics.active_jobs}")
    print(f"  Pending jobs: {metrics.pending_jobs}")

    assert metrics.total_jobs_submitted == 10
    assert metrics.total_jobs_completed == 10
    assert metrics.active_jobs == 0
    assert metrics.pending_jobs == 0
    print(f"  ✓ Metrics tracking works correctly")

    pool.shutdown()
    print()


def test_error_handling():
    """Test error handling in jobs"""
    print("Test 5: Error Handling")

    pool = ThreadPool(max_workers=2)

    def failing_work():
        raise ValueError("Test error")

    job = pool.submit(failing_work)
    time.sleep(0.1)

    assert job.state == JobState.FAILED
    assert job.exception is not None
    assert isinstance(job.exception, ValueError)
    print(f"  ✓ Error captured: {job.exception}")

    pool.shutdown()
    print()


def test_context_manager():
    """Test context manager usage"""
    print("Test 6: Context Manager")

    results = []

    with ThreadPool(max_workers=2) as pool:
        for i in range(5):
            pool.submit(lambda x: results.append(x), i)

        pool.wait_all(timeout=1.0)

    # Pool should be shut down automatically
    assert len(results) == 5
    print(f"  ✓ Context manager works: {len(results)} jobs completed")
    print()


def test_execution_time():
    """Test execution time tracking"""
    print("Test 7: Execution Time Tracking")

    pool = ThreadPool(max_workers=1)

    def slow_work():
        time.sleep(0.1)
        return "done"

    job = pool.submit(slow_work)
    pool.wait_all(timeout=1.0)

    exec_time = job.execution_time
    assert exec_time is not None
    assert 0.09 < exec_time < 0.15  # Allow some variance
    print(f"  ✓ Execution time tracked: {exec_time:.3f}s")

    pool.shutdown()
    print()


def main():
    """Run all tests"""
    print("=" * 60)
    print("ThreadPool Test Suite")
    print("=" * 60)
    print()

    test_basic_execution()
    test_priority_execution()
    test_cancellation()
    test_metrics()
    test_error_handling()
    test_context_manager()
    test_execution_time()

    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
