import os
import subprocess
import sys

import pytest

ASHA = "Dr. Asha Sharma - General Medicine"
RAHUL = "Dr. Rahul Verma - Dental"
NEHA = "Dr. Neha Singh - Dermatology"

@pytest.mark.parametrize(
    "query,status,ids,auth",
    [
        pytest.param({}, 200, [0,1,2,3,4,5], True, id="all-doctors"),
        pytest.param({"doctor": ASHA}, 200, [0,1,4], True, id="doctor-asha"),
        pytest.param({"doctor": RAHUL}, 200, [2,3], True, id="doctor-rahul"),
        pytest.param({"doctor": NEHA}, 200, [5], True, id="doctor-neha"),
        pytest.param(
            {"doctor": ASHA, "start_date": "2026-11-25",
             "end_date": "2026-11-26"},
            200, [0,1], True, id="combined-date-range"
        ),
        pytest.param(
            {"doctor": ASHA, "start_date": "2026-11-26"},
            200, [4], True, id="doctor-start-date"
        ),
        pytest.param(
            {"doctor": ASHA, "end_date": "2026-11-26"},
            200, [0,1], True, id="doctor-end-date"
        ),
        pytest.param(
            {"doctor": RAHUL, "start_date": "2026-11-26",
             "end_date": "2026-11-26"},
            200, [2,3], True, id="doctor-single-day"
        ),
        pytest.param(
            {"doctor": NEHA, "start_date": "2026-11-25",
             "end_date": "2026-11-26"},
            200, [], True, id="no-matching-appointments"
        ),
        pytest.param(
            {"doctor": "Unknown Doctor"},
            400, [], True, id="unknown-doctor"
        ),
        pytest.param(
            {"doctor": ""},
            400, [], True, id="empty-doctor"
        ),
        pytest.param(
            {"doctor": "' OR 1=1 --"},
            400, [], True, id="sql-injection-attempt"
        ),
        pytest.param(
            {"doctor": ASHA, "start_date": "2026-02-30"},
            400, [], True, id="invalid-date"
        ),
        pytest.param(
            {"doctor": ASHA, "start_date": "2026-11-27",
             "end_date": "2026-11-25"},
            400, [], True, id="reversed-date-range"
        ),
        pytest.param(
            {"doctor": ASHA},
            401, [], False, id="unauthorized-access"
        ),
    ],
)
def test_admin_analytics_doctor_filters(
    tmp_path, query, status, ids, auth
):
    db_path = tmp_path / "doctor_filters.db"

    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(db_path),
        "LIVE_MODE": "false",
        "PUBLIC_DEMO_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
        "ADMIN_PASSWORD": "DoctorFilterTestPassword2026!",
        "SECRET_KEY": "doctor-filter-test-secret-not-production",
    })

    script = r"""
import json
import sqlite3
from pathlib import Path
from collections import Counter

import app

assert Path(app.DB).resolve() == Path(DB).resolve()
assert app.LIVE is False
assert app.scheduler.running is False

asha = "Dr. Asha Sharma - General Medicine"
rahul = "Dr. Rahul Verma - Dental"
neha = "Dr. Neha Singh - Dermatology"

assert all(d in app.DOCTORS for d in (asha, rahul, neha))

rows = [
    ("Test Patient A", "+12025550101", asha,
     "2026-11-25", "09:00", "Booked"),
    ("Test Patient B", "+12025550102", asha,
     "2026-11-25", "10:00", "Cancelled"),
    ("Test Patient C", "+12025550103", rahul,
     "2026-11-26", "09:00", "Booked"),
    ("Test Patient D", "+12025550104", rahul,
     "2026-11-26", "11:00", "Booked"),
    ("Test Patient E", "+12025550105", asha,
     "2026-11-27", "09:00", "Cancelled"),
    ("Test Patient F", "+12025550106", neha,
     "2026-11-27", "10:00", "Booked"),
]

with sqlite3.connect(DB) as db:
    db.executemany(
        "INSERT INTO appointments "
        "(patient, phone, doctor, date, time, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows
    )

client = app.app.test_client()

if AUTH:
    with client.session_transaction() as session:
        session["admin"] = True

response = client.get(
    "/api/admin/analytics",
    query_string=QUERY
)

assert response.status_code == STATUS, (
    response.status_code, response.get_json()
)

data = response.get_json()

if STATUS != 200:
    assert "error" in data
else:
    assert set(data) == {
        "summary", "doctors", "daily", "times"
    }

    selected = [rows[i] for i in IDS]
    total = len(selected)
    active = sum(r[5] == "Booked" for r in selected)
    cancelled = sum(r[5] == "Cancelled" for r in selected)

    rate = round(cancelled / total * 100, 2) if total else 0.0

    assert data["summary"] == {
        "total": total,
        "active": active,
        "cancelled": cancelled,
        "cancellation_rate": rate
    }

    for key, field, index in [
        ("doctors", "doctor", 2),
        ("daily", "date", 3),
        ("times", "time", 4),
    ]:
        counts = Counter(r[index] for r in selected)

        if key == "daily":
            ordered = sorted(counts.items())
        else:
            ordered = sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0])
            )

        expected = [
            {field: name, "total": count}
            for name, count in ordered
        ]

        assert data[key] == expected
        assert sum(r["total"] for r in data[key]) == total

    serialized = json.dumps(data).lower()
    assert "patient" not in serialized
    assert "phone" not in serialized
    assert "+1202555" not in serialized

with sqlite3.connect(DB) as db:
    stored = db.execute(
        "SELECT patient, phone, doctor, date, time, status "
        "FROM appointments ORDER BY id"
    ).fetchall()

assert stored == rows
"""

    script = (
        "DB = " + repr(str(db_path)) + "\n"
        + "QUERY = " + repr(query) + "\n"
        + "STATUS = " + repr(status) + "\n"
        + "IDS = " + repr(ids) + "\n"
        + "AUTH = " + repr(auth) + "\n"
        + script
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=45
    )

    assert result.returncode == 0, (
        "STDOUT:\n" + result.stdout
        + "\nSTDERR:\n" + result.stderr
    )

    assert db_path.is_file()
