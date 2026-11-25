import os
import subprocess
import sys

import pytest


ASHA = "Dr. Asha Sharma - General Medicine"
RAHUL = "Dr. Rahul Verma - Dental"
NEHA = "Dr. Neha Singh - Dermatology"


@pytest.mark.parametrize(
    "case",
    [
        "all_time",
        "empty_database",
        "active_rate",
        "average_daily",
        "inclusive_period",
        "zero_booking_days",
        "busiest_day",
        "peak_time",
        "most_booked_doctor",
        "ties",
        "doctor_filter",
        "combined_filters",
        "no_matches",
        "unauthorized",
        "backward_compatibility",
    ],
)
def test_advanced_kpis(tmp_path, case):
    db_path = tmp_path / "kpi_test.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "LIVE_MODE": "false",
        "PUBLIC_DEMO_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
        "ADMIN_PASSWORD": "KpiTestPassword2026!",
        "SECRET_KEY": "kpi-test-secret-not-production",
    })

    script = (
        f"CASE = {case!r}\n"
        f"EXPECTED_DB = {str(db_path)!r}\n"
        f"ASHA = {ASHA!r}\n"
        f"RAHUL = {RAHUL!r}\n"
        f"NEHA = {NEHA!r}\n"
    )

    script += r'''
import sqlite3
from pathlib import Path
import app

assert Path(app.DB).resolve() == Path(EXPECTED_DB).resolve()
assert app.LIVE is False
assert app.scheduler.running is False

records = [
    ("Test Patient A", "+12025550101", ASHA,
     "2026-11-25", "09:00", "Booked"),
    ("Test Patient B", "+12025550102", ASHA,
     "2026-11-25", "10:00", "Cancelled"),
    ("Test Patient C", "+12025550103", RAHUL,
     "2026-11-26", "09:00", "Booked"),
    ("Test Patient D", "+12025550104", RAHUL,
     "2026-11-26", "11:00", "Booked"),
    ("Test Patient E", "+12025550105", ASHA,
     "2026-11-27", "09:00", "Cancelled"),
    ("Test Patient F", "+12025550106", NEHA,
     "2026-11-27", "10:00", "Booked"),
]

with sqlite3.connect(EXPECTED_DB) as conn:
    assert conn.execute(
        "SELECT COUNT(*) FROM appointments"
    ).fetchone()[0] == 0

    if CASE != "empty_database":
        conn.executemany(
            "INSERT INTO appointments "
            "(patient, phone, doctor, date, time, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            records,
        )

client = app.app.test_client()

if CASE != "unauthorized":
    with client.session_transaction() as session:
        session["admin"] = True

query = {"include_kpis": "1"}

if CASE == "inclusive_period":
    query.update(
        start_date="2026-11-25",
        end_date="2026-11-25",
    )

elif CASE == "zero_booking_days":
    query.update(
        start_date="2026-11-24",
        end_date="2026-11-29",
    )

elif CASE == "doctor_filter":
    query["doctor"] = ASHA

elif CASE == "combined_filters":
    query.update(
        doctor=ASHA,
        start_date="2026-11-25",
        end_date="2026-11-26",
    )

elif CASE == "no_matches":
    query.update(
        doctor=NEHA,
        start_date="2026-11-25",
        end_date="2026-11-26",
    )

elif CASE == "backward_compatibility":
    query = {}

response = client.get(
    "/api/admin/analytics",
    query_string=query,
)

if CASE == "unauthorized":
    assert response.status_code == 401
    raise SystemExit(0)

assert response.status_code == 200, response.get_data(as_text=True)

data = response.get_json()

if CASE == "backward_compatibility":
    assert set(data) == {
        "summary", "doctors", "daily", "times"
    }
    raise SystemExit(0)

assert set(data) == {
    "summary", "doctors", "daily", "times", "kpis"
}

k = data["kpis"]

assert set(k) == {
    "active_booking_rate",
    "average_daily_appointments",
    "reporting_days",
    "period_start",
    "period_end",
    "busiest_day",
    "peak_appointment_time",
    "most_booked_doctor",
}

assert "Test Patient" not in response.get_data(as_text=True)
assert "+1202555" not in response.get_data(as_text=True)

if CASE == "all_time":
    assert data["summary"]["total"] == 6
    assert k["active_booking_rate"] == 66.67
    assert k["average_daily_appointments"] == 2.0
    assert k["reporting_days"] == 3
    assert k["period_start"] == "2026-11-25"
    assert k["period_end"] == "2026-11-27"

elif CASE == "empty_database":
    assert data["summary"]["total"] == 0
    assert k["active_booking_rate"] == 0.0
    assert k["average_daily_appointments"] == 0.0
    assert k["reporting_days"] == 0
    assert k["period_start"] is None
    assert k["period_end"] is None

    for field in (
        "busiest_day",
        "peak_appointment_time",
        "most_booked_doctor",
    ):
        assert k[field] == {
            "value": None,
            "total": 0,
            "ties": [],
        }

elif CASE == "active_rate":
    assert k["active_booking_rate"] == 66.67

elif CASE == "average_daily":
    assert k["average_daily_appointments"] == 2.0

elif CASE == "inclusive_period":
    assert k["reporting_days"] == 1
    assert k["average_daily_appointments"] == 2.0
    assert k["active_booking_rate"] == 50.0

elif CASE == "zero_booking_days":
    assert k["reporting_days"] == 6
    assert k["average_daily_appointments"] == 1.0

elif CASE == "busiest_day":
    assert k["busiest_day"]["value"] == "2026-11-25"
    assert k["busiest_day"]["total"] == 2

elif CASE == "peak_time":
    assert k["peak_appointment_time"] == {
        "value": "09:00",
        "total": 3,
        "ties": ["09:00"],
    }

elif CASE == "most_booked_doctor":
    assert k["most_booked_doctor"] == {
        "value": ASHA,
        "total": 3,
        "ties": [ASHA],
    }

elif CASE == "ties":
    assert k["busiest_day"]["ties"] == [
        "2026-11-25",
        "2026-11-26",
        "2026-11-27",
    ]

elif CASE == "doctor_filter":
    assert data["summary"]["total"] == 3
    assert k["active_booking_rate"] == 33.33
    assert k["average_daily_appointments"] == 1.0
    assert k["reporting_days"] == 3
    assert k["most_booked_doctor"]["value"] == ASHA

elif CASE == "combined_filters":
    assert data["summary"]["total"] == 2
    assert k["active_booking_rate"] == 50.0
    assert k["reporting_days"] == 2
    assert k["average_daily_appointments"] == 1.0
    assert k["peak_appointment_time"]["ties"] == [
        "09:00", "10:00"
    ]

elif CASE == "no_matches":
    assert data["summary"]["total"] == 0
    assert k["reporting_days"] == 2
    assert k["active_booking_rate"] == 0.0
    assert k["average_daily_appointments"] == 0.0
    assert k["most_booked_doctor"]["value"] is None

with sqlite3.connect(EXPECTED_DB) as conn:
    stored = conn.execute(
        "SELECT patient, phone, doctor, date, time, status "
        "FROM appointments ORDER BY id"
    ).fetchall()

    assert stored == (
        [] if CASE == "empty_database" else records
    )
'''

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert result.returncode == 0, (
        result.stdout + "\n" + result.stderr
    )

    assert db_path.exists()
