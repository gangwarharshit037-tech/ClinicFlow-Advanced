
import os
import traceback
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
calendar_id = os.getenv("GOOGLE_CALENDAR_ID")

try:
    print("Connecting to Google Calendar...", flush=True)

    credentials = service_account.Credentials.from_service_account_file(
        path,
        scopes=["https://www.googleapis.com/auth/calendar"]
    )

    service = build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False
    )

    print("Checking calendar access...", flush=True)

    result = service.calendars().get(
        calendarId=calendar_id
    ).execute()

    print("SUCCESS: Google Calendar connection works!")
    print("Calendar name:", result.get("summary"))
    print("Testing event creation...", flush=True)

    event = {
        "summary": "ClinicFlow API Test Appointment",
        "start": {
            "dateTime": "2026-11-25T10:30:00+05:30",
            "timeZone": "Asia/Kolkata"
        },
        "end": {
            "dateTime": "2026-11-25T11:00:00+05:30",
            "timeZone": "Asia/Kolkata"
        }
    }

    created = service.events().insert(
        calendarId=calendar_id,
        body=event
    ).execute()

    print("SUCCESS: Event created!")
    print("Event ID:", created.get("id"))
    print("Event Link:", created.get("htmlLink"))

except Exception:
    print("ERROR: Google Calendar connection failed.")
    traceback.print_exc()
