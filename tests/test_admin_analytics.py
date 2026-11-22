import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("scenario", ["empty", "sample"])
def test_admin_analytics(tmp_path, scenario):
    """Verify analytics in an isolated Python process and SQLite DB."""

    db_path = tmp_path / "analytics_test.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "LIVE_MODE": "false",
        "PUBLIC_DEMO_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
        "ADMIN_PASSWORD": "AnalyticsTestPassword2026!",
        "SECRET_KEY": "analytics-test-secret-key-not-for-production",
    })

    code = r"""
import json
import sqlite3
import app

assert str(app.DB) == EXPECTED_DB
assert app.LIVE is False
assert app.scheduler.running is False

client = app.app.test_client()
endpoint = "/api/admin/analytics"

# Anonymous users must not access analytics.
unauthorized = client.get(endpoint)
assert unauthorized.status_code == 401

# Use an isolated test session, not a real administrator account.
with client.session_transaction() as session:
    session["admin"] = True

if SCENARIO == "sample":
    appointments = [
        ("Analytics Patient A", "+12025550101",
         "Doctor A", "2026-11-25", "09:00", "Booked"),
        ("Analytics Patient B", "+12025550102",
         "Doctor A", "2026-11-25", "10:00", "Cancelled"),
        ("Analytics Patient C", "+12025550103",
         "Doctor B", "2026-11-26", "09:00", "Booked"),
        ("Analytics Patient D", "+12025550104",
         "Doctor B", "2026-11-26", "11:00", "Booked"),
        ("Analytics Patient E", "+12025550105",
         "Doctor A", "2026-11-27", "09:00", "Cancelled"),
        ("Analytics Patient F", "+12025550106",
         "Doctor C", "2026-11-27", "10:00", "Booked"),
    ]

    with sqlite3.connect(EXPECTED_DB) as db:
        db.executemany(
            "INSERT INTO appointments "
            "(patient, phone, doctor, date, time, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            appointments,
        )

response = client.get(endpoint)

assert response.status_code == 200, (
    response.status_code,
    response.get_json(),
)

data = response.get_json()

assert set(data) == {"summary", "doctors", "daily", "times"}

# Analytics must not expose patient-identifying information.
serialized = json.dumps(data)

assert "patient" not in serialized.lower()
assert "phone" not in serialized.lower()
assert "+1202555" not in serialized

if SCENARIO == "empty":
    assert data["summary"] == {
        "total": 0,
        "active": 0,
        "cancelled": 0,
        "cancellation_rate": 0.0,
    }

    assert data["doctors"] == []
    assert data["daily"] == []
    assert data["times"] == []

else:
    assert data["summary"] == {
        "total": 6,
        "active": 4,
        "cancelled": 2,
        "cancellation_rate": 33.33,
    }

    assert data["doctors"] == [
        {"doctor": "Doctor A", "total": 3},
        {"doctor": "Doctor B", "total": 2},
        {"doctor": "Doctor C", "total": 1},
    ]

    assert data["daily"] == [
        {"date": "2026-11-25", "total": 2},
        {"date": "2026-11-26", "total": 2},
        {"date": "2026-11-27", "total": 2},
    ]

    assert data["times"] == [
        {"time": "09:00", "total": 3},
        {"time": "10:00", "total": 2},
        {"time": "11:00", "total": 1},
    ]

print("PASSED:", SCENARIO)
"""

    code = (
        "EXPECTED_DB = " + repr(str(db_path)) + "\n"
        + "SCENARIO = " + repr(scenario) + "\n"
        + code
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert result.returncode == 0, (
        "STDOUT:\n" + result.stdout
        + "\nSTDERR:\n" + result.stderr
    )

    assert db_path.is_file()
