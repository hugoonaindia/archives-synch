#!/usr/bin/env python3
"""
sync.py — Archivex Sync (monolito)
Transfiere la agenda de Google Calendar a Archivex Clinical.
Excluye lunes (0) y miércoles (2). Sincroniza siempre la semana actual.

Requisitos previos:
  1. python recon.py  (produce ~/.config/archivex-sync/ui_knowledge.json)
  2. ANTHROPIC_API_KEY configurada en el entorno
  3. credentials.json en el directorio actual
"""

# ─── §1 IMPORTS ──────────────────────────────────────────────────────────────
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ─── §2 CONSTANTS ────────────────────────────────────────────────────────────
CONFIG_DIR   = Path.home() / ".config" / "archivex-sync"
KNOWLEDGE    = CONFIG_DIR / "ui_knowledge.json"
TOKEN_PATH   = CONFIG_DIR / "token_calendar.json"
CREDS_PATH   = Path("credentials.json")
SCOPES       = ["https://www.googleapis.com/auth/calendar.readonly"]
MODEL_VERIFY = os.getenv("ARCHIVEX_VERIFY_MODEL", "claude-haiku-4-5")
SKIP_DAYS    = {0, 2}   # Monday=0, Wednesday=2
LOG_PATH     = CONFIG_DIR / "sync.log"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─── §3 TYPES ────────────────────────────────────────────────────────────────
@dataclass
class Appointment:
    patient:    str
    date:       date
    start_time: str
    end_time:   str
    day_offset: int    # 0=Mon … 6=Sun
    hour:       int
    minute:     int


# ─── §4 GOOGLE CALENDAR ──────────────────────────────────────────────────────
def get_calendar_service():
    """Autentica con Google Calendar vía OAuth2 y devuelve el servicio."""
    creds: Optional[Credentials] = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=creds)


def get_week_appointments(service, monday: date) -> list[Appointment]:
    """
    Devuelve las citas de la semana que empieza en `monday`.
    Excluye lunes (weekday 0) y miércoles (weekday 2).
    Excluye eventos de todo el día.
    """
    sunday = monday + timedelta(days=6)
    time_min = datetime(monday.year, monday.month, monday.day,
                        tzinfo=timezone.utc).isoformat()
    time_max = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59,
                        tzinfo=timezone.utc).isoformat()

    result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    appointments: list[Appointment] = []
    for item in result.get("items", []):
        start = item["start"]
        end   = item["end"]
        if "dateTime" not in start:               # all-day event → skip
            continue
        dt_start = datetime.fromisoformat(start["dateTime"])
        dt_end   = datetime.fromisoformat(end["dateTime"])
        if dt_start.weekday() in SKIP_DAYS:       # Mon or Wed → skip
            continue
        offset = (dt_start.date() - monday).days
        appointments.append(Appointment(
            patient    = item.get("summary", ""),
            date       = dt_start.date(),
            start_time = dt_start.strftime("%H:%M"),
            end_time   = dt_end.strftime("%H:%M"),
            day_offset = offset,
            hour       = dt_start.hour,
            minute     = dt_start.minute,
        ))
    return appointments


# ─── §5 KNOWLEDGE BASE ───────────────────────────────────────────────────────
# (implemented in Task 3)

# ─── §6 ARCHIVEX WINDOW ──────────────────────────────────────────────────────
# (implemented in Task 4)

# ─── §7 VERIFIER ─────────────────────────────────────────────────────────────
# (implemented in Task 5)

# ─── §8 APPOINTMENT PROCESSOR ────────────────────────────────────────────────
# (implemented in Task 6)

# ─── §9 NAVIGATION ───────────────────────────────────────────────────────────
# (implemented in Task 7)

# ─── §10 CONFLICT HANDLING + MAIN ────────────────────────────────────────────
# (implemented in Task 8)
