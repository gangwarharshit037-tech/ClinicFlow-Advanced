from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from login_rate_limiter import FailedLoginLimiter


def test_concurrent_login_checks_do_not_exceed_limit():
    limiter = FailedLoginLimiter(max_attempts=5, window_seconds=900)
    workers = 10
    barrier = Barrier(workers)

    def attempt_login(_):
        barrier.wait(timeout=10)
        return limiter.allow_attempt("192.0.2.10")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(attempt_login, range(workers)))

    assert results.count(True) == 5, (
        f"Expected exactly 5 admitted attempts, got {results.count(True)}"
    )
    assert results.count(False) == 5
    assert limiter.is_blocked("192.0.2.10")
