# ClinicFlow Advanced

A Flask-based clinic appointment management application featuring
patient booking, an administrative dashboard, an AI receptionist
interface, appointment reminders, and integration-ready workflows.

## Project Overview

ClinicFlow Advanced helps demonstrate how a clinic can organize
appointments through a web application while maintaining an
administrative view of booking activity.

The project includes a patient-facing interface and a protected
admin dashboard.

## Features

- Patient appointment booking
- Doctor and time-slot selection
- Appointment validation
- Duplicate booking prevention
- Admin login and protected endpoints
- Appointment search and filtering
- Appointment cancellation
- CSV export interface
- AI receptionist chatbot interface
- Built-in clinic information responses
- WhatsApp delivery monitoring interface
- Reminder preview functionality
- Google Calendar integration code
- SQLite appointment storage
- CSRF protection for administrative actions

## Technology Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript
- Waitress
- APScheduler

Optional integrations include OpenAI, WhatsApp Cloud API,
and Google Calendar.

## Installation

### 1. Clone or download the project

Open a terminal inside the project directory.

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment settings

Create a local `.env` file with suitable development settings.

Recommended safety defaults:

```dotenv
LIVE_MODE=false
ENABLE_SCHEDULER=false
REMINDER_SEND_ENABLED=false
WHATSAPP_OUTBOUND_ENABLED=false
WHATSAPP_STATUS_STORAGE_ENABLED=false
```

Configure a strong local admin password and Flask secret key.

Never commit real credentials or patient data to GitHub.

### 5. Start the application

```powershell
python run_local.py
```

Open:

http://127.0.0.1:5000

Admin dashboard:

http://127.0.0.1:5000/admin

The included launcher is intended for local use.

## Main Application Modules

- `app.py` - Flask routes and application logic
- `wsgi.py` - WSGI application entry point
- `run_local.py` - Local Waitress server launcher
- `templates/` - Patient and admin interfaces
- `requirements.txt` - Python dependencies

## Appointment Workflow

1. A patient opens the booking interface.
2. The patient enters booking information.
3. The application validates the input.
4. SQLite stores the appointment.
5. The admin dashboard displays appointment information.
6. Authorized administrators can cancel appointments.

## AI Receptionist

The chatbot supports built-in responses about clinic hours,
available doctors, booking and cancellation guidance.

An optional OpenAI integration is present in the application,
but live API operation has not been verified by the isolated tests.

## Reminder and Messaging Safety

Reminder functionality currently operates in preview-only mode.

The project includes a separate outbound WhatsApp safety guard.

Recommended local settings:

```dotenv
REMINDER_SEND_ENABLED=false
WHATSAPP_OUTBOUND_ENABLED=false
WHATSAPP_STATUS_STORAGE_ENABLED=false
```

Do not enable live messaging without appropriate configuration,
consent, authorization and testing.

## Testing

The following workflows passed isolated or local tests:

- Homepage rendering
- Admin dashboard rendering
- Admin authentication protection
- CSRF validation for cancellation
- Appointment creation
- Duplicate booking rejection
- Invalid phone number rejection
- Appointment cancellation
- Built-in chatbot responses
- WhatsApp outbound blocking
- SQLite database integrity
- Reminder preview safety

External calendar and AI service calls were not exercised
in the isolated functional tests.

## Known Limitations

- Reminder sending is not implemented for live operation.
- Google Calendar integration has not been verified end-to-end.
- OpenAI integration has not been verified end-to-end.
- WhatsApp outbound messaging is disabled by default.
- This application is not validated for production clinical use.
- The demonstration does not provide medical advice.

## Security Notes

- Keep `.env` private.
- Do not publish real SQLite patient databases.
- Do not publish credential files or API tokens.
- Use HTTPS and appropriate deployment security controls
  before considering any public deployment.
- Review privacy, authentication, logging and access controls
  before handling real patient information.

## Portfolio Description

ClinicFlow Advanced is a Python Flask clinic appointment management
project featuring SQLite-based booking, a protected administrative
dashboard, appointment cancellation, an AI receptionist interface,
reminder previews and optional external service integrations.

## Project Status

Core local demonstration workflows have passed their tested scenarios.
Live external integrations require additional verification.
