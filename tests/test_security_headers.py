"""Regression tests for browser security headers."""

import os
import subprocess
import sys


def test_x_content_type_options():
    script = """
import os

os.environ["LIVE_MODE"] = "false"
os.environ["ENABLE_SCHEDULER"] = "false"

from app import app

with app.test_client() as client:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"
    assert response.headers.get("Content-Security-Policy") == (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    assert response.headers.get("Content-Security-Policy-Report-Only") is None
"""

    env = os.environ.copy()
    env["LIVE_MODE"] = "false"
    env["ENABLE_SCHEDULER"] = "false"

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, (
        result.stdout + "\n" + result.stderr
    )
