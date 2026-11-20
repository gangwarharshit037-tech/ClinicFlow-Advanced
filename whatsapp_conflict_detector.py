
def detect_whatsapp_conflict(current_status, meta_status):
    """Detect conflicting WhatsApp status notifications."""

    delivery_statuses = {"delivered", "read"}

    if current_status == "failed" and meta_status in delivery_statuses:
        return {
            "action": "review",
            "reason": "Delivery confirmation conflicts with failed status"
        }

    if current_status == "delivered" and meta_status == "failed":
        return {
            "action": "review",
            "reason": "Failure notification conflicts with delivered status"
        }

    return {
        "action": "none",
        "reason": "No terminal status conflict detected"
    }
