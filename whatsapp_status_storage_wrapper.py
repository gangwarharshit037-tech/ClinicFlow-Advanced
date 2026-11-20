"""Feature-flagged WhatsApp delivery-status storage.

This module is not connected to the live Flask webhook.
It does not send WhatsApp messages.
"""

from whatsapp_status_event_handler import handle_status_event_payload


def store_statuses_if_enabled(
    payload,
    connection_factory,
    enabled=False
):
    """Store statuses only when explicitly enabled."""

    if enabled is not True:
        return {
            "enabled": False,
            "received": 0,
            "stored": 0,
            "duplicates": 0,
            "ignored": 0
        }

    db = connection_factory()

    try:
        result = handle_status_event_payload(db, payload)

        return {
            "enabled": True,
            **result
        }

    finally:
        db.close()
