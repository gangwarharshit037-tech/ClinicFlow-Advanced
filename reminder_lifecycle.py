

"""Safe reminder lifecycle rules for ClinicFlow."""

ALLOWED_TRANSITIONS = {
    "pending": {"sending"},
    "sending": {"accepted", "failed", "uncertain"},
    "accepted": {"delivered", "failed"},
    "delivered": set(),
    "failed": set(),
    "uncertain": set(),
}


def can_transition(current_status, new_status):
    """Return True only for an allowed status change."""
    return new_status in ALLOWED_TRANSITIONS.get(
        current_status, set()
    )
def can_transition(current_status, new_status):
    """Return True only for an allowed status change."""
    return new_status in ALLOWED_TRANSITIONS.get(
        current_status, set()
    )




def update_reminder_status(
    db,
    appointment_id,
    current_status,
    new_status,
    reminder_type="24h"
):
    """Safely update one reminder in its own transaction."""

    if not can_transition(current_status, new_status):
        return False

    if db.in_transaction:
        raise RuntimeError("A transaction is already active")

    try:
        db.execute("BEGIN IMMEDIATE")

        cursor = db.execute(
            """
            UPDATE reminder_attempts
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE appointment_id = ?
              AND reminder_type = ?
              AND status = ?
            """,
            (
                new_status,
                appointment_id,
                reminder_type,
                current_status
            )
        )

        updated = cursor.rowcount == 1
        db.commit()
        return updated

    except Exception:
        db.rollback()
        raise
