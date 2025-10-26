"""
Tests for AsyncThreadPool implementation
"""

import asyncio
import time
from thread_module import AsyncThreadPool, JobPriority, JobState


async def test_submit_async():
    """Test async job submission"""
    print("Test 1: Async Submit")

    pool = AsyncThreadPool(max_workers=2)

    def cpu_work(x, y):
        time.sleep(0.1)
        return x + y

    result = await pool.submit_async(cpu_work, 10, 20)

    assert result == 30
    print(f"  ✓ Async submit works: {result}")

    await pool.shutdown_async()
    print()


async def test_map_async():
    """Test async map operation"""
    print("Test 2: Async Map")

    pool = AsyncThreadPool(max_workers=4)

    def square(x):
        return x ** 2

    results = await pool.map_async(square, range(5))

    assert results == [0, 1, 4, 9, 16]
    print(f"  ✓ Async map works: {results}")

    await pool.shutdown_async()
    print()


async def test_error_propagation():
    """Test error propagation to async caller"""
    print("Test 3: Error Propagation")

    pool = AsyncThreadPool(max_workers=2)

    def failing_work():
        raise ValueError("Test error")

    try:
        await pool.submit_async(failing_work)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Test error"
        print(f"  ✓ Error propagated correctly: {e}")

    await pool.shutdown_async()
    print()


async def test_as_completed_async():
    """Test as_completed async generator"""
    print("Test 4: As Completed Async")

    pool = AsyncThreadPool(max_workers=2)

    def work(duration):
        time.sleep(duration)
        return duration

    # Submit jobs with different durations
    jobs = [
        pool.submit(work, 0.1, name="fast"),
        pool.submit(work, 0.3, name="slow"),
        pool.submit(work, 0.2, name="medium"),
    ]

    completed_order = []
    async for job in pool.as_completed_async(jobs):
        completed_order.append(job.name)
        print(f"    Completed: {job.name}")

    # Fast should complete first
    assert completed_order[0] == "fast"
    print(f"  ✓ As completed works: {completed_order}")

    await pool.shutdown_async()
    print()


async def test_wait_all_async():
    """Test async wait for all jobs"""
    print("Test 5: Wait All Async")

    pool = AsyncThreadPool(max_workers=4)

    def work(x):
        time.sleep(0.05)
        return x * 2

    # Submit multiple jobs
    for i in range(10):
        pool.submit(work, i)

    # Wait for all
    completed = await pool.wait_all_async(timeout=2.0)

    assert completed is True
    metrics = pool.get_metrics()
    assert metrics.total_jobs_completed == 10
    print(f"  ✓ Wait all async works: {metrics.total_jobs_completed} jobs")

    await pool.shutdown_async()
    print()


async def test_context_manager_async():
    """Test async context manager"""
    print("Test 6: Async Context Manager")

    results = []

    async with AsyncThreadPool(max_workers=4) as pool:
        for i in range(5):
            result = await pool.submit_async(lambda x: x * 2, i)
            results.append(result)

    # Pool should be shut down automatically
    assert results == [0, 2, 4, 6, 8]
    print(f"  ✓ Async context manager works: {results}")
    print()


async def test_concurrent_async_submissions():
    """Test multiple concurrent async submissions"""
    print("Test 7: Concurrent Async Submissions")

    pool = AsyncThreadPool(max_workers=4)

    def work(x):
        time.sleep(0.01)
        return x * 2

    # Submit many tasks concurrently using asyncio.gather
    tasks = [pool.submit_async(work, i) for i in range(20)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 20
    assert results[10] == 20
    print(f"  ✓ Concurrent submissions work: {len(results)} tasks")

    await pool.shutdown_async()
    print()


async def test_priority_with_async():
    """Test priority execution with async"""
    print("Test 8: Priority with Async")

    pool = AsyncThreadPool(max_workers=1)  # Single worker
    results = []

    def record_work(value):
        results.append(value)
        time.sleep(0.01)
        return value

    # Submit with different priorities
    pool.submit(record_work, 1, priority=JobPriority.LOWEST)
    pool.submit(record_work, 2, priority=JobPriority.LOW)
    pool.submit(record_work, 3, priority=JobPriority.HIGHEST)

    # Wait asynchronously
    await pool.wait_all_async(timeout=1.0)

    # Highest priority should execute first
    assert results[0] == 3
    print(f"  ✓ Priority with async works: {results}")

    await pool.shutdown_async()
    print()


def run_async_tests():
    """Run all async tests"""
    print("=" * 60)
    print("AsyncThreadPool Test Suite")
    print("=" * 60)
    print()

    # Run all tests
    asyncio.run(test_submit_async())
    asyncio.run(test_map_async())
    asyncio.run(test_error_propagation())
    asyncio.run(test_as_completed_async())
    asyncio.run(test_wait_all_async())
    asyncio.run(test_context_manager_async())
    asyncio.run(test_concurrent_async_submissions())
    asyncio.run(test_priority_with_async())

    print("=" * 60)
    print("✅ All async tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_async_tests()
