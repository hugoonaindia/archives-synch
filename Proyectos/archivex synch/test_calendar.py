#!/usr/bin/env python3
"""
test_calendar.py — Comprueba que Google Calendar API está activa
y lista los calendarios y citas de esta semana.
"""
import subprocess, sys

for pkg in ["google-auth", "google-auth-oauthlib", "google-api-python-client"]:
    try:
        __import__(pkg.split("-")[0].replace("-","_"))
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q", "--break-system-packages"])

from pathlib import Path
from datetime import datetime, timedelta, date
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES     = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token_calendar.json"

# Auth
creds = None
if TOKEN_FILE.exists():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())

service = build("calendar", "v3", credentials=creds)

# Listar calendarios
print("\n✅ Conexión OK. Tus calendarios:\n")
calendars = service.calendarList().list().execute().get("items", [])
for c in calendars:
    print(f"   • {c['summary']}")

# Citas esta semana
today  = date.today()
monday = today - timedelta(days=today.weekday())
sunday = monday + timedelta(days=6)

events = service.events().list(
    calendarId="primary",
    timeMin=datetime.combine(monday, datetime.min.time()).isoformat() + "+02:00",
    timeMax=datetime.combine(sunday, datetime.max.time()).isoformat() + "+02:00",
    singleEvents=True,
    orderBy="startTime"
).execute().get("items", [])

print(f"\n📆 Citas esta semana ({monday.strftime('%d/%m')} – {sunday.strftime('%d/%m')}):\n")
if not events:
    print("   (ninguna)")
else:
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date"))
        dt    = datetime.fromisoformat(start) if "T" in start else datetime.strptime(start, "%Y-%m-%d")
        print(f"   • {e.get('summary','(sin título)'):<30} {dt.strftime('%a %d/%m %H:%M')}")
