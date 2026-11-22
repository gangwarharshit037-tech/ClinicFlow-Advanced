import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "demo_mode, cookie_override, expected_secure",
    [
        ("true", None, True),
        ("false", None, False),
        ("false", "true", True),
        ("false", "false", False),
        ("true", "false", True),
    ],
)
def test_session_cookie_configuration(
    tmp_path, demo_mode, cookie_override, expected_secure
):
    db_path = tmp_path / "session_config.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "PUBLIC_DEMO_MODE": demo_mode,
        "LIVE_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
        "SECRET_KEY": "session-cookie-test-secret",
        "ADMIN_PASSWORD": "SessionCookieTestPassword2026!",
    })

    # Test the optional secure cookie override.
    if cookie_override is None:
        env.pop("SESSION_COOKIE_SECURE", None)
    else:
        env["SESSION_COOKIE_SECURE"] = cookie_override

    code = """
import app

assert str(app.DB) == EXPECTED_DB
assert app.LIVE is False
assert app.scheduler.running is False

config = app.app.config

assert config["SESSION_COOKIE_HTTPONLY"] is True
assert config["SESSION_COOKIE_SAMESITE"] == "Lax"
assert config["SESSION_COOKIE_SECURE"] is EXPECTED_SECURE

print("PASSED: Session cookie configuration")
"""

    code = (
        "EXPECTED_DB = " + repr(str(db_path)) + "\n"
        + "EXPECTED_SECURE = " + repr(expected_secure) + "\n"
        + code
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        "STDOUT:\n" + result.stdout
        + "\nSTDERR:\n" + result.stderr
    )

    assert db_path.is_file()
