import sqlite3

from contextlib import closing

import pandas as pd

from reporting.build_analytics_db import DATABASE


ADVANCED_QUERIES = {

    "monthly_growth": """
        WITH monthly AS (
            SELECT
                year,
                month_number,
                month_name,
                total_appointments,
                booked,
                cancelled,

                LAG(total_appointments) OVER (
                    ORDER BY year, month_number
                ) AS previous_month

            FROM vw_monthly_summary
        )

        SELECT
            *,

            total_appointments - previous_month
                AS monthly_change,

            ROUND(
                100.0 *
                (total_appointments - previous_month)
                / NULLIF(previous_month, 0),
                2
            ) AS growth_percentage

        FROM monthly
        ORDER BY year, month_number
    """,

    "cumulative_appointments": """
        SELECT
            year,
            month_number,
            month_name,
            total_appointments,
            booked,
            cancelled,

            SUM(total_appointments) OVER (
                ORDER BY year, month_number
                ROWS BETWEEN UNBOUNDED PRECEDING
                    AND CURRENT ROW
            ) AS cumulative_appointments,

            SUM(booked) OVER (
                ORDER BY year, month_number
                ROWS BETWEEN UNBOUNDED PRECEDING
                    AND CURRENT ROW
            ) AS cumulative_booked,

            SUM(cancelled) OVER (
                ORDER BY year, month_number
                ROWS BETWEEN UNBOUNDED PRECEDING
                    AND CURRENT ROW
            ) AS cumulative_cancelled

        FROM vw_monthly_summary
        ORDER BY year, month_number
    """,

    "rolling_seven_day_average": """
        WITH daily AS (
            SELECT
                appointment_date,
                total_appointments,
                booked,
                cancelled,

                AVG(total_appointments) OVER (
                    ORDER BY appointment_date
                    ROWS BETWEEN 6 PRECEDING
                        AND CURRENT ROW
                ) AS rolling_average,

                COUNT(*) OVER (
                    ORDER BY appointment_date
                    ROWS BETWEEN 6 PRECEDING
                        AND CURRENT ROW
                ) AS window_days

            FROM vw_daily_summary
        )

        SELECT
            appointment_date,
            total_appointments,
            booked,
            cancelled,
            window_days,

            CASE
                WHEN window_days = 7
                THEN ROUND(rolling_average, 2)
                ELSE NULL
            END AS rolling_7_day_average

        FROM daily
        ORDER BY appointment_date
    """,

    "department_contribution": """
        WITH departments AS (
            SELECT
                department,
                COUNT(*) AS total_appointments,

                SUM(CASE WHEN status = 'Booked'
                    THEN 1 ELSE 0 END) AS booked,

                SUM(CASE WHEN status = 'Cancelled'
                    THEN 1 ELSE 0 END) AS cancelled

            FROM vw_appointments
            GROUP BY department
        )

        SELECT
            *,

            ROUND(
                100.0 * total_appointments /
                NULLIF(
                    SUM(total_appointments) OVER (),
                    0
                ), 2
            ) AS contribution_percentage,

            ROUND(
                100.0 * cancelled /
                NULLIF(total_appointments, 0),
                2
            ) AS cancellation_rate,

            DENSE_RANK() OVER (
                ORDER BY total_appointments DESC
            ) AS department_rank

        FROM departments
        ORDER BY department_rank, department
    """,

    "monthly_doctor_rankings": """
        WITH doctor_monthly AS (
            SELECT
                year,
                month_number,
                month_name,
                doctor,
                department,
                COUNT(*) AS total_appointments,

                SUM(CASE WHEN status = 'Booked'
                    THEN 1 ELSE 0 END) AS booked,

                SUM(CASE WHEN status = 'Cancelled'
                    THEN 1 ELSE 0 END) AS cancelled

            FROM vw_appointments

            GROUP BY
                year,
                month_number,
                month_name,
                doctor,
                department
        )

        SELECT
            *,

            DENSE_RANK() OVER (
                PARTITION BY year, month_number
                ORDER BY total_appointments DESC
            ) AS monthly_rank,

            ROW_NUMBER() OVER (
                PARTITION BY year, month_number
                ORDER BY total_appointments DESC, doctor
            ) AS monthly_position,

            ROUND(
                100.0 * total_appointments /
                NULLIF(
                    SUM(total_appointments) OVER (
                        PARTITION BY year, month_number
                    ), 0
                ), 2
            ) AS monthly_contribution

        FROM doctor_monthly

        ORDER BY
            year,
            month_number,
            monthly_position
    """,

    "department_monthly_growth": """
        WITH monthly AS (
            SELECT
                year,
                month_number,
                month_name,
                department,
                COUNT(*) AS total_appointments

            FROM vw_appointments

            GROUP BY
                year,
                month_number,
                month_name,
                department
        ),

        comparison AS (
            SELECT
                *,

                LAG(total_appointments) OVER (
                    PARTITION BY department
                    ORDER BY year, month_number
                ) AS previous_month

            FROM monthly
        )

        SELECT
            *,

            total_appointments - previous_month
                AS monthly_change,

            ROUND(
                100.0 *
                (total_appointments - previous_month)
                / NULLIF(previous_month, 0),
                2
            ) AS growth_percentage

        FROM comparison

        ORDER BY department, year, month_number
    """,
}


def run_advanced_analysis(database=DATABASE):

    uri = database.resolve().as_uri() + "?mode=ro"

    with closing(
        sqlite3.connect(uri, uri=True)
    ) as conn:

        conn.execute("PRAGMA query_only = ON")
        conn.execute("BEGIN")

        results = {
            name: pd.read_sql_query(query, conn)
            for name, query in ADVANCED_QUERIES.items()
        }

    return results


def main():

    print("=" * 70)
    print("CLINICFLOW ADVANCED SQL ANALYSIS")
    print("=" * 70)

    results = run_advanced_analysis()

    for name, df in results.items():

        print("\n" + "=" * 70)
        print(name.replace("_", " ").upper())
        print("=" * 70)

        if len(df) > 40:
            print(df.head(10).to_string(index=False))
            print("\n... Remaining records omitted ...\n")
            print(df.tail(5).to_string(index=False))
        else:
            print(df.to_string(index=False))

        print("\nTotal records:", len(df))

    print("\nTotal advanced reports:", len(results))
    print("\nSUCCESS: Advanced SQL analysis completed.")


if __name__ == "__main__":
    main()
