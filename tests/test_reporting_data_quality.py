import pandas as pd
import pytest

from reporting.data_validation import (
    SOURCE,
    validate_dataset,
)

from reporting.data_cleaning import (
    clean_dataset,
    profile_dataset,
)


@pytest.fixture(scope="module")
def raw_dataset():
    return pd.read_csv(SOURCE)


def test_original_dataset_validation(raw_dataset):
    results = validate_dataset(raw_dataset)

    assert len(results) == 24
    assert all(results.values())


def test_dataset_profile(raw_dataset):
    profile = profile_dataset(raw_dataset)

    assert profile["rows"] == 10000
    assert profile["columns"] == 14
    assert profile["missing_values"] == 0
    assert profile["blank_values"] == 0
    assert profile["duplicate_rows"] == 0


def test_clean_dataset_preserves_records(raw_dataset):
    cleaned = clean_dataset(raw_dataset)

    assert len(cleaned) == 10000
    assert cleaned["Status"].eq("Booked").sum() == 8000
    assert cleaned["Status"].eq("Cancelled").sum() == 2000
    assert all(validate_dataset(cleaned).values())


def test_cleaning_does_not_modify_input(raw_dataset):
    original = raw_dataset.copy(deep=True)

    clean_dataset(raw_dataset)

    pd.testing.assert_frame_equal(
        raw_dataset,
        original
    )


def test_whitespace_and_capitalization(raw_dataset):
    dirty = raw_dataset.copy(deep=True)

    dirty.loc[0, "Status"] = (
        "  " + dirty.loc[0, "Status"].lower() + "  "
    )

    dirty.loc[0, "Doctor"] = (
        dirty.loc[0, "Doctor"].upper()
    )

    dirty.loc[0, "Department"] = (
        dirty.loc[0, "Department"].lower()
    )

    dirty.loc[0, "Month"] = (
        " " + dirty.loc[0, "Month"].lower() + " "
    )

    cleaned = clean_dataset(dirty)
    expected = clean_dataset(raw_dataset)

    pd.testing.assert_frame_equal(
        cleaned,
        expected
    )


def test_exact_duplicate_removal(raw_dataset):
    dirty = pd.concat(
        [raw_dataset, raw_dataset.iloc[[0]]],
        ignore_index=True
    )

    assert len(dirty) == 10001

    cleaned = clean_dataset(dirty)

    assert len(cleaned) == 10000
    assert not cleaned.duplicated().any()

    pd.testing.assert_frame_equal(
        cleaned,
        clean_dataset(raw_dataset)
    )


def test_numeric_conversion(raw_dataset):
    dirty = raw_dataset.copy(deep=True)

    dirty["Lead_Time_Days"] = (
        dirty["Lead_Time_Days"].astype(str)
    )

    dirty["Year"] = dirty["Year"].astype(str)

    cleaned = clean_dataset(dirty)

    assert str(cleaned["Lead_Time_Days"].dtype) == "int64"
    assert str(cleaned["Year"].dtype) == "int64"


def test_cleaning_is_idempotent(raw_dataset):
    first = clean_dataset(raw_dataset)
    second = clean_dataset(first)

    pd.testing.assert_frame_equal(
        first,
        second
    )


@pytest.mark.parametrize(
    "column,value",
    [
        ("Appointment_ID", "INVALID"),
        ("Appointment_Date", "invalid-date"),
        ("Appointment_Time", "25:00"),
        ("Doctor", "Unknown Doctor"),
        ("Department", "Unknown Department"),
        ("Status", "Unknown Status"),
        ("Booking_Date", "2030-01-01"),
        ("Lead_Time_Days", "-1"),
        ("Year", "2030"),
        ("Month", "Invalid Month"),
        ("Quarter", "Q9"),
    ],
)
def test_invalid_values_rejected(
    raw_dataset,
    column,
    value
):
    dirty = raw_dataset.copy(deep=True)

    dirty[column] = dirty[column].astype(object)
    dirty.loc[0, column] = value

    with pytest.raises(ValueError):
        clean_dataset(dirty)


def test_unexpected_columns_rejected(raw_dataset):
    dirty = raw_dataset.copy(deep=True)

    dirty["Unexpected_Column"] = "TEST"

    with pytest.raises(ValueError, match="schema"):
        clean_dataset(dirty)
