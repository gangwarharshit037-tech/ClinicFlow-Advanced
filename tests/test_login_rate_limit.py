import os
import subprocess
import sys


def test_admin_login_rate_limit(tmp_path):
    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(tmp_path / "rate_limit.db"),
        "ADMIN_PASSWORD": "ClinicFlowTestPassword2026!",
        "SECRET_KEY": "clinicflow-rate-limit-test-key",
        "PUBLIC_DEMO_MODE": "false",
        "LIVE_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
    })

    code = r"""
import app

client = app.app.test_client()

for attempt in range(5):
    response = client.post(
        "/admin/login",
        json={"password": "IncorrectPassword123!"},
        environ_overrides={"REMOTE_ADDR": "192.0.2.10"},
    )
    assert response.status_code == 401, (
        f"Attempt {attempt + 1}: expected 401, "
        f"got {response.status_code}"
    )

blocked = client.post(
    "/admin/login",
    json={"password": "IncorrectPassword123!"},
    environ_overrides={"REMOTE_ADDR": "192.0.2.10"},
)
assert blocked.status_code == 429, (
    f"Expected 429 after five failures, "
    f"got {blocked.status_code}"
)

other_client = client.post(
    "/admin/login",
    json={"password": "ClinicFlowTestPassword2026!"},
    environ_overrides={"REMOTE_ADDR": "192.0.2.11"},
)
assert other_client.status_code == 200

print("PASSED: Admin login rate limiting")
"""

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
