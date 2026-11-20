"""Store WhatsApp status events as an atomic batch.

Not connected to the live Flask webhook.
Does not send WhatsApp messages.
"""

from whatsapp_status_parser import extract_whatsapp_statuses
from whatsapp_event_store import store_whatsapp_event


def handle_status_event_payload(db, payload):
    """Store all valid events or roll back the entire batch."""

    events = extract_whatsapp_statuses(payload)

    result = {
        "received": len(events),
        "stored": 0,
        "duplicates": 0,
        "ignored": 0
    }

    if db.in_transaction:
        raise RuntimeError(
            "A database transaction is already active"
        )

    db.execute("BEGIN IMMEDIATE")

    try:
        for event in events:
            outcome = store_whatsapp_event(
                db,
                event["message_id"],
                event["status"],
                event.get("timestamp"),
                manage_transaction=False
            )

            action = outcome["action"]

            if action == "stored":
                result["stored"] += 1
            elif action == "duplicate":
                result["duplicates"] += 1
            else:
                result["ignored"] += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    return result
