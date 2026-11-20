
"""Safe reminder integration helpers.

This module does not send messages or modify the database.
"""

from reminder_lifecycle import can_transition


def can_start_reminder(status):
    """Check whether a pending reminder can enter sending."""
    return can_transition(status, "sending")

def plan_reminder_action(appointment_id, status="pending"):
    """Plan a reminder action without executing it."""

    if not can_start_reminder(status):
        return {
            "appointment_id": appointment_id,
            "action": "skip",
            "reason": f"Reminder status '{status}' cannot start sending"
        }

    return {
        "appointment_id": appointment_id,
        "action": "preview",
        "reason": "Live reminder sending is disabled"
    }

def get_reminder_status(db, appointment_id, reminder_type="24h"):
    """Read a reminder's status without modifying the database."""

    row = db.execute(
        """
        SELECT status
        FROM reminder_attempts
        WHERE appointment_id = ?
          AND reminder_type = ?
        """,
        (appointment_id, reminder_type)
    ).fetchone()

    if row is None:
        return None

    return row[0]

def plan_reminder_from_db(db, appointment_id, reminder_type="24h"):
    """Plan a preview action using the stored reminder status."""

    status = get_reminder_status(
        db, appointment_id, reminder_type
    )

    if status is None:
        return {
            "appointment_id": appointment_id,
            "action": "unclaimed",
            "reason": "No reminder attempt exists"
        }

    return plan_reminder_action(appointment_id, status)

def plan_safe_preview_from_db(db, appointment_id, reminder_type="24h"):
    """Decide whether to preview a reminder without claiming it."""

    plan = plan_reminder_from_db(
        db, appointment_id, reminder_type
    )

    if plan["action"] == "unclaimed":
        return {
            "appointment_id": appointment_id,
            "action": "preview",
            "reason": "Unclaimed reminder: preview only, no database claim"
        }

    return plan
