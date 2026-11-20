
def get_whatsapp_review_summary(db):
    """Return a read-only summary of WhatsApp status events."""

    row = db.execute("""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(
                CASE
                    WHEN processed = 0 AND review_required = 0
                    THEN 1 ELSE 0
                END
            ), 0) AS pending,
            COALESCE(SUM(
                CASE
                    WHEN processed = 0 AND review_required = 1
                    THEN 1 ELSE 0
                END
            ), 0) AS review_required,
            COALESCE(SUM(
                CASE
                    WHEN processed = 1
                    THEN 1 ELSE 0
                END
            ), 0) AS completed
        FROM whatsapp_status_events
    """).fetchone()

    return {
        "total": row[0],
        "pending": row[1],
        "review_required": row[2],
        "completed": row[3]
    }
