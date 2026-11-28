from pathlib import Path

import pandas as pd

from reporting.data_validation import (
    COLUMNS,
    DOCTOR_DEPARTMENTS,
    SOURCE,
    validate_dataset,
)


ROOT = Path(__file__).resolve().parents[1]

OUTPUT = (
    ROOT / "data" / "synthetic"
    / "appointments_2025_clean.csv"
)

NUMERIC_COLUMNS = [
    "Lead_Time_Days",
    "Year",
]

TEXT_COLUMNS = [
    column for column in COLUMNS
    if column not in NUMERIC_COLUMNS
]


def profile_dataset(df):
    blank_values = sum(
        df[column].astype("string")
        .str.strip().eq("").sum()
        for column in df.columns
    )

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_values": int(df.isna().sum().sum()),
        "blank_values": int(blank_values),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_kb": round(
            df.memory_usage(deep=True).sum() / 1024,
            2
        ),
    }


def clean_dataset(df):
    if list(df.columns) != COLUMNS:
        raise ValueError("Invalid dataset schema.")

    cleaned = df.copy(deep=True)

    for column in TEXT_COLUMNS:
        cleaned[column] = (
            cleaned[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    cleaned["Appointment_ID"] = (
        cleaned["Appointment_ID"].str.upper()
    )

    cleaned["Status"] = (
        cleaned["Status"].str.title()
    )

    doctor_lookup = {
        doctor.casefold(): doctor
        for doctor in DOCTOR_DEPARTMENTS
    }

    department_lookup = {
        department.casefold(): department
        for department in DOCTOR_DEPARTMENTS.values()
    }

    for column, lookup in [
        ("Doctor", doctor_lookup),
        ("Department", department_lookup),
    ]:
        original = cleaned[column]

        mapped = original.str.casefold().map(lookup)

        cleaned[column] = mapped.fillna(original)

    for column in [
        "Month",
        "Day_of_Week",
        "Is_Weekend",
        "Time_Slot",
    ]:
        cleaned[column] = cleaned[column].str.title()

    cleaned["Quarter"] = (
        cleaned["Quarter"].str.upper()
    )

    for column in NUMERIC_COLUMNS:
        cleaned[column] = pd.to_numeric(
            cleaned[column],
            errors="coerce"
        )

    cleaned = cleaned.drop_duplicates()

    if cleaned.isna().any().any():
        raise ValueError(
            "Missing or invalid essential values detected."
        )

    for column in NUMERIC_COLUMNS:
        if not cleaned[column].mod(1).eq(0).all():
            raise ValueError(
                f"Non-integer values in {column}."
            )

        cleaned[column] = cleaned[column].astype("int64")

    cleaned = cleaned.sort_values(
        [
            "Appointment_Date",
            "Appointment_Time",
            "Doctor",
            "Appointment_ID",
        ]
    ).reset_index(drop=True)

    results = validate_dataset(cleaned)

    failed = [
        name for name, passed in results.items()
        if not passed
    ]

    if failed:
        raise ValueError(
            "Validation failed: " + ", ".join(failed)
        )

    return cleaned


def print_profile(title, profile):
    print("\n" + title)
    print("-" * 50)

    for name, value in profile.items():
        print(f"{name}: {value}")


def main():
    raw = pd.read_csv(SOURCE)

    before = profile_dataset(raw)

    cleaned = clean_dataset(raw)

    after = profile_dataset(cleaned)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    cleaned.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8"
    )

    print("=" * 60)
    print("CLINICFLOW DATA CLEANING REPORT")
    print("=" * 60)

    print_profile("BEFORE CLEANING", before)
    print_profile("AFTER CLEANING", after)

    print(
        "\nRows removed:",
        before["rows"] - after["rows"]
    )

    print("\nDATA TYPES")
    print(cleaned.dtypes.to_string())

    print("\nSTATUS DISTRIBUTION")
    print(cleaned["Status"].value_counts().to_string())

    print("\nOutput:", OUTPUT)

    print(
        "\nSUCCESS: Clean dataset passed "
        "all validation checks."
    )


if __name__ == "__main__":
    main()
