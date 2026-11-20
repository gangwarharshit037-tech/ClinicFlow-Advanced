from datetime import timedelta
from unittest.mock import patch
from app import conn, now, run_reminders

# Create a fictional appointment one hour from now.
appointment_time = now() + timedelta(hours=1)

test_date = appointment_time.strftime("%Y-%m-%d")
test_time = appointment_time.strftime("%H:%M")

test_id = None

try:
    with conn() as c:
        cursor = c.execute(
            """
            INSERT INTO appointments
            (patient, phone, doctor, date, time, status, reminded)
            VALUES (?, ?, ?, ?, ?, 'Booked', 0)
            """,
            (
                "ClinicFlow Test Patient",
                "910000000000",
                "Preview Test Doctor",
                test_date,
                test_time
            )
        )
        test_id = cursor.lastrowid

    print("Created test appointment:", test_id)

    # Prevent this test from making WhatsApp API calls.
    with patch(
        "app.send_whatsapp",
        side_effect=AssertionError("WhatsApp sending is disabled")
    ):
        results = run_reminders()

    test_results = [
        item for item in results
        if item["appointment_id"] == test_id
    ]

    print("TEST PREVIEW:", test_results)

    with conn() as c:
        row = c.execute(
            "SELECT reminded FROM appointments WHERE id=?",
            (test_id,)
        ).fetchone()

    print("Reminded flag:", row["reminded"])

finally:
    if test_id is not None:
        with conn() as c:
            c.execute(
                """
                DELETE FROM appointments
                WHERE id=?
                AND patient='ClinicFlow Test Patient'
                AND doctor='Preview Test Doctor'
                """,
                (test_id,)
            )

        print("Test appointment cleanup completed.")