import sqlite3

from contextlib import closing

import pandas as pd

from reporting.build_analytics_db import DATABASE


QUERIES = {

    "executive_kpis": """
        SELECT
            COUNT(*) AS total_appointments,

            SUM(CASE WHEN status = 'Booked'
                THEN 1 ELSE 0 END) AS booked,

            SUM(CASE WHEN status = 'Cancelled'
                THEN 1 ELSE 0 END) AS cancelled,

            ROUND(
                100.0 * SUM(CASE WHEN status = 'Booked'
                    THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 2
            ) AS booked_rate,

            ROUND(
                100.0 * SUM(CASE WHEN status = 'Cancelled'
                    THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 2
            ) AS cancellation_rate,

            COUNT(DISTINCT doctor_id) AS total_doctors,

            ROUND(AVG(lead_time_days), 2)
                AS avg_lead_time_days,

            ROUND(
                1.0 * COUNT(*) /
                NULLIF((
                    SELECT COUNT(*)
                    FROM dim_date
                    WHERE year = 2025
                ), 0), 2
            ) AS avg_daily_appointments

        FROM fact_appointments
    """,

    "doctor_performance": """
        SELECT
            *,
            DENSE_RANK() OVER (
                ORDER BY total_appointments DESC
            ) AS volume_rank
        FROM vw_doctor_summary
        ORDER BY volume_rank, doctor
    """,

    "monthly_performance": """
        SELECT *
        FROM vw_monthly_summary
        ORDER BY year, month_number
    """,

    "quarterly_performance": """
        SELECT
            year,
            quarter,
            COUNT(*) AS total_appointments,

            SUM(CASE WHEN status = 'Booked'
                THEN 1 ELSE 0 END) AS booked,

            SUM(CASE WHEN status = 'Cancelled'
                THEN 1 ELSE 0 END) AS cancelled,

            ROUND(
                100.0 * SUM(CASE WHEN status = 'Cancelled'
                    THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 2
            ) AS cancellation_rate,

            ROUND(AVG(lead_time_days), 2)
                AS avg_lead_time_days

        FROM vw_appointments
        GROUP BY year, quarter
        ORDER BY year, quarter
    """,

    "peak_appointment_hours": """
        SELECT
            *,
            DENSE_RANK() OVER (
                ORDER BY total_appointments DESC
            ) AS volume_rank
        FROM vw_time_summary
        ORDER BY volume_rank, appointment_time
    """,

    "weekday_weekend_analysis": """
        SELECT
            CASE
                WHEN dt.is_weekend = 1 THEN 'Weekend'
                ELSE 'Weekday'
            END AS day_type,

            COUNT(DISTINCT dt.date_key)
                AS calendar_days,

            COUNT(f.appointment_id)
                AS total_appointments,

            SUM(CASE WHEN f.status = 'Booked'
                THEN 1 ELSE 0 END) AS booked,

            SUM(CASE WHEN f.status = 'Cancelled'
                THEN 1 ELSE 0 END) AS cancelled,

            ROUND(
                1.0 * COUNT(f.appointment_id)
                / NULLIF(
                    COUNT(DISTINCT dt.date_key), 0
                ), 2
            ) AS avg_daily_appointments,

            ROUND(
                100.0 * SUM(CASE WHEN f.status = 'Cancelled'
                    THEN 1 ELSE 0 END)
                / NULLIF(COUNT(f.appointment_id), 0),
                2
            ) AS cancellation_rate

        FROM dim_date AS dt
        LEFT JOIN fact_appointments AS f
            ON dt.date_key = f.appointment_date

        WHERE dt.year = 2025

        GROUP BY dt.is_weekend
        ORDER BY dt.is_weekend
    """,

    "lead_time_analysis": """
        SELECT *
        FROM vw_lead_time_summary
        ORDER BY sort_order
    """,

    "monthly_cancellation_analysis": """
        SELECT
            month_name,
            total_appointments,
            cancelled,
            cancellation_rate,

            DENSE_RANK() OVER (
                ORDER BY
                    1.0 * cancelled /
                    NULLIF(total_appointments, 0) DESC
            ) AS cancellation_rank

        FROM vw_monthly_summary
        ORDER BY cancellation_rank, month_number
    """,

    "busiest_appointment_days": """
        SELECT
            *,
            DENSE_RANK() OVER (
                ORDER BY total_appointments DESC
            ) AS volume_rank
        FROM vw_daily_summary
        ORDER BY volume_rank, appointment_date
        LIMIT 10
    """,

    "time_slot_analysis": """
        SELECT
            time_slot,
            COUNT(*) AS total_appointments,

            SUM(CASE WHEN status = 'Booked'
                THEN 1 ELSE 0 END) AS booked,

            SUM(CASE WHEN status = 'Cancelled'
                THEN 1 ELSE 0 END) AS cancelled,

            ROUND(
                100.0 * COUNT(*) /
                NULLIF((
                    SELECT COUNT(*)
                    FROM fact_appointments
                ), 0), 2
            ) AS appointment_share,

            ROUND(
                100.0 * SUM(CASE WHEN status = 'Cancelled'
                    THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 2
            ) AS cancellation_rate

        FROM vw_appointments
        GROUP BY time_slot

        ORDER BY CASE time_slot
            WHEN 'Morning' THEN 1
            WHEN 'Afternoon' THEN 2
            ELSE 3
        END
    """,
}


def run_business_analysis(database=DATABASE):

    uri = database.resolve().as_uri() + "?mode=ro"

    with closing(
        sqlite3.connect(uri, uri=True)
    ) as conn:

        conn.execute("PRAGMA query_only = ON")
        conn.execute("BEGIN")

        results = {
            name: pd.read_sql_query(query, conn)
            for name, query in QUERIES.items()
        }

    return results


def main():

    print("=" * 70)
    print("CLINICFLOW ADVANCED BUSINESS KPI ANALYSIS")
    print("=" * 70)

    results = run_business_analysis()

    for name, df in results.items():

        print("\n" + "=" * 70)

        print(name.replace("_", " ").upper())

        print("=" * 70)

        print(df.to_string(index=False))

    print("\nTotal analysis reports:", len(results))

    print("\nSUCCESS: Business KPI analysis completed.")


if __name__ == "__main__":
    main()
