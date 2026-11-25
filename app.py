from contextlib import closing
"""ClinicFlow Advanced: demo-first clinic automation. Python 3.10+."""
import os, re, json, hmac, hashlib, logging, sqlite3, secrets

from reminder_lifecycle import can_transition, update_reminder_status
from reminder_integration import plan_safe_preview_from_db
from whatsapp_status_parser import extract_whatsapp_statuses
from whatsapp_status_storage_wrapper import store_statuses_if_enabled
from whatsapp_event_migration import migrate_whatsapp_events

from datetime import datetime, timedelta, date
from functools import wraps
from zoneinfo import ZoneInfo
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from login_rate_limiter import FailedLoginLimiter
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024
app.secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=(
        os.getenv('PUBLIC_DEMO_MODE', 'false').lower() == 'true'
        or os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    ),
)
TZ=ZoneInfo(os.getenv('CLINIC_TIMEZONE','Asia/Kolkata'))
DB=Path(os.getenv('DATABASE_PATH','clinicflow.db'))
if not DB.is_absolute(): DB=ROOT/DB
LIVE=os.getenv('LIVE_MODE','false').lower()=='true'
print("CLINICFLOW LIVE MODE:", LIVE, flush=True)
DOCTORS=['Dr. Asha Sharma - General Medicine','Dr. Rahul Verma - Dental','Dr. Neha Singh - Dermatology']
TIMES=[f'{h:02d}:{m:02d}' for h in range(9,18) for m in (0,30)]
logging.basicConfig(level=logging.INFO)

def conn():
    c=sqlite3.connect(DB, timeout=20)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA busy_timeout=20000')
    return c

def init_db():
    with conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS appointments (
          id INTEGER PRIMARY KEY, patient TEXT NOT NULL, phone TEXT NOT NULL,
          doctor TEXT NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Booked', reminded INTEGER NOT NULL DEFAULT 0,
          calendar_event_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS active_slot ON appointments(doctor,date,time) WHERE status='Booked'")
        c.execute('''CREATE TABLE IF NOT EXISTS deliveries (
          id INTEGER PRIMARY KEY, appointment_id INTEGER, channel TEXT, status TEXT,
          detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('CREATE TABLE IF NOT EXISTS webhook_messages (message_id TEXT PRIMARY KEY, received_at TEXT DEFAULT CURRENT_TIMESTAMP)')
init_db()

# Ensure the read-only admin monitoring tables exist.
# This creates schema only; it does not enable WhatsApp storage.
with closing(conn()) as monitoring_db:
    migrate_whatsapp_events(monitoring_db)

def now(): return datetime.now(TZ)
def error(msg, status=400): return jsonify(error=msg), status

def admin_required(fn):
    @wraps(fn)
    def inner(*a,**kw):
        if not session.get('admin'): return error('Admin login required',401)
        return fn(*a,**kw)
    return inner


# Admin-only WhatsApp monitoring endpoint.
# Read-only access to the clinic database.

import sqlite3
from pathlib import Path
from whatsapp_monitoring_api import create_monitoring_blueprint


def whatsapp_monitoring_readonly_connection():
    db_path = DB

    return sqlite3.connect(
        db_path.as_uri() + "?mode=ro",
        uri=True
    )


app.register_blueprint(
    create_monitoring_blueprint(
        admin_required,
        whatsapp_monitoring_readonly_connection
    )
)


def csrf_required(fn):
    @wraps(fn)
    def inner(*a,**kw):
        if session.get('admin') and not hmac.compare_digest(request.headers.get('X-CSRF-Token',''),session.get('csrf','')):
            return error('Invalid CSRF token',403)
        return fn(*a,**kw)
    return inner

def public_row(r):
    return {k:r[k] for k in ('id','patient','doctor','date','time','status','reminded')}



def create_calendar_event(a):
    """Create a Google Calendar event for an appointment."""
    import traceback
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    print("Starting Google Calendar sync...", flush=True)

    path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    cal = os.getenv("GOOGLE_CALENDAR_ID")

    if not LIVE:
        print("Demo mode: Calendar sync skipped")
        return None

    if not path or not cal:
        print("ERROR: Google Calendar configuration missing")
        return None

    try:
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

        start = datetime.fromisoformat(
            a["date"] + "T" + a["time"]
        ).replace(tzinfo=TZ)

        end = start + timedelta(minutes=30)

        event = {
            "summary": f"Clinic Appointment - {a['doctor']}",
            "description": f"ClinicFlow Appointment #{a['id']}",
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "Asia/Kolkata"
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "Asia/Kolkata"
            }
        }

        result = service.events().insert(
            calendarId=cal,
            body=event
        ).execute()

        event_id = result.get("id")

        print("SUCCESS: Google Calendar event created!")
        print("Google Calendar Event ID:", event_id)
        print("Event Link:", result.get("htmlLink"))

        return event_id

    except Exception:
        print("ERROR: Google Calendar sync failed!")
        traceback.print_exc()
        return None


def delete_calendar_event(event_id):
    if not (LIVE and event_id and os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE') and os.getenv('GOOGLE_CALENDAR_ID')):return
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds=service_account.Credentials.from_service_account_file(os.environ['GOOGLE_SERVICE_ACCOUNT_FILE'],scopes=['https://www.googleapis.com/auth/calendar.events'])
    build('calendar','v3',credentials=creds,cache_discovery=False).events().delete(calendarId=os.environ['GOOGLE_CALENDAR_ID'],eventId=event_id).execute()

def send_whatsapp(phone, text, template=False, parameters=None):
    """In demo, log only. Live reminder uses an approved WhatsApp template."""
    # Independent outbound WhatsApp safety switch.
    # Disabled by default, including in LIVE_MODE.
    if os.getenv('WHATSAPP_OUTBOUND_ENABLED', 'false').strip().lower() != 'true':
        return {
            'status': 'disabled',
            'detail': 'Outbound WhatsApp messaging disabled by safety flag'
        }
    if not LIVE: return {'status':'demo','detail':'Simulated message; nothing sent'}
    token=os.getenv('WHATSAPP_ACCESS_TOKEN'); phone_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    if not token or not phone_id: return {'status':'skipped','detail':'WhatsApp credentials missing'}
    import requests
    payload = {'messaging_product': 'whatsapp', 'to': phone.lstrip('+')}
    if template:
        template_data = {
            'name': os.getenv(
                'WHATSAPP_TEMPLATE_NAME',
                'appointment_reminder'
            ),
            'language': {
                'code': os.getenv(
                    'WHATSAPP_TEMPLATE_LANGUAGE',
                    'en_US'
                )
            }
        }

        if parameters:
            template_data['components'] = [{
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': str(v)}
                    for v in parameters
                ]
            }]

        payload.update(
            type='template',
            template=template_data
        )

    else:
        payload.update(
            type='text',
            text={'body': text}
        )
    try:
        resp=requests.post(f'https://graph.facebook.com/v22.0/{phone_id}/messages',json=payload,
            headers={'Authorization':f'Bearer {token}'},timeout=15)
        resp.raise_for_status()
        return {'status':'sent','detail':resp.json().get('messages',[{}])[0].get('id','accepted')}
    except Exception as exc:
        logging.exception('WhatsApp delivery error')
        return {'status':'failed','detail':str(exc)[:200]}

def chatbot(message):
    q=message.strip()[:500]
    if not q:return 'Please type a question.'
    basic=('I can help with doctors, clinic hours, booking and cancellations. '
           'For an appointment, use the booking form or ask the clinic receptionist. '
           'For medical concerns, contact a qualified clinician.')
    if 'hour' in q.lower() or 'open' in q.lower():return 'Demo clinic hours: 9 AM to 6 PM.'
    if 'doctor' in q.lower():return 'Available doctors: '+', '.join(DOCTORS)

    if 'cancel' in q.lower():
        return 'To cancel an appointment, please contact the clinic staff for assistance.'
    if any(s in q.lower() for s in ('book', 'appointment', 'schedule')):
        return 'Book through the ClinicFlow form; select a doctor, date and available time.'

    key=os.getenv('OPENAI_API_KEY')
    if not (LIVE and key):return basic
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key,timeout=12)
        out=client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),max_tokens=160,
          messages=[{'role':'system','content':'You are ClinicFlow, a clinic scheduling receptionist. Only discuss clinic hours (9 AM-6 PM), doctors ('+', '.join(DOCTORS)+'), bookings and cancellations. Never provide diagnosis, medical advice or claim an appointment is booked. Do not request sensitive health information. Be concise.'},
                    {'role':'user','content':q}])
        return out.choices[0].message.content or basic
    except Exception:
        logging.exception('AI assistant failed; using fallback')
        return basic

@app.get('/')
def index():
    public_demo_mode = os.getenv(
        'PUBLIC_DEMO_MODE', 'false'
    ).lower() == 'true'

    return render_template(
        'index.html',
        doctors=DOCTORS,
        times=TIMES,
        live=LIVE,
        public_demo_mode=public_demo_mode,
        whatsapp_outbound_enabled=(
            LIVE and os.getenv(
                'WHATSAPP_OUTBOUND_ENABLED', 'false'
            ).strip().lower() == 'true'
        )
    )
@app.post('/api/chat')
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error('Expected a JSON object', 400)

    message = str(data.get('message', ''))

    if os.getenv('PUBLIC_DEMO_MODE', 'false').lower() == 'true':
        allowed = {
            'clinic hours': 'Demo clinic hours: 9 AM to 6 PM.',
            'doctors': 'Available doctors: ' + ', '.join(DOCTORS),
            'booking': 'Use the demo booking form to explore appointments.',
            'cancellation': 'Contact the demo clinic receptionist for cancellations.',
        }

        question = message.strip().lower()

        if not question:
            reply = 'Please type a question.'
        elif question in allowed:
            reply = allowed[question]
        elif any(word in question for word in (
            'hour', 'open', 'closing', 'timing'
        )):
            reply = allowed['clinic hours']
        elif any(word in question for word in (
            'doctor', 'physician'
        )):
            reply = allowed['doctors']
        elif any(word in question for word in (
            'cancel', 'reschedule'
        )):
            reply = allowed['cancellation']
        elif any(word in question for word in (
            'book', 'appointment', 'schedule'
        )):
            reply = allowed['booking']
        else:
            reply = (
                'Public demo: please ask about clinic hours, '
                'doctors, booking, or cancellation. '
                'Do not enter personal or medical information.'
            )

        return jsonify(reply=reply)

    return jsonify(reply=chatbot(message))
@app.post('/api/book')
def book():
    print("DEBUG: BOOKING API CALLED", flush=True)

    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return error('Expected a JSON object', 400)

    patient=str(d.get('patient','')).strip(); phone=str(d.get('phone','')).strip()
    doctor=str(d.get('doctor','')); day=str(d.get('date','')); time=str(d.get('time',''))

    # Public portfolio demo: reject non-demo personal details.
    if os.getenv('PUBLIC_DEMO_MODE', 'false').lower() == 'true':
        if patient != 'Demo Patient' or phone != '+12025550123':
            return error(
                'Public demo: use exactly Demo Patient '
                'and phone +12025550123.'
            )
    if not (1<=len(patient)<=100) or not re.fullmatch(r'\+?[1-9]\d{7,14}',phone):return error('Enter a valid name and international phone number (e.g. +919876543210)')
    if doctor not in DOCTORS or time not in TIMES:return error('Invalid doctor or time')
    try:
         when = datetime.fromisoformat(day + 'T' + time).replace(tzinfo=TZ)
    except ValueError:
        return error('Invalid date')

    if when <= now() or when > now() + timedelta(days=180):
        return error('Choose a future slot within 180 days')

    try:
        with conn() as c:
            if os.getenv('PUBLIC_DEMO_MODE', 'false').lower() == 'true':
                # Serialize demo booking checks and inserts.
                c.execute('BEGIN IMMEDIATE')
                active_count = c.execute(
                    "SELECT COUNT(*) FROM appointments WHERE status='Booked'"
                ).fetchone()[0]
                if active_count >= 30:
                    return error(
                        'Public demo appointment limit reached. '
                        'Please try again after the demo is reset.',
                        429
                    )

            cur = c.execute(
                'INSERT INTO appointments(patient,phone,doctor,date,time) VALUES(?,?,?,?,?)',
                (patient, phone, doctor, day, time)
            )
            aid = cur.lastrowid

    except sqlite3.IntegrityError:
        return error('That slot is already booked', 409)

    a = {
        'id': aid,
        'patient': patient,
        'phone': phone,
        'doctor': doctor,
        'date': day,
        'time': time
    }

    try:
        print("Starting Google Calendar sync...", flush=True)

        # Public portfolio demo must not invoke external Calendar integration.
        if os.getenv('PUBLIC_DEMO_MODE', 'false').lower() == 'true':
            event_id = None
        else:
            event_id = create_calendar_event(a)

        print("Google Calendar Event ID:", event_id, flush=True)

        if event_id:
            with conn() as c:
                c.execute(
                    'UPDATE appointments SET calendar_event_id=? WHERE id=?',
                    (event_id, aid)
                )

    except Exception:
        logging.exception(
            'Calendar sync failed for appointment %s', aid
        )
    # No unsolicited WhatsApp: confirmation displayed on screen; reminders require opt-in and approved template.
    return jsonify(id=aid,message=f'Appointment #{aid} booked. '+('Calendar sync attempted.' if LIVE else 'Demo mode: no external messages sent.')),201

@app.get('/admin/login')
def login_page():return render_template('login.html')
login_limiter = FailedLoginLimiter(
    max_attempts=5,
    window_seconds=15 * 60,
)

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    return response


@app.post('/admin/login')
def login():
    configured=os.getenv('ADMIN_PASSWORD','')
    if len(configured)<12:
        return error('Set ADMIN_PASSWORD to at least 12 characters in .env',503)

    client_ip = request.remote_addr or 'unknown'

    token = login_limiter.reserve_attempt(client_ip)
    if token is None:
        return error('Too many login attempts. Try again later.',429)

    try:
        password = str((request.get_json(silent=True) or {}).get('password',''))
        succeeded = hmac.compare_digest(password,configured)
    except BaseException:
        login_limiter.finish_attempt(client_ip, token, succeeded=False)
        raise

    if not login_limiter.finish_attempt(client_ip, token, succeeded):
        return error('Login attempt expired. Please try again.',429)

    if not succeeded:
        return error('Invalid password',401)

    session.clear()
    session['admin']=True
    session['csrf']=secrets.token_urlsafe(24)
    return jsonify(ok=True)
@app.get('/admin')
def admin():
    if not session.get('admin'):return redirect(url_for('login_page'))
    return render_template('admin.html',csrf=session['csrf'],live=LIVE,doctors=DOCTORS,whatsapp_outbound_enabled=(LIVE and os.getenv('WHATSAPP_OUTBOUND_ENABLED','false').strip().lower()=='true'))
@app.post('/admin/logout')
@admin_required
@csrf_required
def logout():session.clear();return jsonify(ok=True)
@app.get('/api/admin/appointments')
@admin_required
def list_appointments():
    with conn() as c:rows=c.execute('SELECT * FROM appointments ORDER BY id DESC').fetchall()
    return jsonify([dict(r) for r in rows])


@app.get('/api/admin/analytics')
@admin_required
def analytics():
    """Return filtered appointment analytics without patient details."""

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    doctor = request.args.get('doctor')

    if doctor is not None and doctor not in DOCTORS:
        return error('Invalid doctor selection.', 400)

    for name, value in (
        ('start_date', start_date),
        ('end_date', end_date)
    ):
        if value is None:
            continue

        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            return error(f'Invalid {name}. Use YYYY-MM-DD.', 400)

        try:
            date.fromisoformat(value)
        except ValueError:
            return error(f'Invalid {name}. Use a valid date.', 400)

    if start_date and end_date and start_date > end_date:
        return error('start_date must not be after end_date', 400)

    conditions = []
    params = []

    if start_date:
        conditions.append('date >= ?')
        params.append(start_date)

    if end_date:
        conditions.append('date <= ?')
        params.append(end_date)

    if doctor is not None:
        conditions.append('doctor = ?')
        params.append(doctor)

    where_sql = (
        'WHERE ' + ' AND '.join(conditions)
        if conditions else ''
    )

    with closing(conn()) as c:
        c.execute("BEGIN")

        summary = dict(c.execute(f"""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(
                    CASE WHEN status = 'Booked' THEN 1 ELSE 0 END
                ), 0) AS active,
                COALESCE(SUM(
                    CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END
                ), 0) AS cancelled
            FROM appointments
            {where_sql}
        """, params).fetchone())

        doctors = [
            dict(row) for row in c.execute(f"""
                SELECT doctor, COUNT(*) AS total
                FROM appointments
                {where_sql}
                GROUP BY doctor
                ORDER BY total DESC, doctor ASC
            """, params)
        ]

        daily = [
            dict(row) for row in c.execute(f"""
                SELECT date, COUNT(*) AS total
                FROM appointments
                {where_sql}
                GROUP BY date
                ORDER BY date ASC
            """, params)
        ]

        times = [
            dict(row) for row in c.execute(f"""
                SELECT time, COUNT(*) AS total
                FROM appointments
                {where_sql}
                GROUP BY time
                ORDER BY total DESC, time ASC
            """, params)
        ]

    total = summary['total']

    cancellation_rate = (
        round(summary['cancelled'] / total * 100, 2)
        if total else 0.0
    )

    return jsonify({
        'summary': {
            **summary,
            'cancellation_rate': cancellation_rate
        },
        'doctors': doctors,
        'daily': daily,
        'times': times
    })


@app.post('/api/admin/appointments/<int:aid>/cancel')
@admin_required
@csrf_required
def cancel(aid):
    with conn() as c:
        a=c.execute('SELECT * FROM appointments WHERE id=? AND status="Booked"',(aid,)).fetchone()
        if not a:return error('Active appointment not found',404)
        c.execute('UPDATE appointments SET status="Cancelled" WHERE id=?',(aid,))
    try:delete_calendar_event(a['calendar_event_id'])
    except Exception:logging.exception('Calendar deletion failed')
    return jsonify(ok=True)






def claim_reminder(appointment_id, reminder_type="24h", db_path=None):
    """Atomically claim a reminder without sending WhatsApp."""

    import sqlite3

    # Never allow this function to claim reminders
    # from the real database while sending is disabled.
    if db_path is None:
        return {
            "status": "disabled",
            "detail": "Live reminder claiming is not enabled"
        }

    # Only allow temporary, in-memory test databases.
    if not str(db_path).startswith("file:clinicflow_claim_test_"):
        return {
            "status": "blocked",
            "detail": "Only test databases are permitted"
        }

    try:
        with sqlite3.connect(db_path, uri=True, timeout=5) as c:
            c.execute("BEGIN IMMEDIATE")

            cursor = c.execute(
                """
                INSERT OR IGNORE INTO reminder_attempts
                    (appointment_id, reminder_type, status)
                VALUES (?, ?, 'pending')
                """,
                (appointment_id, reminder_type)
            )

            claimed = cursor.rowcount == 1

        return {
            "status": "claimed" if claimed else "duplicate",
            "appointment_id": appointment_id
        }

    except sqlite3.Error as exc:
        return {
            "status": "error",
            "detail": str(exc)
        }

def run_reminders():
    """Preview upcoming reminders without sending WhatsApp messages."""

    reminder_send_enabled = (
        os.getenv("REMINDER_SEND_ENABLED", "false")
        .strip()
        .lower() == "true"
    )

    if reminder_send_enabled:
        raise RuntimeError(
            "Live reminders are not implemented yet. "
            "Keep REMINDER_SEND_ENABLED=false."
        )

    current = now()
    end = current + timedelta(hours=24)
    results = []

    with conn() as c:
        rows = c.execute(
            """SELECT * FROM appointments
               WHERE status='Booked' AND reminded=0"""
        ).fetchall()

    for a in rows:
        try:
            when = datetime.fromisoformat(
                a['date'] + 'T' + a['time']
            ).replace(tzinfo=TZ)
        except ValueError:
            logging.warning(
                "Invalid appointment date/time for ID %s",
                a['id']
            )
            continue

        if not (current <= when <= end):
            continue

        reminder_parameters = [
            str(a['patient']),
            str(a['date']),
            str(a['time'])
        ]

        message = (
            f"Reminder for {a['patient']}: "
            f"Appointment on {a['date']} "
            f"at {a['time']}."
        )
        with conn() as c:
            plan = plan_safe_preview_from_db(
                c, a["id"], "24h"
            )

        if plan["action"] != "preview":
            logging.info(
                "Skipping reminder for appointment %s: %s",
                a["id"],
                plan["reason"]
            )
            continue
        # SAFE PREVIEW MODE:
        # Do not send WhatsApp messages.
        # Do not mark appointments as reminded.
        print(
            f"[DEMO REMINDER] Appointment #{a['id']}: {message}",
            flush=True
        )

        results.append({
            'appointment_id': a['id'],
            'status': 'simulated',
            'template': 'clinic_appointment_reminder',
            'parameters': reminder_parameters
        })

    return results

@app.post('/api/admin/reminders/run')
@admin_required
@csrf_required
def trigger_reminders():return jsonify(results=run_reminders())
@app.get('/api/admin/deliveries')
@admin_required
def deliveries():
    with conn() as c:rows=c.execute('SELECT * FROM deliveries ORDER BY id DESC LIMIT 50').fetchall()
    return jsonify([dict(r) for r in rows])

@app.get('/webhook/whatsapp')
def verify_webhook():
    if os.getenv('PUBLIC_DEMO_MODE', 'false').lower() == 'true':
        return 'Not Found', 404
    if request.args.get('hub.mode')=='subscribe' and os.getenv('WHATSAPP_VERIFY_TOKEN') and hmac.compare_digest(request.args.get('hub.verify_token',''),os.getenv('WHATSAPP_VERIFY_TOKEN')):
        return request.args.get('hub.challenge',''),200
    return 'Forbidden',403
@app.post('/webhook/whatsapp')
def whatsapp_webhook():
    if os.getenv('PUBLIC_DEMO_MODE', 'false').lower() == 'true':
        return 'Not Found', 404
    secret=os.getenv('META_APP_SECRET','')
    if not secret:return 'Webhook disabled until META_APP_SECRET configured',503
    signature=request.headers.get('X-Hub-Signature-256','')
    expected='sha256='+hmac.new(secret.encode(),request.get_data(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature,expected):return 'Invalid signature',403
    data=request.get_json(silent=True) or {}
        # Log WhatsApp delivery statuses (preview only)
    # Feature-flagged delivery-status storage.
    # Disabled by default; incoming chatbot logic is unchanged.
    status_storage_enabled = (
        os.getenv(
            "WHATSAPP_STATUS_STORAGE_ENABLED", "false"
        ).strip().lower() == "true"
    )

    store_statuses_if_enabled(
        data,
        conn,
        enabled=status_storage_enabled
    )

    status_events = extract_whatsapp_statuses(data)

    for event in status_events:
        logging.info(
            "WhatsApp status event received: status=%s",
            event["status"]
        )
    # Safely process incoming text messages.
    # Ignore malformed JSON structures without invoking the chatbot.
    entries = data.get('entry', [])
    if not isinstance(entries, list):
        entries = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        changes = entry.get('changes', [])
        if not isinstance(changes, list):
            continue

        for change in changes:
            if not isinstance(change, dict):
                continue

            value = change.get('value', {})
            if not isinstance(value, dict):
                continue

            messages = value.get('messages', [])
            if not isinstance(messages, list):
                continue

            for message in messages:
                if not isinstance(message, dict):
                    continue

                mid = message.get('id')
                sender = message.get('from')

                if not isinstance(mid, str) or not mid:
                    continue

                if not isinstance(sender, str) or not sender:
                    continue

                if message.get('type') != 'text':
                    continue

                text_data = message.get('text', {})
                if not isinstance(text_data, dict):
                    continue

                body = text_data.get('body', '')
                if not isinstance(body, str):
                    continue

                with closing(conn()) as c, c:
                    try:
                        c.execute(
                            'INSERT INTO webhook_messages(message_id) VALUES(?)',
                            (mid,)
                        )
                    except sqlite3.IntegrityError:
                        continue

                reply = chatbot(body)

                # Replies are free-form only within the
                # WhatsApp customer service window.
                outcome = send_whatsapp(sender, reply)

                with closing(conn()) as c, c:
                    c.execute(
                        'INSERT INTO deliveries(channel,status,detail) VALUES(?,?,?)',
                        (
                            'whatsapp-reply',
                            outcome['status'],
                            outcome['detail']
                        )
                    )
    return jsonify(ok=True)

scheduler=BackgroundScheduler(timezone=TZ)
if os.getenv('ENABLE_SCHEDULER','false').lower()=='true':
    scheduler.add_job(run_reminders,'interval',minutes=5,id='reminders',max_instances=1,coalesce=True)
    scheduler.start()

if __name__=='__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)
