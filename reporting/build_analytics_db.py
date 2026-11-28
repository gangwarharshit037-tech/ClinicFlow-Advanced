import sqlite3
import tempfile

from pathlib import Path
from datetime import date, timedelta
from contextlib import closing

import pandas as pd

from reporting.data_cleaning import OUTPUT
from reporting.data_validation import (
    DOCTOR_DEPARTMENTS,
    validate_dataset,
)


ROOT = Path(__file__).resolve().parents[1]

SCHEMA = ROOT / "reporting" / "sql" / "schema.sql"

DATABASE = (
    ROOT / "data" / "analytics"
    / "clinicflow_analytics.db"
)

EXPECTED_COUNTS = {
    "dim_doctor": 3,
    "dim_date": 396,
    "dim_time": 18,
    "fact_appointments": 10000,
}


def build_doctor_dimension():
    return [
        (number, doctor, department)
        for number, (doctor, department)
        in enumerate(
            sorted(DOCTOR_DEPARTMENTS.items()),
            start=1
        )
    ]


def build_date_dimension():
    start = date(2024, 12, 1)
    end = date(2025, 12, 31)

    rows = []

    current = start

    while current <= end:
        rows.append((
            current.isoformat(),
            current.year,
            current.month,
            current.strftime("%B"),
            f"Q{(current.month - 1) // 3 + 1}",
            current.strftime("%A"),
            int(current.weekday() >= 5),
        ))

        current += timedelta(days=1)

    return rows


def build_time_dimension():
    rows = []

    for hour in range(9, 18):
        for minute in (0, 30):

            if hour < 12:
                slot = "Morning"
            elif hour < 15:
                slot = "Afternoon"
            else:
                slot = "Evening"

            rows.append((
                f"{hour:02d}:{minute:02d}",
                hour,
                minute,
                slot,
            ))

    return rows


def verify_database(conn):
    counts = {}

    for table, expected in EXPECTED_COUNTS.items():
        actual = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        if actual != expected:
            raise ValueError(
                f"{table}: expected {expected}, "
                f"found {actual}"
            )

        counts[table] = actual

    statuses = dict(conn.execute("""
        SELECT status, COUNT(*)
        FROM fact_appointments
        GROUP BY status
    """).fetchall())

    if statuses != {
        "Booked": 8000,
        "Cancelled": 2000
    }:
        raise ValueError("Invalid status distribution.")

    violations = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if violations:
        raise ValueError("Foreign key violations detected.")

    integrity = conn.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if integrity != "ok":
        raise ValueError("Database integrity check failed.")

    return counts


def build_database(source=OUTPUT, database=DATABASE):
    source = Path(source)
    database = Path(database)

    df = pd.read_csv(source)

    results = validate_dataset(df)

    failed = [
        name for name, passed in results.items()
        if not passed
    ]

    if failed:
        raise ValueError(
            "Dataset validation failed: "
            + ", ".join(failed)
        )

    doctors = build_doctor_dimension()
    dates = build_date_dimension()
    times = build_time_dimension()

    doctor_lookup = {
        name: doctor_id
        for doctor_id, name, department in doctors
    }

    facts = [
        (
            row.Appointment_ID,
            doctor_lookup[row.Doctor],
            row.Appointment_Date,
            row.Booking_Date,
            row.Appointment_Time,
            row.Status,
            int(row.Lead_Time_Days),
        )
        for row in df.itertuples(index=False)
    ]

    database.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    schema = SCHEMA.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(
        dir=database.parent
    ) as temp_dir:

        temporary_db = (
            Path(temp_dir) / "analytics_build.db"
        )

        with closing(
            sqlite3.connect(temporary_db)
        ) as conn:

            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(schema)

            with conn:
                conn.executemany("""
                    INSERT INTO dim_doctor
                    VALUES (?, ?, ?)
                """, doctors)

                conn.executemany("""
                    INSERT INTO dim_date
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, dates)

                conn.executemany("""
                    INSERT INTO dim_time
                    VALUES (?, ?, ?, ?)
                """, times)

                conn.executemany("""
                    INSERT INTO fact_appointments
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, facts)

                counts = verify_database(conn)

            for filename in ("indexes.sql", "views.sql"):
                sql_path = SCHEMA.parent / filename

                conn.executescript(
                    sql_path.read_text(encoding="utf-8")
                )

            conn.execute("ANALYZE")

            conn.commit()

            counts = verify_database(conn)

        temporary_db.replace(database)

    return counts


def main():
    print("=" * 60)
    print("CLINICFLOW ANALYTICAL DATABASE BUILDER")
    print("=" * 60)

    counts = build_database()

    print("\nTABLE RECORD COUNTS")

    for table, count in counts.items():
        print(f"{table}: {count:,}")

    print("\nTotal records:", sum(counts.values()))
    print("Foreign key check: PASSED")
    print("Database integrity: PASSED")

    print("\nDatabase:", DATABASE)
    print("Database size:", DATABASE.stat().st_size, "bytes")

    print("\nSUCCESS: Analytical database created.")


if __name__ == "__main__":
    main()
