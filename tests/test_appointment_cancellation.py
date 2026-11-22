import os
import subprocess
import sys


def test_appointment_cancellation_security(tmp_path):
    db_path = tmp_path / "cancellation_test.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "ADMIN_PASSWORD": "ClinicFlowCancellationTest2026!",
        "SECRET_KEY": "clinicflow-cancellation-test-only-key",
        "LIVE_MODE": "false",
        "PUBLIC_DEMO_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
    })

    code = r"""
import sqlite3
from unittest.mock import patch

import app

assert str(app.DB) == EXPECTED_DB
assert app.LIVE is False
assert app.scheduler.running is False

client = app.app.test_client()

with sqlite3.connect(EXPECTED_DB) as db:
    cursor = db.execute(
        "INSERT INTO appointments "
        "(patient, phone, doctor, date, time, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "Cancellation Test Patient",
            "+12025550199",
            app.DOCTORS[0],
            "2026-12-15",
            "10:00",
            "Booked",
        ),
    )
    appointment_id = cursor.lastrowid

endpoint = (
    f"/api/admin/appointments/{appointment_id}/cancel"
)

def status():
    with sqlite3.connect(EXPECTED_DB) as db:
        return db.execute(
            "SELECT status FROM appointments WHERE id=?",
            (appointment_id,),
        ).fetchone()[0]

assert status() == "Booked"

# Anonymous cancellation must be rejected.
assert client.post(endpoint).status_code == 401
assert status() == "Booked"

# Authenticate using fictional test credentials.
login = client.post(
    "/admin/login",
    json={"password": "ClinicFlowCancellationTest2026!"},
)
assert login.status_code == 200

with client.session_transaction() as session:
    csrf = session["csrf"]

# Missing and invalid CSRF tokens must be rejected.
assert client.post(endpoint).status_code == 403
assert status() == "Booked"

assert client.post(
    endpoint,
    headers={"X-CSRF-Token": "invalid-token"},
).status_code == 403
assert status() == "Booked"

# Successful cancellation must update the database.
# External calendar deletion is mocked.
with patch.object(app, "delete_calendar_event") as calendar:
    response = client.post(
        endpoint,
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    calendar.assert_called_once_with(None)

assert status() == "Cancelled"

# A cancelled appointment cannot be cancelled again.
repeat = client.post(
    endpoint,
    headers={"X-CSRF-Token": csrf},
)
assert repeat.status_code == 404
assert status() == "Cancelled"

# Nonexistent appointments must return 404.
missing = client.post(
    "/api/admin/appointments/999999999/cancel",
    headers={"X-CSRF-Token": csrf},
)
assert missing.status_code == 404

with sqlite3.connect(EXPECTED_DB) as db:
    rows = db.execute(
        "SELECT COUNT(*) FROM appointments"
    ).fetchone()[0]

assert rows == 1

print("PASSED: Cancellation security and database consistency")
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
