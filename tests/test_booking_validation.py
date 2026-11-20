import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"patient": "", "phone": "+919876543210"},
        {"patient": "Test Patient", "phone": "invalid"},
        {
            "patient": "Test Patient",
            "phone": "+919876543210",
            "doctor": "Unknown Doctor",
            "date": "2099-01-01",
            "time": "10:00",
        },
    ],
)
def test_invalid_booking_rejected(tmp_path, payload):
    db_path = tmp_path / "booking_validation.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "LIVE_MODE": "false",
    })

    code = """
import json
import sqlite3
import app

assert str(app.DB) == EXPECTED_DB
assert app.scheduler.running is False

client = app.app.test_client()
response = client.post('/api/book', json=PAYLOAD)

assert response.status_code == 400, (
    response.status_code,
    response.get_json()
)

with sqlite3.connect(EXPECTED_DB) as db:
    count = db.execute(
        'SELECT COUNT(*) FROM appointments'
    ).fetchone()[0]

assert count == 0
"""

    code = (
        "EXPECTED_DB = " + repr(str(db_path)) + "\n"
        + "PAYLOAD = " + repr(payload) + "\n"
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
