from pathlib import Path
from datetime import date, timedelta
import random

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "synthetic" / "appointments_2025.csv"

SEED = 42
TOTAL_RECORDS = 10000
BOOKED_RECORDS = 8000
CANCELLED_RECORDS = 2000

START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 12, 31)

DOCTORS = [
    ("Dr. Asha Sharma", "General Medicine"),
    ("Dr. Rahul Verma", "Dental"),
    ("Dr. Neha Singh", "Dermatology"),
]

TIMES = [
    f"{hour:02d}:{minute:02d}"
    for hour in range(9, 18)
    for minute in (0, 30)
]


def generate_dataset():
    rng = random.Random(SEED)

    days = (END_DATE - START_DATE).days + 1

    dates = [
        START_DATE + timedelta(days=i)
        for i in range(days)
    ]

    available_slots = [
        (day, time, doctor, department)
        for day in dates
        for time in TIMES
        for doctor, department in DOCTORS
    ]

    booked_slots = rng.sample(
        available_slots,
        BOOKED_RECORDS
    )

    cancelled_slots = rng.choices(
        available_slots,
        k=CANCELLED_RECORDS
    )

    appointments = [
        (*slot, "Booked")
        for slot in booked_slots
    ] + [
        (*slot, "Cancelled")
        for slot in cancelled_slots
    ]

    rng.shuffle(appointments)

    records = []

    for index, appointment in enumerate(
        appointments, start=1
    ):
        day, time, doctor, department, status = appointment

        lead_time = rng.randint(0, 30)
        booking_date = day - timedelta(days=lead_time)

        hour = int(time.split(":")[0])

        if hour < 12:
            time_slot = "Morning"
        elif hour < 15:
            time_slot = "Afternoon"
        else:
            time_slot = "Evening"

        records.append({
            "Appointment_ID": f"APT{index:05d}",
            "Appointment_Date": day.isoformat(),
            "Appointment_Time": time,
            "Doctor": doctor,
            "Department": department,
            "Status": status,
            "Booking_Date": booking_date.isoformat(),
            "Lead_Time_Days": lead_time,
            "Year": day.year,
            "Month": day.strftime("%B"),
            "Quarter": f"Q{(day.month - 1) // 3 + 1}",
            "Day_of_Week": day.strftime("%A"),
            "Is_Weekend": "Yes" if day.weekday() >= 5 else "No",
            "Time_Slot": time_slot,
        })

    df = pd.DataFrame(records)

    df = df.sort_values(
        ["Appointment_Date", "Appointment_Time", "Doctor"]
    ).reset_index(drop=True)

    assert len(df) == TOTAL_RECORDS
    assert df["Appointment_ID"].is_unique
    assert not df.isna().any().any()

    booked = df[df["Status"] == "Booked"]

    assert len(booked) == BOOKED_RECORDS

    assert len(df[df["Status"] == "Cancelled"]) == CANCELLED_RECORDS

    assert not booked.duplicated(
        subset=[
            "Doctor",
            "Appointment_Date",
            "Appointment_Time",
        ]
    ).any()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8"
    )

    print("=" * 60)
    print("CLINICFLOW SYNTHETIC DATASET GENERATED")
    print("=" * 60)
    print("Output:", OUTPUT)
    print("Total records:", len(df))
    print("Total columns:", len(df.columns))
    print("Unique appointment IDs:", df["Appointment_ID"].nunique())
    print("Missing values:", df.isna().sum().sum())
    print("Duplicate active slots:", booked.duplicated(
        subset=["Doctor", "Appointment_Date", "Appointment_Time"]
    ).sum())

    print("\nSTATUS DISTRIBUTION")
    print(df["Status"].value_counts().to_string())

    print("\nDOCTOR DISTRIBUTION")
    print(df["Doctor"].value_counts().to_string())

    print("\nMONTHLY DISTRIBUTION")
    print(df.groupby(
        df["Appointment_Date"].str[:7]
    ).size().to_string())

    print("\nDate range:")
    print(df["Appointment_Date"].min())
    print(df["Appointment_Date"].max())

    print("\nSUCCESS: All generation checks passed.")


if __name__ == "__main__":
    generate_dataset()
