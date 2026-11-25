import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "query, expected_status, expected_ids, authenticated",
    [
        pytest.param(
            {}, 200, [0, 1, 2, 3, 4, 5], True,
            id="all-time"
        ),
        pytest.param(
            {"start_date": "2026-11-26"},
            200, [2, 3, 4, 5], True,
            id="start-date-only"
        ),
        pytest.param(
            {"end_date": "2026-11-26"},
            200, [0, 1, 2, 3], True,
            id="end-date-only"
        ),
        pytest.param(
            {
                "start_date": "2026-11-25",
                "end_date": "2026-11-26",
            },
            200, [0, 1, 2, 3], True,
            id="inclusive-date-range"
        ),
        pytest.param(
            {
                "start_date": "2026-11-26",
                "end_date": "2026-11-26",
            },
            200, [2, 3], True,
            id="single-day"
        ),
        pytest.param(
            {
                "start_date": "2026-11-27",
                "end_date": "2026-11-27",
            },
            200, [4, 5], True,
            id="single-day-with-cancellation"
        ),
        pytest.param(
            {"start_date": "25-11-2026"},
            400, [], True,
            id="invalid-date-format"
        ),
        pytest.param(
            {"end_date": "2026-02-30"},
            400, [], True,
            id="invalid-calendar-date"
        ),
        pytest.param(
            {
                "start_date": "2026-11-27",
                "end_date": "2026-11-25",
            },
            400, [], True,
            id="reversed-date-range"
        ),
        pytest.param(
            {"start_date": "2026-11-25' OR 1=1 --"},
            400, [], True,
            id="sql-injection-attempt"
        ),
        pytest.param(
            {
                "start_date": "2026-12-01",
                "end_date": "2026-12-31",
            },
            200, [], True,
            id="no-matching-appointments"
        ),
        pytest.param(
            {"start_date": "2026-11-25"},
            401, [], False,
            id="unauthorized-access"
        ),
        pytest.param(
            {"start_date": ""},
            400, [], True,
            id="empty-start-date"
        ),
        pytest.param(
            {"end_date": ""},
            400, [], True,
            id="empty-end-date"
        ),
        pytest.param(
            {
                "start_date": "2024-02-29",
                "end_date": "2024-02-29",
            },
            200, [], True,
            id="valid-leap-year-date"
        ),
    ],
)
def test_admin_analytics_date_filters(
    tmp_path,
    query,
    expected_status,
    expected_ids,
    authenticated,
):
    """Verify date filters using isolated fictional appointment data."""

    db_path = tmp_path / "analytics_date_filters.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "LIVE_MODE": "false",
        "PUBLIC_DEMO_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
        "ADMIN_PASSWORD": "DateFilterTestPassword2026!",
        "SECRET_KEY": "date-filter-test-secret-not-for-production",
    })

    code = r"""
import json
import sqlite3
from collections import Counter

import app

assert str(app.DB) == EXPECTED_DB
assert app.LIVE is False
assert app.scheduler.running is False

appointments = [
    ("Filter Patient A", "+12025550101",
     "Doctor A", "2026-11-25", "09:00", "Booked"),

    ("Filter Patient B", "+12025550102",
     "Doctor A", "2026-11-25", "10:00", "Cancelled"),

    ("Filter Patient C", "+12025550103",
     "Doctor B", "2026-11-26", "09:00", "Booked"),

    ("Filter Patient D", "+12025550104",
     "Doctor B", "2026-11-26", "11:00", "Booked"),

    ("Filter Patient E", "+12025550105",
     "Doctor A", "2026-11-27", "09:00", "Cancelled"),

    ("Filter Patient F", "+12025550106",
     "Doctor C", "2026-11-27", "10:00", "Booked"),
]

with sqlite3.connect(EXPECTED_DB) as db:
    db.executemany(
        "INSERT INTO appointments "
        "(patient, phone, doctor, date, time, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        appointments,
    )

client = app.app.test_client()

if AUTHENTICATED:
    with client.session_transaction() as session:
        session["admin"] = True

response = client.get(
    "/api/admin/analytics",
    query_string=QUERY,
)

assert response.status_code == EXPECTED_STATUS, (
    response.status_code,
    response.get_json(),
)

data = response.get_json()

if EXPECTED_STATUS != 200:
    assert "error" in data

else:
    assert set(data) == {
        "summary", "doctors", "daily", "times"
    }

    selected = [
        appointments[i] for i in EXPECTED_IDS
    ]

    total = len(selected)

    active = sum(
        row[5] == "Booked" for row in selected
    )

    cancelled = sum(
        row[5] == "Cancelled" for row in selected
    )

    rate = (
        round(cancelled / total * 100, 2)
        if total else 0.0
    )

    assert data["summary"] == {
        "total": total,
        "active": active,
        "cancelled": cancelled,
        "cancellation_rate": rate,
    }

    doctor_counts = Counter(
        row[2] for row in selected
    )

    date_counts = Counter(
        row[3] for row in selected
    )

    time_counts = Counter(
        row[4] for row in selected
    )

    expected_doctors = [
        {"doctor": name, "total": count}
        for name, count in sorted(
            doctor_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    expected_daily = [
        {"date": name, "total": count}
        for name, count in sorted(date_counts.items())
    ]

    expected_times = [
        {"time": name, "total": count}
        for name, count in sorted(
            time_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    assert data["doctors"] == expected_doctors
    assert data["daily"] == expected_daily
    assert data["times"] == expected_times

    # Every chart must match the filtered total.
    for key in ("doctors", "daily", "times"):
        assert sum(
            row["total"] for row in data[key]
        ) == total

    # Verify that analytics exposes no patient details.
    serialized = json.dumps(data).lower()

    assert "patient" not in serialized
    assert "phone" not in serialized
    assert "+1202555" not in serialized

# Confirm that filtering and invalid requests never modify records.
with sqlite3.connect(EXPECTED_DB) as db:
    stored = db.execute(
        "SELECT patient, phone, doctor, date, time, status "
        "FROM appointments ORDER BY id"
    ).fetchall()

assert stored == appointments

print("PASSED:", QUERY, EXPECTED_STATUS)
"""

    code = (
        "EXPECTED_DB = " + repr(str(db_path)) + "\n"
        + "QUERY = " + repr(query) + "\n"
        + "EXPECTED_STATUS = " + repr(expected_status) + "\n"
        + "EXPECTED_IDS = " + repr(expected_ids) + "\n"
        + "AUTHENTICATED = " + repr(authenticated) + "\n"
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