from login_rate_limiter import FailedLoginLimiter


def test_forwarded_header_cannot_bypass_ip_limit():
    from flask import Flask, request

    app = Flask(__name__)
    limiter = FailedLoginLimiter(max_attempts=5)

    @app.post("/check")
    def check():
        client_ip = request.remote_addr or "unknown"

        if limiter.is_blocked(client_ip):
            return {"blocked": True}, 429

        limiter.record_failure(client_ip)
        return {"blocked": False}, 401

    with app.test_client() as client:
        for i in range(5):
            response = client.post(
                "/check",
                environ_overrides={"REMOTE_ADDR": "192.0.2.10"},
                headers={"X-Forwarded-For": f"198.51.100.{i + 1}"},
            )
            assert response.status_code == 401

        response = client.post(
            "/check",
            environ_overrides={"REMOTE_ADDR": "192.0.2.10"},
            headers={"X-Forwarded-For": "203.0.113.99"},
        )

        assert response.status_code == 429
