
from flask import Blueprint, jsonify
from whatsapp_review_queue import get_review_queue
from whatsapp_review_summary import get_whatsapp_review_summary


def create_monitoring_blueprint(admin_required, connection_factory):
    """Create an admin-protected, read-only monitoring API."""

    bp = Blueprint("whatsapp_monitoring", __name__)

    @bp.get("/api/admin/whatsapp/monitoring")
    @admin_required
    def monitoring():
        db = connection_factory()

        try:
            summary = get_whatsapp_review_summary(db)
            queue = get_review_queue(db, limit=20)

            # Do not expose WhatsApp message IDs or patient data.
            safe_queue = [
                {
                    "event_id": event["event_id"],
                    "meta_status": event["meta_status"]
                }
                for event in queue
            ]

            return jsonify({
                "ok": True,
                "summary": summary,
                "review_queue": safe_queue
            })

        finally:
            db.close()

    return bp
