import os
import subprocess
import sys


def test_homepage_loads_safely(tmp_path):
    """Test Flask in a separate Python process and temporary database."""

    db_path = tmp_path / "clinicflow_test.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "LIVE_MODE": "false",
    })

    code = """
import app

assert str(app.DB) == EXPECTED_DB
assert app.LIVE is False
assert app.scheduler.running is False

client = app.app.test_client()
response = client.get('/')

assert response.status_code == 200
assert b'<html' in response.data.lower()
"""

    code = "EXPECTED_DB = " + repr(str(db_path)) + "\n" + code

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        "STDOUT:\n" + result.stdout +
        "\nSTDERR:\n" + result.stderr
    )

    assert db_path.is_file()
