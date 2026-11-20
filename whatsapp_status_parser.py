

def extract_whatsapp_statuses(payload):
    """Safely extract WhatsApp delivery status events."""

    results = []

    if not isinstance(payload, dict):
        return results

    entries = payload.get("entry")

    if not isinstance(entries, list):
        return results

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        changes = entry.get("changes")

        if not isinstance(changes, list):
            continue

        for change in changes:
            if not isinstance(change, dict):
                continue

            value = change.get("value")

            if not isinstance(value, dict):
                continue

            statuses = value.get("statuses")

            if not isinstance(statuses, list):
                continue

            for item in statuses:
                if not isinstance(item, dict):
                    continue

                message_id = item.get("id")
                status = item.get("status")

                if not isinstance(message_id, str) or not message_id:
                    continue

                if status not in (
                    "sent",
                    "delivered",
                    "read",
                    "failed"
                ):
                    continue

                results.append({
                    "message_id": message_id,
                    "status": status,
                    "timestamp": item.get("timestamp")
                })

    return results
