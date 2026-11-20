
import sqlite3


def migrate_whatsapp_events(db):
    """Create WhatsApp event storage without deleting existing data."""

    if db.in_transaction:
        raise RuntimeError("A database transaction is already active")

    try:
        db.execute("BEGIN IMMEDIATE")

        db.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_status_events (
                id INTEGER PRIMARY KEY,
                meta_message_id TEXT NOT NULL,
                meta_status TEXT NOT NULL,
                event_timestamp TEXT,
                processed INTEGER NOT NULL DEFAULT 0
                    CHECK (processed IN (0, 1)),
                review_required INTEGER NOT NULL DEFAULT 0
                    CHECK (review_required IN (0, 1)),
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(meta_message_id, meta_status)
            )
        """)

        columns = {
            row[1]
            for row in db.execute(
                "PRAGMA table_info(whatsapp_status_events)"
            )
        }

        required = {
            "id",
            "meta_message_id",
            "meta_status",
            "event_timestamp",
            "processed",
            "review_required",
            "created_at",
        }

        if not required.issubset(columns):
            raise RuntimeError(
                "Existing WhatsApp event table has an "
                "incompatible schema"
            )

        db.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_whatsapp_events_review
            ON whatsapp_status_events(
                review_required,
                processed,
                id
            )
        """)

        db.commit()
        return {"action": "ready"}

    except Exception:
        db.rollback()
        raise
