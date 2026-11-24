from unittest.mock import patch

from login_rate_limiter import FailedLoginLimiter


def test_expired_reservation_cannot_be_finished():
    limiter = FailedLoginLimiter(max_attempts=5, window_seconds=900)
    client_ip = "192.0.2.10"

    with patch("login_rate_limiter.time.monotonic") as clock:
        clock.return_value = 100
        token = limiter.reserve_attempt(client_ip)

        assert token is not None

        # The reservation has expired.
        clock.return_value = 1001

        # An expired token must not be accepted as active.
        assert limiter.finish_attempt(
            client_ip, token, succeeded=False
        ) is False

        assert limiter.is_blocked(client_ip) is False
