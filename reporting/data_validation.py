from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data" / "synthetic" / "appointments_2025.csv"

COLUMNS = [
    "Appointment_ID",
    "Appointment_Date",
    "Appointment_Time",
    "Doctor",
    "Department",
    "Status",
    "Booking_Date",
    "Lead_Time_Days",
    "Year",
    "Month",
    "Quarter",
    "Day_of_Week",
    "Is_Weekend",
    "Time_Slot",
]

DOCTOR_DEPARTMENTS = {
    "Dr. Asha Sharma": "General Medicine",
    "Dr. Rahul Verma": "Dental",
    "Dr. Neha Singh": "Dermatology",
}

VALID_TIMES = {
    f"{hour:02d}:{minute:02d}"
    for hour in range(9, 18)
    for minute in (0, 30)
}


def validate_dataset(df):
    results = {}

    def check(name, condition):
        results[name] = bool(condition)

    check("Correct schema", list(df.columns) == COLUMNS)

    if not results["Correct schema"]:
        return results

    check("Record count", len(df) == 10000)

    check(
        "No missing values",
        not df.isna().any().any()
        and not df.astype(str).apply(
            lambda col: col.str.strip().eq("")
        ).any().any()
    )

    check(
        "Unique appointment IDs",
        df["Appointment_ID"].is_unique
    )

    check(
        "Valid appointment IDs",
        df["Appointment_ID"].astype(str)
        .str.fullmatch(r"APT[0-9]{5}").all()
    )

    check(
        "No duplicate rows",
        not df.duplicated().any()
    )

    check(
        "Valid statuses",
        df["Status"].isin(["Booked", "Cancelled"]).all()
    )

    check(
        "Expected status distribution",
        df["Status"].eq("Booked").sum() == 8000
        and df["Status"].eq("Cancelled").sum() == 2000
    )

    check(
        "Valid doctors",
        df["Doctor"].isin(DOCTOR_DEPARTMENTS).all()
    )

    check(
        "Doctor department consistency",
        df["Doctor"].map(DOCTOR_DEPARTMENTS)
        .eq(df["Department"]).all()
    )

    check(
        "Valid appointment times",
        df["Appointment_Time"].isin(VALID_TIMES).all()
    )

    appointment_dates = pd.to_datetime(
        df["Appointment_Date"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    booking_dates = pd.to_datetime(
        df["Booking_Date"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    check(
        "Valid appointment dates",
        appointment_dates.notna().all()
        and df["Appointment_Date"].astype(str)
        .str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
    )

    check(
        "Valid booking dates",
        booking_dates.notna().all()
        and df["Booking_Date"].astype(str)
        .str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
    )

    check(
        "Appointment date range",
        appointment_dates.between(
            "2025-01-01", "2025-12-31"
        ).all()
    )

    check(
        "Booking before or on appointment",
        booking_dates.le(appointment_dates).all()
    )

    lead_time = pd.to_numeric(
        df["Lead_Time_Days"],
        errors="coerce"
    )

    calculated_lead = (
        appointment_dates - booking_dates
    ).dt.days

    check(
        "Lead time range",
        lead_time.between(0, 30).all()
    )

    check(
        "Lead time accuracy",
        calculated_lead.eq(lead_time).all()
    )

    check(
        "Year consistency",
        appointment_dates.dt.year.eq(
            pd.to_numeric(df["Year"], errors="coerce")
        ).all()
    )

    check(
        "Month consistency",
        appointment_dates.dt.month_name()
        .eq(df["Month"]).all()
    )

    expected_quarter = appointment_dates.dt.quarter.map({
        1: "Q1",
        2: "Q2",
        3: "Q3",
        4: "Q4",
    })

    check(
        "Quarter consistency",
        expected_quarter.eq(df["Quarter"]).all()
    )

    check(
        "Day of week consistency",
        appointment_dates.dt.day_name()
        .eq(df["Day_of_Week"]).all()
    )

    expected_weekend = (
        appointment_dates.dt.dayofweek.ge(5)
        .map({True: "Yes", False: "No"})
    )

    check(
        "Weekend consistency",
        expected_weekend.eq(df["Is_Weekend"]).all()
    )

    def classify_time(value):
        if value not in VALID_TIMES:
            return None

        hour = int(value.split(":")[0])

        if hour < 12:
            return "Morning"
        if hour < 15:
            return "Afternoon"

        return "Evening"

    check(
        "Time slot consistency",
        df["Appointment_Time"].map(classify_time)
        .eq(df["Time_Slot"]).all()
    )

    booked = df[df["Status"] == "Booked"]

    check(
        "No duplicate active slots",
        not booked.duplicated(
            subset=[
                "Doctor",
                "Appointment_Date",
                "Appointment_Time",
            ]
        ).any()
    )

    return results


def main():
    df = pd.read_csv(SOURCE)

    results = validate_dataset(df)

    print("=" * 60)
    print("CLINICFLOW DATA QUALITY VALIDATION")
    print("=" * 60)

    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")

    passed_count = sum(results.values())
    failed_count = len(results) - passed_count

    print("\nTotal checks:", len(results))
    print("Passed:", passed_count)
    print("Failed:", failed_count)

    score = passed_count / len(results) * 100

    print(f"Validation pass rate: {score:.2f}%")

    if failed_count:
        raise SystemExit(1)

    print("\nSUCCESS: All data quality checks passed.")


if __name__ == "__main__":
    main()
