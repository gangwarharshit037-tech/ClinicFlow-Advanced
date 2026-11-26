import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("case", [
    "backward_compatibility",
    "all_time",
    "start_only",
    "end_only",
    "equal_length",
    "positive_growth",
    "negative_growth",
    "zero_growth",
    "zero_previous",
    "zero_current",
    "both_empty",
    "active_rate",
    "cancellation_rate",
    "average_daily",
    "doctor_filter",
    "single_day",
    "invalid_range",
    "date_underflow",
    "unauthorized",
    "privacy_integrity",
])
def test_period_comparison(tmp_path, case):
    db_path = tmp_path / "comparison_test.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "LIVE_MODE": "false",
        "PUBLIC_DEMO_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
        "ADMIN_PASSWORD": "ComparisonTestPassword2026!",
        "SECRET_KEY": "comparison-test-not-production",
    })

    script = (
        f"CASE = {case!r}\n"
        f"EXPECTED_DB = {str(db_path)!r}\n"
    )

    script += r'''
import sqlite3
from pathlib import Path
import app

assert Path(app.DB).resolve() == Path(EXPECTED_DB).resolve()
assert app.LIVE is False
assert app.scheduler.running is False

ASHA, RAHUL, NEHA = app.DOCTORS

records = [
    ("Test Patient 1", "+12025550101", ASHA,
     "2026-11-22", "09:00", "Booked"),

    ("Test Patient 2", "+12025550102", ASHA,
     "2026-11-23", "10:00", "Cancelled"),

    ("Test Patient 3", "+12025550103", RAHUL,
     "2026-11-24", "09:00", "Booked"),

    ("Test Patient 4", "+12025550104", RAHUL,
     "2026-11-24", "10:00", "Cancelled"),

    ("Test Patient 5", "+12025550105", ASHA,
     "2026-11-25", "09:00", "Booked"),

    ("Test Patient 6", "+12025550106", ASHA,
     "2026-11-25", "10:00", "Cancelled"),

    ("Test Patient 7", "+12025550107", RAHUL,
     "2026-11-26", "09:00", "Booked"),

    ("Test Patient 8", "+12025550108", RAHUL,
     "2026-11-26", "11:00", "Booked"),

    ("Test Patient 9", "+12025550109", ASHA,
     "2026-11-27", "09:00", "Cancelled"),

    ("Test Patient 10", "+12025550110", NEHA,
     "2026-11-27", "10:00", "Booked"),
]

if CASE == "negative_growth":
    records = records[:6]

elif CASE == "zero_growth":
    records = records[:8]

elif CASE == "zero_previous":
    records = records[4:]

elif CASE == "zero_current":
    records = records[:4]

elif CASE == "both_empty":
    records = []

with sqlite3.connect(EXPECTED_DB) as conn:
    assert conn.execute(
        "SELECT COUNT(*) FROM appointments"
    ).fetchone()[0] == 0

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

query = {
    "include_comparison": "1",
    "include_kpis": "1",
    "start_date": "2026-11-25",
    "end_date": "2026-11-27",
}

if CASE == "backward_compatibility":
    query.pop("include_comparison")

elif CASE == "all_time":
    query.pop("start_date")
    query.pop("end_date")

elif CASE == "start_only":
    query.pop("end_date")

elif CASE == "end_only":
    query.pop("start_date")

elif CASE == "doctor_filter":
    query["doctor"] = ASHA

elif CASE == "single_day":
    query["end_date"] = "2026-11-25"

elif CASE == "invalid_range":
    query["start_date"] = "2026-11-28"

elif CASE == "date_underflow":
    query["start_date"] = "0001-01-01"
    query["end_date"] = "0001-01-01"

response = client.get(
    "/api/admin/analytics",
    query_string=query,
)

if CASE == "unauthorized":
    assert response.status_code == 401
    raise SystemExit(0)

if CASE in ("invalid_range", "date_underflow"):
    assert response.status_code == 400
    assert "error" in response.get_json()
    raise SystemExit(0)

assert response.status_code == 200, response.get_data(as_text=True)

data = response.get_json()

assert "Test Patient" not in response.get_data(as_text=True)
assert "+1202555" not in response.get_data(as_text=True)

if CASE == "backward_compatibility":
    assert set(data) == {
        "summary", "doctors", "daily", "times", "kpis"
    }
    assert data["summary"]["total"] == 6
    raise SystemExit(0)

assert set(data) == {
    "summary", "doctors", "daily",
    "times", "kpis", "comparison"
}

comparison = data["comparison"]

if CASE in ("all_time", "start_only", "end_only"):
    assert comparison == {
        "available": False,
        "reason": "Select both start and end dates."
    }
    raise SystemExit(0)

assert comparison["available"] is True

current = comparison["current"]
previous = comparison["previous"]
changes = comparison["changes"]

assert current["total"] == data["summary"]["total"]
assert current["active"] == data["summary"]["active"]
assert current["cancelled"] == data["summary"]["cancelled"]

if CASE != "single_day":
    assert comparison["reporting_days"] == 3
    assert current["start_date"] == "2026-11-25"
    assert current["end_date"] == "2026-11-27"
    assert previous["start_date"] == "2026-11-22"
    assert previous["end_date"] == "2026-11-24"

if CASE == "equal_length":
    assert current["total"] == 6
    assert previous["total"] == 4

elif CASE == "positive_growth":
    assert changes["total_difference"] == 2
    assert changes["total_growth_percentage"] == 50.0
    assert changes["active_difference"] == 2
    assert changes["cancelled_difference"] == 0

elif CASE == "negative_growth":
    assert current["total"] == 2
    assert previous["total"] == 4
    assert changes["total_difference"] == -2
    assert changes["total_growth_percentage"] == -50.0

elif CASE == "zero_growth":
    assert current["total"] == 4
    assert previous["total"] == 4
    assert changes["total_growth_percentage"] == 0.0

elif CASE == "zero_previous":
    assert previous["total"] == 0
    assert current["total"] == 6
    assert changes["total_growth_percentage"] is None
    assert changes["average_daily_growth_percentage"] is None
    assert previous["active_booking_rate"] is None
    assert previous["cancellation_rate"] is None
    assert changes["active_rate_percentage_points"] is None
    assert changes["cancellation_rate_percentage_points"] is None

elif CASE == "zero_current":
    assert current["total"] == 0
    assert previous["total"] == 4
    assert changes["total_growth_percentage"] == -100.0
    assert current["active_booking_rate"] is None
    assert current["cancellation_rate"] is None
    assert changes["active_rate_percentage_points"] is None
    assert changes["cancellation_rate_percentage_points"] is None

elif CASE == "both_empty":
    assert current["total"] == 0
    assert previous["total"] == 0
    assert changes["total_difference"] == 0
    assert changes["total_growth_percentage"] is None
    assert current["average_daily_appointments"] == 0.0
    assert previous["average_daily_appointments"] == 0.0

elif CASE == "active_rate":
    assert current["active_booking_rate"] == 66.67
    assert previous["active_booking_rate"] == 50.0
    assert changes["active_rate_percentage_points"] == 16.67

elif CASE == "cancellation_rate":
    assert current["cancellation_rate"] == 33.33
    assert previous["cancellation_rate"] == 50.0
    assert changes["cancellation_rate_percentage_points"] == -16.67

elif CASE == "average_daily":
    assert current["average_daily_appointments"] == 2.0
    assert previous["average_daily_appointments"] == 1.33
    assert changes["average_daily_growth_percentage"] == 50.0

elif CASE == "doctor_filter":
    assert current["total"] == 3
    assert previous["total"] == 2
    assert current["active"] == 1
    assert previous["active"] == 1
    assert changes["total_growth_percentage"] == 50.0
    assert changes["active_rate_percentage_points"] == -16.67
    assert changes["cancellation_rate_percentage_points"] == 16.67

elif CASE == "single_day":
    assert comparison["reporting_days"] == 1
    assert current["start_date"] == "2026-11-25"
    assert current["end_date"] == "2026-11-25"
    assert previous["start_date"] == "2026-11-24"
    assert previous["end_date"] == "2026-11-24"
    assert current["total"] == 2
    assert previous["total"] == 2
    assert changes["total_growth_percentage"] == 0.0

elif CASE == "privacy_integrity":
    assert current["total"] == 6
    assert previous["total"] == 4
    assert "patient" not in comparison
    assert "phone" not in comparison

with sqlite3.connect(EXPECTED_DB) as conn:
    stored = conn.execute(
        "SELECT patient, phone, doctor, date, time, status "
        "FROM appointments ORDER BY id"
    ).fetchall()

    assert stored == records
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
