from login_rate_limiter import FailedLoginLimiter


def test_inflight_reservations_respect_max_clients():
    limiter = FailedLoginLimiter(
        max_attempts=5,
        window_seconds=900,
        max_clients=3,
    )

    for number in range(3):
        token = limiter.reserve_attempt(f"192.0.2.{number + 1}")
        assert token is not None

    # The fourth distinct client must not create an
    # additional in-flight client entry.
    extra = limiter.reserve_attempt("192.0.2.4")

    assert extra is None, (
        "In-flight reservations exceeded max_clients"
    )
    assert len(limiter._inflight) <= 3



def test_completed_failures_respect_max_clients():
    limiter = FailedLoginLimiter(
        max_attempts=5,
        window_seconds=900,
        max_clients=3,
    )

    for number in range(3):
        client_ip = f"192.0.2.{number + 1}"
        token = limiter.reserve_attempt(client_ip)

        assert token is not None
        assert limiter.finish_attempt(
            client_ip, token, succeeded=False
        ) is True

    # Capacity is full: a fourth distinct client is rejected.
    assert limiter.reserve_attempt("192.0.2.4") is None

    assert len(limiter._attempts) == 3
    assert len(set(limiter._attempts) | set(limiter._inflight)) <= 3



def test_combined_client_storage_respects_max_clients():
    limiter = FailedLoginLimiter(
        max_attempts=5,
        window_seconds=900,
        max_clients=3,
    )

    # Create two completed-failure client records.
    for number in range(2):
        client_ip = f"192.0.2.{number + 1}"
        token = limiter.reserve_attempt(client_ip)
        assert token is not None
        assert limiter.finish_attempt(
            client_ip, token, succeeded=False
        ) is True

    # Create two additional clients with pending reservations.
    for number in range(2):
        client_ip = f"192.0.2.{number + 3}"
        limiter.reserve_attempt(client_ip)

    distinct_clients = (
        set(limiter._attempts) | set(limiter._inflight)
    )

    assert len(distinct_clients) <= limiter.max_clients, (
        "Combined client storage exceeded max_clients"
    )



def test_capacity_recovers_after_records_expire():
    from unittest.mock import patch

    limiter = FailedLoginLimiter(
        max_attempts=5,
        window_seconds=900,
        max_clients=3,
    )

    with patch("login_rate_limiter.time.monotonic") as clock:
        clock.return_value = 100

        for number in range(3):
            client_ip = f"192.0.2.{number + 1}"
            token = limiter.reserve_attempt(client_ip)
            assert token is not None
            assert limiter.finish_attempt(
                client_ip, token, succeeded=False
            ) is True

        # Capacity is full.
        assert limiter.reserve_attempt("192.0.2.4") is None

        # Existing records have expired.
        clock.return_value = 1001

        # A new client should now be admitted.
        assert limiter.reserve_attempt("192.0.2.4") is not None
