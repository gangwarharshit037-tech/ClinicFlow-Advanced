import os
import subprocess
import sys


def test_successful_booking_and_duplicate_protection(tmp_path):
    db_path = tmp_path / "booking_success.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "LIVE_MODE": "false",
    })

    code = """
import sqlite3
from datetime import timedelta
from unittest.mock import patch

import app

assert str(app.DB) == EXPECTED_DB
assert app.LIVE is False
assert app.scheduler.running is False

# Choose a valid future appointment within 180 days.
future = app.now() + timedelta(days=7)
day = future.date().isoformat()

payload = {
    "patient": "Automated Test Patient",
    "phone": "+919876543210",
    "doctor": app.DOCTORS[0],
    "date": day,
    "time": "10:00",
}

client = app.app.test_client()

# Prevent Google Calendar integration from running.
with patch.object(
    app, "create_calendar_event", return_value=None
) as mock_calendar:

    first = client.post("/api/book", json=payload)

    assert first.status_code == 201, (
        first.status_code,
        first.get_json()
    )

    first_data = first.get_json()
    assert isinstance(first_data.get("id"), int)

    second = client.post("/api/book", json=payload)

    assert second.status_code == 409, (
        second.status_code,
        second.get_json()
    )

    assert mock_calendar.call_count == 1

with sqlite3.connect(EXPECTED_DB) as db:
    count = db.execute(
        "SELECT COUNT(*) FROM appointments"
    ).fetchone()[0]

assert count == 1

print("PASSED: Successful booking returns 201")
print("PASSED: Duplicate booking returns 409")
print("PASSED: Exactly one appointment stored")
print("PASSED: Calendar API mocked")
"""

    code = (
        "EXPECTED_DB = " + repr(str(db_path)) + "\n"
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
