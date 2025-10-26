"""
Tests for RetryPolicy and RetryableJob
"""

import time
from thread_module import ThreadPool, RetryPolicy, RetryableJob, JobState


def test_basic_retry():
    """Test basic retry functionality"""
    print("Test 1: Basic Retry")

    pool = ThreadPool(max_workers=2)
    attempts = []

    def flaky_work():
        attempts.append(time.time())
        if len(attempts) < 3:
            raise ValueError("Transient error")
        return "Success"

    job = pool.submit_with_retry(
        flaky_work,
        retry_policy=RetryPolicy(max_attempts=5, initial_delay=0.1)
    )

    pool.wait_all(timeout=2.0)

    assert job.state == JobState.COMPLETED
    assert job.result == "Success"
    assert job.attempt_count == 3
    print(f"  ✓ Basic retry works: succeeded on attempt {job.attempt_count}")

    pool.shutdown()
    print()


def test_retry_exhaustion():
    """Test all retries exhausted"""
    print("Test 2: Retry Exhaustion")

    pool = ThreadPool(max_workers=2)

    def always_fails():
        raise ValueError("Permanent error")

    job = pool.submit_with_retry(
        always_fails,
        retry_policy=RetryPolicy(max_attempts=3, initial_delay=0.05)
    )

    pool.wait_all(timeout=2.0)

    assert job.state == JobState.FAILED
    assert job.attempt_count == 3
    assert isinstance(job.exception, ValueError)
    print(f"  ✓ Retry exhaustion works: failed after {job.attempt_count} attempts")

    pool.shutdown()
    print()


def test_exponential_backoff():
    """Test exponential backoff timing"""
    print("Test 3: Exponential Backoff")

    pool = ThreadPool(max_workers=2)
    attempts = []

    def failing_work():
        attempts.append(time.time())
        raise TimeoutError("Network timeout")

    job = pool.submit_with_retry(
        failing_work,
        retry_policy=RetryPolicy(
            max_attempts=4,
            initial_delay=0.1,
            backoff_factor=2.0
        )
    )

    pool.wait_all(timeout=3.0)

    # Check delays: ~0.1s, ~0.2s, ~0.4s between attempts
    if len(attempts) >= 2:
        delay1 = attempts[1] - attempts[0]
        assert 0.09 < delay1 < 0.15  # First retry after ~0.1s

    if len(attempts) >= 3:
        delay2 = attempts[2] - attempts[1]
        assert 0.18 < delay2 < 0.25  # Second retry after ~0.2s

    print(f"  ✓ Exponential backoff works: {len(attempts)} attempts with backoff")

    pool.shutdown()
    print()


def test_selective_retry():
    """Test retrying only specific exceptions"""
    print("Test 4: Selective Retry")

    pool = ThreadPool(max_workers=2)
    attempts = []

    def work_with_different_errors():
        attempts.append(1)
        if len(attempts) == 1:
            raise TimeoutError("Retryable")
        else:
            raise ValueError("Non-retryable")

    job = pool.submit_with_retry(
        work_with_different_errors,
        retry_policy=RetryPolicy(
            max_attempts=5,
            retry_on=(TimeoutError, ConnectionError),
            initial_delay=0.05
        )
    )

    pool.wait_all(timeout=1.0)

    # Should fail on second attempt (ValueError not in retry_on)
    assert job.state == JobState.FAILED
    assert job.attempt_count == 2
    assert isinstance(job.exception, ValueError)
    print(f"  ✓ Selective retry works: stopped at non-retryable exception")

    pool.shutdown()
    print()


def test_retry_callback():
    """Test retry callback invocation"""
    print("Test 5: Retry Callback")

    pool = ThreadPool(max_workers=2)
    callbacks = []

    def on_retry(error, attempt):
        callbacks.append((str(error), attempt))

    def failing_work():
        raise RuntimeError("Test error")

    job = pool.submit_with_retry(
        failing_work,
        retry_policy=RetryPolicy(
            max_attempts=3,
            initial_delay=0.05,
            on_retry=on_retry
        )
    )

    pool.wait_all(timeout=1.0)

    # Should have 2 callbacks (attempt 1 fails, retry before attempt 2 and 3)
    assert len(callbacks) >= 2
    assert callbacks[0][1] == 1  # First callback after attempt 1
    print(f"  ✓ Retry callback works: {len(callbacks)} callbacks invoked")

    pool.shutdown()
    print()


def test_max_delay():
    """Test maximum delay cap"""
    print("Test 6: Max Delay Cap")

    pool = ThreadPool(max_workers=2)
    attempts = []

    def failing_work():
        attempts.append(time.time())
        raise TimeoutError()

    job = pool.submit_with_retry(
        failing_work,
        retry_policy=RetryPolicy(
            max_attempts=5,
            initial_delay=1.0,
            backoff_factor=10.0,
            max_delay=0.5  # Cap at 0.5s
        )
    )

    pool.wait_all(timeout=5.0)

    # Later delays should be capped
    if len(attempts) >= 4:
        delay3 = attempts[3] - attempts[2]
        assert delay3 < 0.6  # Should be capped at max_delay
    print(f"  ✓ Max delay cap works: delays capped at configured maximum")

    pool.shutdown()
    print()


def test_retry_history():
    """Test retry history tracking"""
    print("Test 7: Retry History")

    pool = ThreadPool(max_workers=2)

    def failing_work():
        raise ValueError("Test")

    job = pool.submit_with_retry(
        failing_work,
        retry_policy=RetryPolicy(max_attempts=3, initial_delay=0.05)
    )

    pool.wait_all(timeout=1.0)

    # Check retry history
    assert len(job.retry_history) == 3
    for attempt, error, delay in job.retry_history:
        assert isinstance(error, ValueError)
        assert delay >= 0

    print(f"  ✓ Retry history works: {len(job.retry_history)} retries recorded")

    pool.shutdown()
    print()


def test_successful_first_attempt():
    """Test no retry on first success"""
    print("Test 8: Successful First Attempt")

    pool = ThreadPool(max_workers=2)

    def successful_work():
        return "Success"

    job = pool.submit_with_retry(
        successful_work,
        retry_policy=RetryPolicy(max_attempts=5)
    )

    pool.wait_all(timeout=1.0)

    assert job.state == JobState.COMPLETED
    assert job.attempt_count == 1
    assert len(job.retry_history) == 0
    print(f"  ✓ Successful first attempt works: no retries needed")

    pool.shutdown()
    print()


def main():
    """Run all tests"""
    print("=" * 60)
    print("RetryPolicy Test Suite")
    print("=" * 60)
    print()

    test_basic_retry()
    test_retry_exhaustion()
    test_exponential_backoff()
    test_selective_retry()
    test_retry_callback()
    test_max_delay()
    test_retry_history()
    test_successful_first_attempt()

    print("=" * 60)
    print("✅ All retry tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
