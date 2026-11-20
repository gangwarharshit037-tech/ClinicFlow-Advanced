
VALID_META_STATUSES = {
    "sent",
    "delivered",
    "read",
    "failed"
}


def store_whatsapp_event(
    db,
    message_id,
    meta_status,
    timestamp=None,
    manage_transaction=True
):
    """Safely store a WhatsApp status event."""

    if not isinstance(message_id, str) or not message_id.strip():
        return {
            "action": "ignore",
            "reason": "Invalid message ID"
        }

    if meta_status not in VALID_META_STATUSES:
        return {
            "action": "ignore",
            "reason": "Unsupported Meta status"
        }

    if manage_transaction and db.in_transaction:
        raise RuntimeError(
            "A database transaction is already active"
        )

    if not manage_transaction and not db.in_transaction:
        raise RuntimeError(
            "Caller-managed transaction is required"
        )

    try:
        if manage_transaction:
            db.execute("BEGIN IMMEDIATE")

        cursor = db.execute(
            """
            INSERT INTO whatsapp_status_events
            (meta_message_id, meta_status, event_timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(meta_message_id, meta_status) DO NOTHING
            """,
            (message_id, meta_status, timestamp)
        )

        inserted = cursor.rowcount == 1

        if manage_transaction:
            db.commit()

        if inserted:
            return {
                "action": "stored",
                "message_id": message_id,
                "status": meta_status
            }

        return {
            "action": "duplicate",
            "message_id": message_id,
            "status": meta_status
        }

    except Exception:
        if manage_transaction:
            db.rollback()
        raise
