import os
import subprocess
import sys


def test_admin_authentication_and_logout(tmp_path):
    db_path = tmp_path / "admin_security.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "ADMIN_PASSWORD": "ClinicFlowTestPassword2026!",
        "SECRET_KEY": "clinicflow-security-test-only-key",
        "LIVE_MODE": "false",
        "PUBLIC_DEMO_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
    })

    code = r"""
import app

assert str(app.DB) == EXPECTED_DB
assert app.LIVE is False
assert app.scheduler.running is False

client = app.app.test_client()

appointments = "/api/admin/appointments"
analytics = "/api/admin/analytics"

# Anonymous users cannot access admin APIs.
assert client.get(appointments).status_code == 401
assert client.get(analytics).status_code == 401

# Incorrect passwords must be rejected.
wrong = client.post(
    "/admin/login",
    json={"password": "IncorrectPassword123!"}
)
assert wrong.status_code == 401

# Correct test credentials establish an admin session.
correct = client.post(
    "/admin/login",
    json={"password": "ClinicFlowTestPassword2026!"}
)
assert correct.status_code == 200
assert correct.get_json()["ok"] is True

with client.session_transaction() as session:
    assert session.get("admin") is True
    csrf = session.get("csrf")
    assert isinstance(csrf, str) and len(csrf) >= 24

assert client.get(appointments).status_code == 200
assert client.get(analytics).status_code == 200

# Logout requires the correct CSRF token.
assert client.post("/admin/logout").status_code == 403

assert client.post(
    "/admin/logout",
    headers={"X-CSRF-Token": "invalid-token"}
).status_code == 403

# A rejected logout must preserve authentication.
assert client.get(appointments).status_code == 200

logout = client.post(
    "/admin/logout",
    headers={"X-CSRF-Token": csrf}
)
assert logout.status_code == 200
assert logout.get_json()["ok"] is True

# Logout must revoke admin API access.
assert client.get(appointments).status_code == 401
assert client.get(analytics).status_code == 401

print("PASSED: Admin authentication and logout security")
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
        "STDOUT:\n" + result.stdout
        + "\nSTDERR:\n" + result.stderr
    )

    assert db_path.is_file()
