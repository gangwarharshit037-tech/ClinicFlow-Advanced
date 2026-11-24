from unittest.mock import patch

from login_rate_limiter import FailedLoginLimiter


def test_abandoned_reservations_expire():
    limiter = FailedLoginLimiter(max_attempts=5, window_seconds=900)
    client_ip = "192.0.2.10"

    with patch("login_rate_limiter.time.monotonic") as clock:
        clock.return_value = 100

        for _ in range(5):
            assert limiter.reserve_attempt(client_ip) is not None

        assert limiter.reserve_attempt(client_ip) is None

        # Move beyond the 15-minute reservation window.
        clock.return_value = 1001

        # Abandoned reservations must no longer block login.
        assert limiter.reserve_attempt(client_ip) is not None, (
            "Expired in-flight reservations were not cleaned up"
        )
