"""
Tests for advanced features: Dependencies, BoundedQueue, JobGroups
"""

import time
from thread_module import (
    ThreadPool, BoundedThreadPool, QueueFullError,
    DependentJob, JobGroup, JobState
)


def test_job_dependencies():
    """Test job dependency execution"""
    print("Test 1: Job Dependencies")

    pool = ThreadPool(max_workers=4)
    results = []

    def work(name, value):
        results.append((name, value))
        time.sleep(0.05)
        return value

    # Create dependency chain
    job_a = pool.submit(work, "A", 1)
    job_b = pool.submit_with_deps(work, "B", 2, depends_on=[job_a])
    job_c = pool.submit_with_deps(work, "C", 3, depends_on=[job_b])

    pool.wait_all(timeout=2.0)

    # Check execution order
    assert results[0] == ("A", 1)
    assert results[1] == ("B", 2)
    assert results[2] == ("C", 3)
    print(f"  ✓ Dependencies work: {[r[0] for r in results]}")

    pool.shutdown()
    print()


def test_job_group():
    """Test job group management"""
    print("Test 2: Job Group")

    pool = ThreadPool(max_workers=4)

    with pool.create_group("test-group") as group:
        for i in range(5):
            group.submit(lambda x: x * 2, i)

    stats = group.statistics
    assert stats["total"] == 5
    assert stats["completed"] == 5
    print(f"  ✓ Job group works: {stats['completed']}/{stats['total']} completed")
    print()


def test_bounded_queue_block():
    """Test bounded queue with blocking"""
    print("Test 3: Bounded Queue (Block)")

    pool = BoundedThreadPool(
        max_workers=1,
        max_queue_size=3,
        on_queue_full="block"
    )

    def slow_work(x):
        time.sleep(0.1)
        return x

    # Submit jobs
    jobs = []
    for i in range(5):
        job = pool.submit(slow_work, i, block=True, timeout=1.0)
        jobs.append(job)

    pool.wait_all(timeout=2.0)

    # All should complete despite queue limit
    completed = sum(1 for j in jobs if j.state == JobState.COMPLETED)
    assert completed == 5
    print(f"  ✓ Bounded queue blocking works: {completed}/5 completed")

    pool.shutdown()
    print()


def test_bounded_queue_reject():
    """Test bounded queue with rejection"""
    print("Test 4: Bounded Queue (Reject)")

    pool = BoundedThreadPool(
        max_workers=1,
        max_queue_size=2,
        on_queue_full="reject"
    )

    def slow_work():
        time.sleep(0.5)

    # Fill queue
    pool.submit(slow_work)
    pool.submit(slow_work)

    # Next should be rejected
    try:
        pool.submit(slow_work, block=False)
        assert False, "Should have raised QueueFullError"
    except QueueFullError:
        print(f"  ✓ Bounded queue rejection works: QueueFullError raised")

    pool.shutdown()
    print()


def test_multiple_dependencies():
    """Test job with multiple dependencies"""
    print("Test 5: Multiple Dependencies")

    pool = ThreadPool(max_workers=4)
    results = []

    def work(name):
        results.append(name)
        time.sleep(0.05)
        return name

    # Fan-out and fan-in
    job_a = pool.submit(work, "A")
    job_b = pool.submit(work, "B")
    job_c = pool.submit_with_deps(work, "C", depends_on=[job_a, job_b])

    pool.wait_all(timeout=1.0)

    # C should execute after both A and B
    assert "C" in results
    c_index = results.index("C")
    assert "A" in results[:c_index]
    assert "B" in results[:c_index]
    print(f"  ✓ Multiple dependencies work: {results}")

    pool.shutdown()
    print()


def test_group_statistics():
    """Test job group statistics"""
    print("Test 6: Group Statistics")

    pool = ThreadPool(max_workers=2)
    group = pool.create_group("stats-test")

    # Mix of successful and failing jobs
    for i in range(10):
        if i % 3 == 0:
            group.submit(lambda: 1 / 0)  # Will fail
        else:
            group.submit(lambda x: x, i)

    group.wait(timeout=1.0)

    stats = group.statistics
    assert stats["total"] == 10
    assert stats["failed"] >= 3
    assert stats["completed"] >= 6
    print(f"  ✓ Group statistics work: {stats}")

    pool.shutdown()
    print()


def main():
    """Run all tests"""
    print("=" * 60)
    print("Advanced Features Test Suite")
    print("=" * 60)
    print()

    test_job_dependencies()
    test_job_group()
    test_bounded_queue_block()
    test_bounded_queue_reject()
    test_multiple_dependencies()
    test_group_statistics()

    print("=" * 60)
    print("✅ All advanced feature tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
