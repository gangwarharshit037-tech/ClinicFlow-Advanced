"""
ClinicFlow Advanced production WSGI entrypoint.

The application scheduler is intentionally disabled
inside web-server worker processes.

Run scheduled jobs separately when explicitly configured.
"""

import os

# Must be set before importing app.py.
os.environ["ENABLE_SCHEDULER"] = "false"

from app import app

__all__ = ["app"]
