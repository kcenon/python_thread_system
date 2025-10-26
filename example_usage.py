"""
Example usage of python_thread_system
"""

from thread_module import ThreadPool, JobPriority, CancellationToken
import time


def example1_basic_usage():
    """Basic thread pool usage"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    pool = ThreadPool(max_workers=4)

    def work(x, y):
        return x + y

    job = pool.submit(work, 10, 20, priority=JobPriority.HIGH)

    pool.wait_all(timeout=1.0)

    print(f"Result: {job.result}")
    print(f"Execution time: {job.execution_time:.6f}s")
    print(f"Job state: {job.state.name}")

    metrics = pool.get_metrics()
    print(f"Metrics: {metrics}")

    pool.shutdown()
    print()


def example2_priority_execution():
    """Priority-based execution"""
    print("=" * 60)
    print("Example 2: Priority Execution")
    print("=" * 60)

    results = []

    with ThreadPool(max_workers=1) as pool:  # Single worker to see order
        def record(name, priority):
            results.append((name, priority))
            time.sleep(0.01)
            return name

        # Submit in reverse priority order
        pool.submit(record, "Task 1", JobPriority.LOWEST, priority=JobPriority.LOWEST)
        pool.submit(record, "Task 2", JobPriority.LOW, priority=JobPriority.LOW)
        pool.submit(record, "Task 3", JobPriority.NORMAL, priority=JobPriority.NORMAL)
        pool.submit(record, "Task 4", JobPriority.HIGH, priority=JobPriority.HIGH)
        pool.submit(record, "Task 5", JobPriority.HIGHEST, priority=JobPriority.HIGHEST)

        pool.wait_all()

    print("Execution order (by priority):")
    for name, priority in results:
        print(f"  {name}: {priority.name}")
    print()


def example3_cancellation():
    """Job cancellation with token"""
    print("=" * 60)
    print("Example 3: Cancellation")
    print("=" * 60)

    pool = ThreadPool(max_workers=2)
    token = CancellationToken()

    def long_work():
        for i in range(10):
            if token.is_cancelled():
                print("  Work cancelled at iteration", i)
                raise RuntimeError("Cancelled")
            time.sleep(0.05)
        return "Completed"

    job = pool.submit(long_work, cancellation_token=token)

    # Cancel after 0.15 seconds (should cancel around iteration 3)
    time.sleep(0.15)
    print("Requesting cancellation...")
    token.cancel()

    pool.wait_all(timeout=1.0)

    print(f"Final state: {job.state.name}")
    if job.exception:
        print(f"Exception: {job.exception}")

    pool.shutdown()
    print()


def example4_metrics_tracking():
    """Performance metrics tracking"""
    print("=" * 60)
    print("Example 4: Metrics Tracking")
    print("=" * 60)

    with ThreadPool(max_workers=4) as pool:
        # Submit mix of successful and failing jobs
        for i in range(10):
            if i % 3 == 0:
                # Failing job
                pool.submit(lambda: 1 / 0, name=f"failing-{i}")
            else:
                # Successful job
                pool.submit(lambda x: x * 2, i, name=f"success-{i}")

        pool.wait_all(timeout=1.0)

        metrics = pool.get_metrics()
        print(f"Total submitted: {metrics.total_jobs_submitted}")
        print(f"Total completed: {metrics.total_jobs_completed}")
        print(f"Total failed: {metrics.total_jobs_failed}")
        print(f"Success rate: {metrics.total_jobs_completed / metrics.total_jobs_submitted * 100:.1f}%")
    print()


def example5_context_manager():
    """Using context manager for automatic cleanup"""
    print("=" * 60)
    print("Example 5: Context Manager")
    print("=" * 60)

    results = []

    with ThreadPool(max_workers=4) as pool:
        jobs = [pool.submit(lambda x: x ** 2, i) for i in range(10)]

        pool.wait_all()

        for job in jobs:
            results.append(job.result)

    print(f"Squares: {results}")
    print("Pool automatically shut down after context exit")
    print()


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Python Thread System Examples" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    example1_basic_usage()
    example2_priority_execution()
    example3_cancellation()
    example4_metrics_tracking()
    example5_context_manager()

    print("=" * 60)
    print("✅ All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
