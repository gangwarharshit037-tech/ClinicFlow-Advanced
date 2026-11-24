from unittest.mock import patch

from login_rate_limiter import FailedLoginLimiter


def test_expired_attempts_are_removed():
    limiter = FailedLoginLimiter(max_attempts=5, window_seconds=900)

    with patch("login_rate_limiter.time.monotonic") as clock:
        clock.return_value = 0

        for _ in range(4):
            limiter.record_failure("192.0.2.10")

        assert not limiter.is_blocked("192.0.2.10")

        clock.return_value = 899
        limiter.record_failure("192.0.2.10")
        assert limiter.is_blocked("192.0.2.10")

        clock.return_value = 900
        assert not limiter.is_blocked("192.0.2.10")


def test_successful_login_reset_behavior():
    limiter = FailedLoginLimiter(max_attempts=5, window_seconds=900)

    for _ in range(5):
        limiter.record_failure("192.0.2.10")

    assert limiter.is_blocked("192.0.2.10")

    limiter.clear("192.0.2.10")

    assert not limiter.is_blocked("192.0.2.10")


def test_different_clients_are_independent():
    limiter = FailedLoginLimiter(max_attempts=5, window_seconds=900)

    for _ in range(5):
        limiter.record_failure("192.0.2.10")

    assert limiter.is_blocked("192.0.2.10")
    assert not limiter.is_blocked("192.0.2.11")
