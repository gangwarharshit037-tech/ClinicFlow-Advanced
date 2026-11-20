

from reminder_lifecycle import can_transition

META_STATUS_MAP = {
    "sent": "accepted",
    "delivered": "delivered",
    "read": "delivered",
    "failed": "failed",
}


def plan_webhook_status(current_status, meta_status):
    """Plan a safe status update without changing the database."""

    target = META_STATUS_MAP.get(meta_status)

    if target is None:
        return {
            "action": "ignore",
            "reason": "Unsupported Meta status"
        }

    if current_status == target:
        return {
            "action": "ignore",
            "reason": "Duplicate or equivalent status"
        }

    # An early delivery confirmation requires two lifecycle steps.
    if current_status == "sending" and target == "delivered":
        return {
            "action": "defer",
            "reason": "Delivery arrived before API acceptance was recorded"
        }

    if can_transition(current_status, target):
        return {
            "action": "update",
            "new_status": target
        }

    return {
        "action": "ignore",
        "reason": "Transition not allowed or event out of order"
    }
