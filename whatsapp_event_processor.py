
from whatsapp_status_mapper import plan_webhook_status
from whatsapp_conflict_detector import detect_whatsapp_conflict


def process_deferred_event(db, event_id):
    """Atomically process one stored WhatsApp status event."""

    if db.in_transaction:
        raise RuntimeError("A database transaction is already active")

    try:
        db.execute("BEGIN IMMEDIATE")

        event = db.execute("""
            SELECT meta_message_id, meta_status
            FROM whatsapp_status_events
            WHERE id = ?
              AND processed = 0
              AND review_required = 0
        """, (event_id,)).fetchone()

        if event is None:
            db.commit()
            return {"action": "ignore"}

        message_id, meta_status = event

        attempts = db.execute("""
            SELECT appointment_id, reminder_type, status
            FROM reminder_attempts
            WHERE meta_message_id = ?
            LIMIT 2
        """, (message_id,)).fetchall()

        if len(attempts) != 1:
            db.commit()
            return {"action": "defer"}

        appointment_id, reminder_type, current_status = attempts[0]

        conflict = detect_whatsapp_conflict(
            current_status, meta_status
        )

        if conflict["action"] == "review":
            db.execute("""
                UPDATE whatsapp_status_events
                SET review_required = 1
                WHERE id = ?
                  AND processed = 0
            """, (event_id,))

            db.commit()

            return {
                "action": "review",
                "reason": conflict["reason"]
            }

        plan = plan_webhook_status(current_status, meta_status)

        if plan["action"] == "defer":
            db.commit()
            return {"action": "defer"}

        if plan["action"] == "update":
            cursor = db.execute("""
                UPDATE reminder_attempts
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE appointment_id = ?
                  AND reminder_type = ?
                  AND status = ?
                  AND meta_message_id = ?
            """, (
                plan["new_status"],
                appointment_id,
                reminder_type,
                current_status,
                message_id
            ))

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Reminder status changed unexpectedly"
                )

        db.execute("""
            UPDATE whatsapp_status_events
            SET processed = 1
            WHERE id = ?
              AND processed = 0
              AND review_required = 0
        """, (event_id,))

        db.commit()

        return {
            "action": (
                "updated"
                if plan["action"] == "update"
                else "processed"
            )
        }

    except Exception:
        db.rollback()
        raise
