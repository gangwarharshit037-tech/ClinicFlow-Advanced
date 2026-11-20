
def get_review_queue(db, limit=50):
    """Return WhatsApp events requiring manual review."""

    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError("Limit must be an integer")

    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")

    rows = db.execute("""
        SELECT
            id,
            meta_message_id,
            meta_status,
            event_timestamp
        FROM whatsapp_status_events
        WHERE processed = 0
          AND review_required = 1
        ORDER BY id ASC
        LIMIT ?
    """, (limit,)).fetchall()

    return [
        {
            "event_id": row[0],
            "message_id": row[1],
            "meta_status": row[2],
            "event_timestamp": row[3]
        }
        for row in rows
    ]
