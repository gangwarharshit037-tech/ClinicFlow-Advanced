
from whatsapp_status_mapper import plan_webhook_status
from reminder_lifecycle import update_reminder_status


def handle_whatsapp_status(db, message_id, meta_status):
    """
    Process a WhatsApp delivery status using an existing
    database connection.

    Does not send WhatsApp messages.
    """

    if not isinstance(message_id, str) or not message_id:
        return {
            "action": "ignore",
            "reason": "Invalid message ID"
        }

    rows = db.execute(
        """
        SELECT appointment_id, reminder_type, status
        FROM reminder_attempts
        WHERE meta_message_id = ?
        LIMIT 2
        """,
        (message_id,)
    ).fetchall()

    if not rows:
        return {
            "action": "ignore",
            "reason": "Unknown WhatsApp message ID"
        }

    if len(rows) != 1:
        return {
            "action": "ignore",
            "reason": "Ambiguous WhatsApp message ID"
        }

    appointment_id, reminder_type, current_status = rows[0]

    plan = plan_webhook_status(
        current_status,
        meta_status
    )

    if plan["action"] != "update":
        return plan

    updated = update_reminder_status(
        db,
        appointment_id,
        current_status,
        plan["new_status"],
        reminder_type
    )

    if not updated:
        return {
            "action": "ignore",
            "reason": "Reminder status changed concurrently"
        }

    return {
        "action": "updated",
        "appointment_id": appointment_id,
        "new_status": plan["new_status"]
    }
