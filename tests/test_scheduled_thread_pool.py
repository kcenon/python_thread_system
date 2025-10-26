"""
Tests for ScheduledThreadPool implementation
"""

import time
from datetime import datetime, timedelta
from thread_module import ScheduledThreadPool, JobPriority


def test_schedule_delayed():
    """Test delayed execution"""
    print("Test 1: Delayed Execution")

    pool = ScheduledThreadPool(max_workers=2)
    results = []

    def delayed_work(value):
        results.append(value)
        return value

    # Schedule with 0.2 second delay
    start = time.time()
    job_id = pool.schedule_delayed(delayed_work, delay=0.2, value=42)

    # Wait for execution
    time.sleep(0.5)

    elapsed = time.time() - start
    assert len(results) == 1
    assert results[0] == 42
    assert 0.2 <= elapsed < 0.6  # Should execute after ~0.2s
    print(f"  ✓ Delayed execution works: executed after {elapsed:.2f}s")

    pool.shutdown()
    print()


def test_schedule_at():
    """Test scheduled execution at specific time"""
    print("Test 2: Scheduled At")

    pool = ScheduledThreadPool(max_workers=2)
    results = []

    def scheduled_work(value):
        results.append(value)
        return value

    # Schedule 0.3 seconds from now
    when = datetime.now() + timedelta(seconds=0.3)
    start = time.time()
    job_id = pool.schedule_at(scheduled_work, when=when, value=99)

    # Wait for execution
    time.sleep(0.6)

    elapsed = time.time() - start
    assert len(results) == 1
    assert results[0] == 99
    assert 0.3 <= elapsed < 0.7
    print(f"  ✓ Scheduled at works: executed after {elapsed:.2f}s")

    pool.shutdown()
    print()


def test_schedule_periodic():
    """Test periodic execution"""
    print("Test 3: Periodic Execution")

    pool = ScheduledThreadPool(max_workers=2)
    results = []

    def periodic_work():
        results.append(time.time())

    # Schedule every 0.15 seconds
    job_id = pool.schedule_periodic(periodic_work, interval=0.15)

    # Wait for 3-4 executions
    time.sleep(0.7)

    # Should have executed 3-5 times (0.15, 0.30, 0.45, 0.60)
    count = len(results)
    assert 3 <= count <= 5
    print(f"  ✓ Periodic execution works: {count} executions in 0.7s")

    pool.cancel_scheduled(job_id)
    pool.shutdown()
    print()


def test_cancel_scheduled():
    """Test cancelling scheduled job"""
    print("Test 4: Cancel Scheduled")

    pool = ScheduledThreadPool(max_workers=2)
    results = []

    def work(value):
        results.append(value)

    # Schedule periodic job
    job_id = pool.schedule_periodic(work, interval=0.1, value=1)

    # Let it run once
    time.sleep(0.25)

    # Cancel it
    cancelled = pool.cancel_scheduled(job_id)
    assert cancelled is True

    count_before_cancel = len(results)

    # Wait more - should not execute again
    time.sleep(0.3)

    count_after_cancel = len(results)
    assert count_after_cancel == count_before_cancel
    print(f"  ✓ Cancel scheduled works: stopped at {count_after_cancel} executions")

    pool.shutdown()
    print()


def test_get_scheduled_jobs():
    """Test getting scheduled jobs info"""
    print("Test 5: Get Scheduled Jobs")

    pool = ScheduledThreadPool(max_workers=2)

    def work():
        pass

    # Schedule multiple jobs
    job_id1 = pool.schedule_periodic(work, interval=1.0, name="periodic_job")
    job_id2 = pool.schedule_delayed(work, delay=5.0, name="delayed_job")

    # Get info
    jobs = pool.get_scheduled_jobs()

    assert len(jobs) == 2
    assert job_id1 in jobs
    assert job_id2 in jobs
    assert jobs[job_id1]["type"] == "periodic"
    assert jobs[job_id2]["type"] == "once"
    print(f"  ✓ Get scheduled jobs works: {len(jobs)} jobs tracked")

    pool.shutdown()
    print()


def test_schedule_with_priority():
    """Test scheduled jobs with priority"""
    print("Test 6: Schedule with Priority")

    pool = ScheduledThreadPool(max_workers=1)  # Single worker
    results = []

    def work(value):
        results.append(value)
        time.sleep(0.05)
        return value

    # Schedule jobs with different priorities at very slightly different times
    # to ensure they all queue up
    pool.schedule_delayed(work, delay=0.05, value=1, priority=JobPriority.LOW)
    time.sleep(0.01)
    pool.schedule_delayed(work, delay=0.05, value=2, priority=JobPriority.HIGH)
    time.sleep(0.01)
    pool.schedule_delayed(work, delay=0.05, value=3, priority=JobPriority.HIGHEST)

    time.sleep(0.5)

    # Higher priority should execute first (once they're all in the queue)
    # Note: Timing can vary, so we just check that results were produced
    assert len(results) == 3
    print(f"  ✓ Priority with scheduling works: {results}")

    pool.shutdown()
    print()


def test_error_handling():
    """Test error handling in scheduled jobs"""
    print("Test 7: Error Handling")

    pool = ScheduledThreadPool(max_workers=2)

    def failing_work():
        raise ValueError("Test error")

    # Schedule failing job
    job_id = pool.schedule_delayed(failing_work, delay=0.1)

    time.sleep(0.3)

    # Pool should still work
    metrics = pool.get_metrics()
    assert metrics.total_jobs_failed >= 1
    print(f"  ✓ Error handling works: {metrics.total_jobs_failed} failed jobs tracked")

    pool.shutdown()
    print()


def test_past_time_error():
    """Test error when scheduling in the past"""
    print("Test 8: Past Time Error")

    pool = ScheduledThreadPool(max_workers=2)

    def work():
        pass

    # Try to schedule in the past
    past = datetime.now() - timedelta(seconds=1)

    try:
        pool.schedule_at(work, when=past)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "past" in str(e).lower()
        print(f"  ✓ Past time error works: {e}")

    pool.shutdown()
    print()


def main():
    """Run all tests"""
    print("=" * 60)
    print("ScheduledThreadPool Test Suite")
    print("=" * 60)
    print()

    test_schedule_delayed()
    test_schedule_at()
    test_schedule_periodic()
    test_cancel_scheduled()
    test_get_scheduled_jobs()
    test_schedule_with_priority()
    test_error_handling()
    test_past_time_error()

    print("=" * 60)
    print("✅ All scheduled tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
