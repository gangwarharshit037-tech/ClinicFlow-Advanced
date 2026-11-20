"""
ClinicFlow Advanced - local Waitress launcher.

Run:
    python run_local.py

Access:
    http://127.0.0.1:5000

This launcher is for local use only.
"""

import os

# Apply safety settings before importing the application.
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["REMINDER_SEND_ENABLED"] = "false"
os.environ["WHATSAPP_STATUS_STORAGE_ENABLED"] = "false"

from waitress import serve
from wsgi import app


def main():
    print("ClinicFlow Advanced - Local Waitress Server")
    print("Address: http://127.0.0.1:5000")
    print("Scheduler: DISABLED")
    print("Reminder sending: DISABLED")
    print("Status storage: DISABLED")
    print("Press Ctrl+C to stop.")

    serve(
        app,
        host="127.0.0.1",
        port=5000,
        threads=4
    )


if __name__ == "__main__":
    main()
