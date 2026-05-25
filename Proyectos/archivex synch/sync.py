#!/usr/bin/env python3
"""
sync.py — Archivex Sync (monolito)
Transfiere la agenda de Google Calendar a Archivex Clinical.
Excluye lunes (0) y miércoles (2). Sincroniza siempre la semana actual.

Requisitos previos:
  1. python recon.py  (produce ~/.config/archivex-sync/ui_knowledge.json)
  2. OPENROUTER_API_KEY configurada en el entorno
  3. credentials.json en el directorio actual
"""

# ─── §1 IMPORTS ──────────────────────────────────────────────────────────────
from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

import pyautogui
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from openai import OpenAI

# ─── §2 CONSTANTS ────────────────────────────────────────────────────────────
CONFIG_DIR   = Path.home() / ".config" / "archivex-sync"
KNOWLEDGE    = CONFIG_DIR / "ui_knowledge.json"
TOKEN_PATH   = CONFIG_DIR / "token_calendar.json"
CREDS_PATH   = Path("credentials.json")
SCOPES       = ["https://www.googleapis.com/auth/calendar.readonly"]
MODEL_VERIFY     = os.getenv(
    "ARCHIVEX_VERIFY_MODEL", "nvidia/nemotron-nano-12b-v2-vl:free"
)
OPENROUTER_URL   = "https://openrouter.ai/api/v1"
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
_REQUIRED_KEYS       = {"version", "grid", "elements", "visual_signatures"}
_REQUIRED_GRID       = {"start_hour", "end_hour", "col_offsets_pct",
                        "first_row_y_pct", "last_row_y_pct"}
_REQUIRED_ELEMENTS   = {"nav_prev_pct", "nav_next_pct", "patient_search_pct",
                        "first_result_pct", "save_btn_pct"}


def validate_knowledge(kb: dict) -> None:
    """Raises KeyError if any required key is missing from ui_knowledge.json."""
    for k in _REQUIRED_KEYS:
        if k not in kb:
            raise KeyError(f"ui_knowledge.json: falta la clave '{k}'")
    for k in _REQUIRED_GRID:
        if k not in kb["grid"]:
            raise KeyError(f"ui_knowledge.json grid: falta '{k}'")
    for k in _REQUIRED_ELEMENTS:
        if k not in kb["elements"]:
            raise KeyError(f"ui_knowledge.json elements: falta '{k}'")


def load_knowledge() -> dict:
    """Carga ui_knowledge.json. Aborta con mensaje claro si no existe."""
    if not KNOWLEDGE.exists():
        sys.exit(
            f"❌  {KNOWLEDGE} no encontrado.\n"
            "   Ejecuta primero:  python recon.py"
        )
    kb = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
    validate_knowledge(kb)
    return kb


def abs_coords(pct_x: float, pct_y: float,
               wx: int, wy: int, ww: int, wh: int) -> tuple[int, int]:
    """Convierte coordenadas relativas (0-1) a píxeles absolutos."""
    return int(wx + pct_x * ww), int(wy + pct_y * wh)


def slot_coords(day_offset: int, hour: int, minute: int,
                kb: dict, wx: int, wy: int, ww: int, wh: int) -> tuple[int, int]:
    """Calcula las coordenadas absolutas del slot del calendario."""
    g = kb["grid"]
    x_pct = g["col_offsets_pct"][day_offset]
    total_hours = g["end_hour"] - g["start_hour"]
    row_span    = g["last_row_y_pct"] - g["first_row_y_pct"]
    y_pct = g["first_row_y_pct"] + (
        (hour - g["start_hour"] + minute / 60.0) / total_hours * row_span
    )
    return abs_coords(x_pct, y_pct, wx, wy, ww, wh)

# ─── §6 ARCHIVEX WINDOW ──────────────────────────────────────────────────────
_APPLESCRIPT_BOUNDS = """\
tell application "System Events"
    tell process "Archivex Clinical"
        set b to position of window 1 & size of window 1
        return (item 1 of b as text) & "," & (item 2 of b as text) & "," & \
               (item 3 of b as text) & "," & (item 4 of b as text)
    end tell
end tell
"""


def get_window_bounds() -> tuple[int, int, int, int]:
    """
    Devuelve (x, y, width, height) de la ventana de Archivex Clinical.
    Lanza RuntimeError si Archivex no está abierto.
    """
    result = subprocess.run(
        ["osascript", "-e", _APPLESCRIPT_BOUNDS],
        capture_output=True, text=True,
    )
    raw = result.stdout.strip()
    if not raw:
        raise RuntimeError(
            "Archivex Clinical no está abierto o no es visible. "
            "Ábrelo y ponlo en vista semanal antes de ejecutar sync.py."
        )
    parts = [int(v) for v in raw.split(",")]
    return parts[0], parts[1], parts[2], parts[3]


# ─── §7 VERIFIER (OpenRouter vision model) ───────────────────────────────────
def _screenshot_b64() -> str:
    """Captura la pantalla y devuelve PNG en base64."""
    buf = BytesIO()
    pyautogui.screenshot().save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _build_system_prompt(signatures: dict) -> str:
    lines = [
        "Eres un asistente de verificación para Archivex Clinical (macOS).",
        "Recibirás un screenshot y una pregunta sobre el estado de la UI.",
        "Responde ÚNICAMENTE con la palabra indicada, nada más.",
        "",
        "Descripciones visuales de los estados de la app:",
    ]
    for key, desc in signatures.items():
        lines.append(f"  - {key}: {desc}")
    return "\n".join(lines)


def _ask_llm(question: str, signatures: dict) -> str:
    """Envía screenshot + pregunta al modelo de visión via OpenRouter."""
    client = OpenAI(
        base_url=OPENROUTER_URL,
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    resp = client.chat.completions.create(
        model=MODEL_VERIFY,
        max_tokens=10,
        messages=[
            {"role": "system", "content": _build_system_prompt(signatures)},
            {"role": "user", "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{_screenshot_b64()}"}},
                {"type": "text", "text": question},
            ]},
        ],
    )
    return resp.choices[0].message.content.strip().lower()


def verify_slot_empty(signatures: dict, day_offset: int, hour: int) -> str:
    """Devuelve: 'empty' | 'occupied' | 'uncertain'"""
    days_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    question = (
        f"¿El slot del calendario del {days_es[day_offset]} a las {hour:02d}:00 "
        "está vacío o tiene una cita?\n"
        "Responde ÚNICAMENTE con: empty (vacío) u occupied (tiene cita)."
    )
    raw = _ask_llm(question, signatures)
    if "empty" in raw:
        return "empty"
    if "occupied" in raw:
        return "occupied"
    return "uncertain"


def verify_form_open(signatures: dict) -> bool:
    """Verifica si el formulario de nueva cita está abierto."""
    raw = _ask_llm(
        "¿Está visible el formulario modal de nueva cita con el campo de búsqueda?\n"
        "Responde ÚNICAMENTE con: yes o no.",
        signatures,
    )
    return "yes" in raw


def verify_saved(signatures: dict) -> bool:
    """Verifica si la cita fue guardada exitosamente."""
    raw = _ask_llm(
        "¿Se cerró el formulario y la nueva cita es visible en el calendario?\n"
        "Responde ÚNICAMENTE con: yes o no.",
        signatures,
    )
    return "yes" in raw


# ─── §8 APPOINTMENT PROCESSOR ────────────────────────────────────────────────
def open_slot(x: int, y: int) -> None:
    """Doble clic en el slot del calendario para abrir el formulario."""
    pyautogui.doubleClick(x, y)
    time.sleep(2.0)


def fill_patient(patient: str, kb: dict,
                 wx: int, wy: int, ww: int, wh: int) -> None:
    """Clic en búsqueda, pega nombre via pbcopy, selecciona primer resultado."""
    sx, sy = abs_coords(
        kb["elements"]["patient_search_pct"]["x"],
        kb["elements"]["patient_search_pct"]["y"],
        wx, wy, ww, wh,
    )
    pyautogui.click(sx, sy)
    time.sleep(0.4)
    subprocess.run(["pbcopy"], input=patient.encode("utf-8"), check=True)
    pyautogui.hotkey("command", "a")
    time.sleep(0.1)
    pyautogui.hotkey("command", "v")
    time.sleep(2.5)
    rx, ry = abs_coords(
        kb["elements"]["first_result_pct"]["x"],
        kb["elements"]["first_result_pct"]["y"],
        wx, wy, ww, wh,
    )
    pyautogui.click(rx, ry)
    time.sleep(0.8)


def save_appointment(kb: dict, wx: int, wy: int, ww: int, wh: int) -> None:
    """Hace clic en el botón guardar/crear cita."""
    bx, by = abs_coords(
        kb["elements"]["save_btn_pct"]["x"],
        kb["elements"]["save_btn_pct"]["y"],
        wx, wy, ww, wh,
    )
    pyautogui.click(bx, by)
    time.sleep(1.5)


# ─── §9 NAVIGATION ───────────────────────────────────────────────────────────
def detect_displayed_monday() -> Optional[date]:
    """Pregunta al modelo de visión qué lunes muestra el calendario. Devuelve date o None."""
    client = OpenAI(
        base_url=OPENROUTER_URL,
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    resp = client.chat.completions.create(
        model=MODEL_VERIFY,
        max_tokens=32,
        messages=[{"role": "user", "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{_screenshot_b64()}"}},
            {"type": "text", "text": (
                "Mira este calendario semanal de Archivex Clinical. "
                "¿Qué fecha tiene el lunes (primer día) de la semana visible? "
                'Responde ÚNICAMENTE con JSON: {"date": "YYYY-MM-DD"} '
                'o {"date": null} si no puedes determinarlo.'
            )},
        ]}],
    )
    raw = resp.choices[0].message.content.strip()
    try:
        d = json.loads(raw)
        if d.get("date"):
            return date.fromisoformat(d["date"])
    except Exception:
        pass
    return None


def navigate_to_week(target_monday: date, kb: dict,
                     wx: int, wy: int, ww: int, wh: int) -> None:
    """Navega Archivex a la semana de target_monday."""
    current = detect_displayed_monday()
    if current is None:
        log.warning("No se pudo detectar la semana actual — omitiendo navegación")
        return
    delta = (target_monday - current).days // 7
    if delta == 0:
        return
    btn = kb["elements"]["nav_next_pct"] if delta > 0 else kb["elements"]["nav_prev_pct"]
    bx, by = abs_coords(btn["x"], btn["y"], wx, wy, ww, wh)
    for _ in range(abs(delta)):
        pyautogui.click(bx, by)
        time.sleep(0.8)


# ─── §10 CONFLICT HANDLING ───────────────────────────────────────────────────
class StopSync(Exception):
    """Raised when the user chooses to stop the entire sync."""


def ask_conflict_action(appt: Appointment) -> str:
    """Pregunta al usuario qué hacer. Devuelve: 'crear' | 'saltar' | 'parar'"""
    print(f"\n  ⚠️  CONFLICTO: {appt.patient} — "
          f"{appt.date.strftime('%a %d/%m')} {appt.start_time}")
    print("     El slot parece ocupado en Archivex.")
    print("     [C] Crear igualmente   [S] Saltar   [P] Parar todo")
    while True:
        resp = input("     ¿Qué hago? (c/s/p): ").strip().lower()
        if resp == "c":
            return "crear"
        if resp == "s":
            return "saltar"
        if resp == "p":
            return "parar"
        print("     Responde c, s o p.")


def process_appointment(appt: Appointment, kb: dict,
                        wx: int, wy: int, ww: int, wh: int) -> str:
    """
    Crea una cita en Archivex. Devuelve: 'creada' | 'saltada'
    Lanza StopSync si el usuario elige parar.
    """
    sigs = kb["visual_signatures"]

    status = verify_slot_empty(sigs, day_offset=appt.day_offset, hour=appt.hour)
    if status != "empty":
        accion = ask_conflict_action(appt)
        if accion == "parar":
            raise StopSync()
        if accion == "saltar":
            log.info("SALTADA  | %s | %s %s | slot ocupado",
                     appt.patient, appt.date.strftime("%d/%m/%Y"), appt.start_time)
            return "saltada"

    sx, sy = slot_coords(appt.day_offset, appt.hour, appt.minute, kb, wx, wy, ww, wh)
    open_slot(sx, sy)

    if not verify_form_open(sigs):
        open_slot(sx, sy)
        if not verify_form_open(sigs):
            log.warning("SALTADA  | %s | %s %s | formulario no se abrió",
                        appt.patient, appt.date.strftime("%d/%m/%Y"), appt.start_time)
            print(f"  ⚠️  Formulario no se abrió para {appt.patient}. Saltando.")
            return "saltada"

    fill_patient(appt.patient, kb, wx, wy, ww, wh)
    save_appointment(kb, wx, wy, ww, wh)

    if not verify_saved(sigs):
        print(f"  ⚠️  No se pudo confirmar que la cita de {appt.patient} fue guardada.")

    log.info("CREADA   | %s | %s %s-%s",
             appt.patient, appt.date.strftime("%d/%m/%Y"),
             appt.start_time, appt.end_time)
    return "creada"


# ─── §11 MAIN ────────────────────────────────────────────────────────────────
def main() -> None:
    print("🗓  Archivex Sync")
    print("─" * 40)

    kb = load_knowledge()
    print(f"✅  Knowledge base cargado ({KNOWLEDGE})")

    try:
        wx, wy, ww, wh = get_window_bounds()
    except RuntimeError as e:
        sys.exit(f"❌  {e}")
    print(f"✅  Archivex detectado: {ww}×{wh} en ({wx},{wy})")

    service = get_calendar_service()
    monday = date.today() - timedelta(days=date.today().weekday())
    print(f"📅  Semana del {monday.strftime('%d/%m/%Y')}")

    appointments = get_week_appointments(service, monday)
    print(f"📋  {len(appointments)} cita(s) a procesar (lunes y miércoles excluidos)")

    if not appointments:
        print("   Nada que sincronizar.")
        return

    navigate_to_week(monday, kb, wx, wy, ww, wh)

    creadas = saltadas = 0
    try:
        for appt in appointments:
            print(f"\n  ▶  {appt.patient}  {appt.date.strftime('%a %d/%m')} "
                  f"{appt.start_time}–{appt.end_time}", end="  ", flush=True)
            resultado = process_appointment(appt, kb, wx, wy, ww, wh)
            if resultado == "creada":
                creadas += 1
                print("✅")
            else:
                saltadas += 1
                print("⏭")
    except StopSync:
        print("\n⛔  Parado por el usuario.")

    print("\n" + "─" * 40)
    print(f"✅  Creadas: {creadas}   ⏭  Saltadas: {saltadas}")


if __name__ == "__main__":
    main()
