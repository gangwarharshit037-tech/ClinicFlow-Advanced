from login_rate_limiter import FailedLoginLimiter


def test_success_preserves_another_inflight_failed_attempt():
    limiter = FailedLoginLimiter(max_attempts=5, window_seconds=900)
    client_ip = "192.0.2.10"

    # Two overlapping requests reserve separate attempts.
    first = limiter.reserve_attempt(client_ip)
    second = limiter.reserve_attempt(client_ip)

    assert first is not None
    assert second is not None
    assert first != second

    # First request succeeds; second request fails.
    limiter.finish_attempt(client_ip, first, succeeded=True)
    limiter.finish_attempt(client_ip, second, succeeded=False)

    # The failed second request must still count.
    results = [
        limiter.reserve_attempt(client_ip)
        for _ in range(4)
    ]

    assert sum(token is not None for token in results) == 4
    assert limiter.reserve_attempt(client_ip) is None
