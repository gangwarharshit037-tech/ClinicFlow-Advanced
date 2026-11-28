import hashlib
import sqlite3

from contextlib import closing

import pandas as pd
import pytest

from reporting.data_cleaning import OUTPUT
from reporting.build_analytics_db import build_database
from reporting.business_kpis import run_business_analysis
from reporting.advanced_sql import run_advanced_analysis
from reporting.export_sql_reports import (
    export_sql_reports,
    safe_text,
    prepare_export,
)


@pytest.fixture(scope="module")
def analytics_db(tmp_path_factory):

    folder = tmp_path_factory.mktemp("analytics")

    database = folder / "test_analytics.db"

    build_database(
        source=OUTPUT,
        database=database
    )

    return database


@pytest.fixture
def conn(analytics_db):

    uri = analytics_db.resolve().as_uri() + "?mode=ro"

    with closing(
        sqlite3.connect(uri, uri=True)
    ) as connection:

        connection.execute("PRAGMA foreign_keys = ON")

        yield connection


@pytest.fixture(scope="module")
def business(analytics_db):

    return run_business_analysis(analytics_db)


@pytest.fixture(scope="module")
def advanced(analytics_db):

    return run_advanced_analysis(analytics_db)


@pytest.fixture(scope="module")
def exports(analytics_db, tmp_path_factory):

    folder = tmp_path_factory.mktemp("sql_exports")

    manifest = export_sql_reports(
        database=analytics_db,
        output_dir=folder
    )

    return folder, manifest


# DATABASE STRUCTURE: 5 TESTS

def test_database_tables(conn):

    tables = {
        row[0] for row in conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
        """)
    }

    assert tables == {
        "dim_doctor",
        "dim_date",
        "dim_time",
        "fact_appointments",
    }


def test_dimension_counts(conn):

    expected = {
        "dim_doctor": 3,
        "dim_date": 396,
        "dim_time": 18,
    }

    for table, count in expected.items():

        assert conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0] == count


def test_fact_record_count(conn):

    assert conn.execute("""
        SELECT COUNT(*)
        FROM fact_appointments
    """).fetchone()[0] == 10000


def test_database_integrity(conn):

    assert conn.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0] == "ok"

    assert conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall() == []


def test_database_indexes(conn):

    indexes = {
        row[0] for row in conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
            AND name NOT LIKE 'sqlite_%'
        """)
    }

    assert indexes == {
        "uq_fact_active_slot",
        "idx_fact_appointment_date",
        "idx_fact_doctor_date",
        "idx_fact_status_date",
        "idx_fact_booking_date",
        "idx_fact_appointment_time",
    }


# DATABASE CONSTRAINTS: 5 TESTS

@pytest.mark.parametrize(
    "column,value",
    [
        ("status", "Invalid"),
        ("lead_time_days", -1),
        ("lead_time_days", 31),
        ("doctor_id", 999),
    ]
)
def test_invalid_fact_rejected(
    analytics_db, tmp_path, column, value
):

    database = tmp_path / "constraints.db"

    database.write_bytes(
        analytics_db.read_bytes()
    )

    with closing(sqlite3.connect(database)) as c:

        c.execute("PRAGMA foreign_keys = ON")

        with pytest.raises(sqlite3.IntegrityError):

            c.execute(f"""
                UPDATE fact_appointments
                SET {column} = ?
                WHERE appointment_id = (
                    SELECT appointment_id
                    FROM fact_appointments
                    LIMIT 1
                )
            """, (value,))

        c.rollback()


def test_duplicate_booked_slot_rejected(
    analytics_db, tmp_path
):

    database = tmp_path / "duplicate.db"

    database.write_bytes(
        analytics_db.read_bytes()
    )

    with closing(sqlite3.connect(database)) as c:

        c.execute("PRAGMA foreign_keys = ON")

        with pytest.raises(sqlite3.IntegrityError):

            c.execute("""
                INSERT INTO fact_appointments
                SELECT
                    'APT99999',
                    doctor_id,
                    appointment_date,
                    booking_date,
                    appointment_time,
                    status,
                    lead_time_days
                FROM fact_appointments
                WHERE status = 'Booked'
                LIMIT 1
            """)

        c.rollback()


# ETL PIPELINE: 3 TESTS

def test_etl_repeatability(tmp_path):

    database = tmp_path / "repeat.db"

    first = build_database(
        source=OUTPUT,
        database=database
    )

    second = build_database(
        source=OUTPUT,
        database=database
    )

    assert first == second

    assert second["fact_appointments"] == 10000


def test_etl_invalid_source_preserves_database(
    analytics_db, tmp_path
):

    database = tmp_path / "preserved.db"

    database.write_bytes(
        analytics_db.read_bytes()
    )

    before = hashlib.sha256(
        database.read_bytes()
    ).hexdigest()

    df = pd.read_csv(OUTPUT)

    df.loc[0, "Status"] = "Invalid"

    invalid = tmp_path / "invalid.csv"

    df.to_csv(invalid, index=False)

    with pytest.raises(ValueError):

        build_database(
            source=invalid,
            database=database
        )

    after = hashlib.sha256(
        database.read_bytes()
    ).hexdigest()

    assert before == after


def test_etl_missing_source(tmp_path):

    database = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError):

        build_database(
            source=tmp_path / "missing.csv",
            database=database
        )

    assert not database.exists()


# ANALYTICAL VIEWS: 6 TESTS

@pytest.mark.parametrize(
    "view,count",
    [
        ("vw_appointments", 10000),
        ("vw_daily_summary", 365),
        ("vw_monthly_summary", 12),
        ("vw_doctor_summary", 3),
        ("vw_time_summary", 18),
        ("vw_lead_time_summary", 5),
    ]
)
def test_analytical_views(conn, view, count):

    assert conn.execute(
        f"SELECT COUNT(*) FROM {view}"
    ).fetchone()[0] == count

    if view != "vw_appointments":

        totals = conn.execute(f"""
            SELECT
                SUM(total_appointments),
                SUM(booked),
                SUM(cancelled)
            FROM {view}
        """).fetchone()

        assert totals == (10000, 8000, 2000)


# BUSINESS KPIS: 4 TESTS

def test_business_report_count(business):

    assert len(business) == 10


def test_executive_kpis(business):

    row = business["executive_kpis"].iloc[0]

    expected = {
        "total_appointments": 10000,
        "booked": 8000,
        "cancelled": 2000,
        "booked_rate": 80.0,
        "cancellation_rate": 20.0,
        "total_doctors": 3,
        "avg_lead_time_days": 14.96,
        "avg_daily_appointments": 27.40,
    }

    for column, value in expected.items():

        assert row[column] == value


def test_business_summary_reconciliation(business):

    names = [
        "doctor_performance",
        "monthly_performance",
        "quarterly_performance",
        "peak_appointment_hours",
        "weekday_weekend_analysis",
        "lead_time_analysis",
        "time_slot_analysis",
    ]

    for name in names:

        df = business[name]

        assert df["total_appointments"].sum() == 10000
        assert df["booked"].sum() == 8000
        assert df["cancelled"].sum() == 2000

        assert (
            df["booked"] + df["cancelled"]
            == df["total_appointments"]
        ).all()


def test_weekday_weekend_calendar(business):

    df = business["weekday_weekend_analysis"]

    counts = dict(zip(
        df["day_type"],
        df["calendar_days"]
    ))

    assert counts == {
        "Weekday": 261,
        "Weekend": 104,
    }


# ADVANCED SQL: 6 TESTS

def test_monthly_growth(advanced):

    df = advanced["monthly_growth"]

    assert len(df) == 12

    assert pd.isna(
        df.iloc[0]["growth_percentage"]
    )

    assert df["growth_percentage"].max() == 6.24

    assert df["growth_percentage"].min() == -5.76


def test_cumulative_appointments(advanced):

    df = advanced["cumulative_appointments"]

    assert df.iloc[-1]["cumulative_appointments"] == 10000

    assert df.iloc[-1]["cumulative_booked"] == 8000

    assert df.iloc[-1]["cumulative_cancelled"] == 2000

    assert df[
        "cumulative_appointments"
    ].is_monotonic_increasing


def test_rolling_average(advanced):

    df = advanced["rolling_seven_day_average"]

    assert len(df) == 365

    actual = df["rolling_7_day_average"]

    expected = df[
        "total_appointments"
    ].rolling(7).mean()

    assert actual.iloc[:6].isna().all()

    assert actual.iloc[6:].notna().all()

    assert (
        expected.iloc[6:] - actual.iloc[6:]
    ).abs().le(0.005001).all()


def test_department_contribution(advanced):

    df = advanced["department_contribution"]

    assert len(df) == 3

    assert df["total_appointments"].sum() == 10000

    assert df[
        "contribution_percentage"
    ].sum() == pytest.approx(100.0, abs=0.02)


def test_monthly_doctor_rankings(advanced):

    df = advanced["monthly_doctor_rankings"]

    assert len(df) == 36

    assert df["total_appointments"].sum() == 10000

    assert df.groupby(
        ["year", "month_number"]
    )["monthly_rank"].min().eq(1).all()

    assert df.groupby(
        ["year", "month_number"]
    )["monthly_position"].nunique().eq(3).all()


def test_department_monthly_growth(advanced):

    df = advanced["department_monthly_growth"]

    assert len(df) == 36

    assert df["total_appointments"].sum() == 10000

    assert df["growth_percentage"].isna().sum() == 3


# CSV EXPORTS: 6 TESTS

def test_export_manifest(exports):

    folder, manifest = exports

    assert len(manifest) == 16

    assert manifest["filename"].is_unique

    assert manifest["rows"].sum() == 534

    assert len(list(folder.glob("*.csv"))) == 17

    assert (folder / "report_manifest.csv").is_file()


def test_export_checksums(exports):

    folder, manifest = exports

    for row in manifest.itertuples(index=False):

        path = folder / row.filename

        assert path.stat().st_size == row.size_bytes

        assert hashlib.sha256(
            path.read_bytes()
        ).hexdigest() == row.sha256


def test_export_csv_shapes(exports):

    folder, manifest = exports

    for row in manifest.itertuples(index=False):

        df = pd.read_csv(
            folder / row.filename,
            encoding="utf-8-sig"
        )

        assert df.shape == (
            row.rows, row.columns
        )


def test_export_missing_values(exports):

    folder, manifest = exports

    df = pd.read_csv(
        folder / "rolling_seven_day_average.csv"
    )

    assert df[
        "rolling_7_day_average"
    ].iloc[:6].isna().all()

    assert df[
        "rolling_7_day_average"
    ].iloc[6:].notna().all()


def test_csv_formula_safety():

    dangerous = [
        "=1+1",
        "+SUM(A1:A2)",
        "-1+2",
        "@example",
        "  =1+1",
        "\tformula",
        "\rformula",
        "\nformula",
    ]

    for value in dangerous:

        assert safe_text(value) == "'" + value

    assert safe_text(-5.76) == -5.76

    assert safe_text("Dermatology") == "Dermatology"


def test_export_does_not_modify_input():

    original = pd.DataFrame({
        "text": ["=1+1", "Dental"],
        "number": [-5.76, 10.0],
    })

    before = original.copy(deep=True)

    prepared = prepare_export(original)

    pd.testing.assert_frame_equal(
        original, before
    )

    assert prepared.loc[0, "text"] == "'=1+1"

    assert prepared.loc[0, "number"] == -5.76
