#!/usr/bin/env python3
"""
sync.py — Archivex Sync (monolito)
Transfiere la agenda de Google Calendar a Archivex Clinical.
Sincroniza la semana actual; los días a procesar se eligen al arrancar.

Requisitos previos:
  1. ~/.config/archivex-sync/ui_knowledge.json  (coordenadas de la UI)
  2. credentials.json en el directorio actual   (Google Calendar OAuth)
  3. Archivex abierto en vista semanal mostrando la semana actual
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
pyautogui.PAUSE = 0.5   # pausa global entre cualquier acción de pyautogui

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
LOG_PATH     = CONFIG_DIR / "sync.log"

# ─── Tiempos de espera (segundos) — fiabilidad > velocidad ───────────────────
T_AFTER_OPEN_SLOT   = 5.0   # tras click en slot → form 'Nueva cita' renderizado
T_AFTER_FIELD_CLICK = 1.0   # tras click/tripleClick en campo → cursor activo
T_AFTER_TYPE        = 1.2   # tras pegar valor (deja que la app procese)
T_AFTER_SEARCH      = 5.0   # tras pegar nombre paciente → resultados visibles
T_AFTER_PICK        = 2.5   # tras click en el primer resultado
T_AFTER_SAVE        = 4.0   # tras '+ Crear cita' → diálogo 'Cita creada'
T_AFTER_CONFIRM     = 3.0   # tras 'Aceptar' → vuelta al calendario
T_AFTER_SCROLL      = 2.5   # tras hacer scroll en el calendario (snap visual)

# ─── Scroll del calendario ───────────────────────────────────────────────────
# Calibrado empíricamente en 2026-05-26 con pyautogui en macOS:
# 12 ticks de scroll = 1 hora; el calendario hace snap limpio a la fila.
# Si la hora pre-rellenada se desvía, ajustar SCROLL_PER_HOUR.
SCROLL_PER_HOUR = 12
SCROLL_RESET    = 200   # ticks de scroll hacia arriba para garantizar 08:00 al top

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
    El filtrado por día se aplica más tarde según la selección del usuario.
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
_REQUIRED_ELEMENTS   = {"patient_search_pct", "first_result_pct", "save_btn_pct",
                        "fecha_field_pct", "hora_inicio_pct", "hora_fin_pct",
                        "confirm_btn_pct"}


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
    Intenta primero AppleScript; si falla (sin permisos), usa Quartz CGWindowList.
    """
    result = subprocess.run(
        ["osascript", "-e", _APPLESCRIPT_BOUNDS],
        capture_output=True, text=True,
    )
    raw = result.stdout.strip()
    if raw:
        parts = [int(v) for v in raw.split(",")]
        return parts[0], parts[1], parts[2], parts[3]

    # Fallback: Quartz CGWindowList (no requiere permisos de accesibilidad)
    try:
        import Quartz
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly
            | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )
        for win in windows:
            if "archivex" in str(win.get("kCGWindowOwnerName", "")).lower():
                b = win.get("kCGWindowBounds", {})
                x, y = int(b.get("X", 0)), int(b.get("Y", 0))
                w, h = int(b.get("Width", 0)), int(b.get("Height", 0))
                if w > 100 and h > 100:
                    return x, y, w, h
    except Exception as e:
        log.debug("Quartz window lookup failed: %s", e)

    raise RuntimeError(
        "Archivex Clinical no está abierto o no es visible. "
        "Ábrelo y ponlo en vista semanal antes de ejecutar sync.py."
    )


def focus_archivex() -> None:
    """Trae Archivex Clinical al frente. Imprescindible antes de cada acción
    automatizada para que los clics/scrolls vayan a su ventana (y no al Terminal)."""
    subprocess.run(
        ["open", "-a", "Archivex Clinical"],
        capture_output=True,
    )
    time.sleep(0.6)   # tiempo para que la app reciba foco


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
    """Verificación visual deshabilitada — devuelve siempre cadena vacía."""
    return ""


def verify_slot_empty(signatures: dict, day_offset: int, hour: int) -> str:
    """Devuelve: 'empty' | 'occupied' | 'uncertain'.
    Si el LLM no responde, asume 'empty' para no bloquear la sincronización."""
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
    return "empty"   # sin respuesta del modelo → procede sin bloquear


def verify_form_open(signatures: dict) -> bool:
    """Verifica si el formulario de nueva cita está abierto.
    Si el LLM no responde, asume True (el rightClick es fiable)."""
    raw = _ask_llm(
        "¿Está visible el formulario modal de nueva cita con el campo de búsqueda?\n"
        "Responde ÚNICAMENTE con: yes o no.",
        signatures,
    )
    if not raw:
        return True
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
def click_slot(day_offset: int, hour: int, kb: dict,
               wx: int, wy: int, ww: int, wh: int) -> None:
    """
    Hace scroll del calendario para que `hour` quede en la primera fila visible,
    y a continuación hace click izquierdo en la columna correspondiente al día.
    Archivex abre 'Nueva cita' con la fecha y la hora pre-rellenadas.

    El scroll se hace en trozos pequeños con pausas, para evitar overshoot
    o que el snap visual no haya terminado al hacer el siguiente click.
    """
    cx, cy = wx + ww // 2, wy + wh // 2

    # 1. Reset: scroll arriba en trozos para garantizar 08:00 al top
    remaining = SCROLL_RESET
    while remaining > 0:
        chunk = min(40, remaining)
        pyautogui.scroll(chunk, x=cx, y=cy)
        remaining -= chunk
        time.sleep(0.4)
    time.sleep(T_AFTER_SCROLL)   # pausa final para que el snap se complete

    # 2. Scroll abajo (hour - 8) horas, también en trozos
    scroll_down_total = max(0, (hour - 8) * SCROLL_PER_HOUR)
    remaining = scroll_down_total
    while remaining > 0:
        chunk = min(24, remaining)   # ~2 horas por trozo
        pyautogui.scroll(-chunk, x=cx, y=cy)
        remaining -= chunk
        time.sleep(0.4)
    if scroll_down_total > 0:
        time.sleep(T_AFTER_SCROLL)   # snap visual antes del click

    # 3. Mueve el cursor a la posición y click izquierdo
    x_pct = kb["grid"]["col_offsets_pct"][day_offset]
    y_pct = kb["grid"]["first_row_y_pct"] + 0.01   # cae dentro de la fila HH:00
    sx, sy = abs_coords(x_pct, y_pct, wx, wy, ww, wh)
    log.info("  click_slot day=%d hour=%d → (%d, %d)  [scroll=%d ticks]",
             day_offset, hour, sx, sy, scroll_down_total)
    pyautogui.moveTo(sx, sy, duration=0.3)   # movimiento visible y suave
    time.sleep(0.4)
    pyautogui.click(sx, sy)
    time.sleep(T_AFTER_OPEN_SLOT)


def fill_form_fields(date_str: str, start_time: str, end_time: str,
                     kb: dict, wx: int, wy: int, ww: int, wh: int) -> None:
    """
    Rellena Fecha, Hora de inicio y Hora de fin en el formulario 'Nueva cita'.
    Usa tripleClick (selecciona todo el contenido del campo) + paste por
    portapapeles (Cmd+V) — más fiable que `typewrite` porque el picker no
    intercepta caracteres uno a uno.

    date_str  : "DD/MM/YYYY"
    start_time: "HH:MM"
    end_time  : "HH:MM"
    """
    elems = kb["elements"]

    def _set_field(pct_key: str, value: str) -> None:
        fx, fy = abs_coords(elems[pct_key]["x"], elems[pct_key]["y"], wx, wy, ww, wh)
        pyautogui.tripleClick(fx, fy)              # selecciona contenido actual
        time.sleep(T_AFTER_FIELD_CLICK)
        subprocess.run(["pbcopy"], input=value.encode("utf-8"), check=True)
        pyautogui.hotkey("command", "v")           # reemplaza con el nuevo valor
        time.sleep(T_AFTER_TYPE)

    _set_field("fecha_field_pct",  date_str)
    _set_field("hora_inicio_pct",  start_time)
    _set_field("hora_fin_pct",     end_time)


def fill_patient(patient: str, kb: dict,
                 wx: int, wy: int, ww: int, wh: int) -> None:
    """Clic en búsqueda, pega nombre via pbcopy, selecciona primer resultado."""
    sx, sy = abs_coords(
        kb["elements"]["patient_search_pct"]["x"],
        kb["elements"]["patient_search_pct"]["y"],
        wx, wy, ww, wh,
    )
    pyautogui.moveTo(sx, sy, duration=0.3)
    time.sleep(0.4)
    pyautogui.tripleClick(sx, sy)
    time.sleep(T_AFTER_FIELD_CLICK)
    subprocess.run(["pbcopy"], input=patient.encode("utf-8"), check=True)
    pyautogui.hotkey("command", "v")
    time.sleep(T_AFTER_SEARCH)
    rx, ry = abs_coords(
        kb["elements"]["first_result_pct"]["x"],
        kb["elements"]["first_result_pct"]["y"],
        wx, wy, ww, wh,
    )
    pyautogui.moveTo(rx, ry, duration=0.3)
    time.sleep(0.4)
    pyautogui.click(rx, ry)
    time.sleep(T_AFTER_PICK)


def save_appointment(kb: dict, wx: int, wy: int, ww: int, wh: int) -> None:
    """Hace clic en '+ Crear cita' y luego acepta el diálogo 'Cita creada'."""
    bx, by = abs_coords(
        kb["elements"]["save_btn_pct"]["x"],
        kb["elements"]["save_btn_pct"]["y"],
        wx, wy, ww, wh,
    )
    log.info("  save_appointment click '+ Crear cita' → (%d, %d)", bx, by)
    pyautogui.moveTo(bx, by, duration=0.3)
    time.sleep(0.4)
    pyautogui.click(bx, by)
    time.sleep(T_AFTER_SAVE)

    # Aceptar el modal de confirmación "Cita creada"
    confirm = kb["elements"].get("confirm_btn_pct")
    if confirm:
        cx, cy = abs_coords(confirm["x"], confirm["y"], wx, wy, ww, wh)
        log.info("  confirm click 'Aceptar' → (%d, %d)", cx, cy)
        pyautogui.moveTo(cx, cy, duration=0.3)
        time.sleep(0.4)
        pyautogui.click(cx, cy)
        time.sleep(T_AFTER_CONFIRM)


# ─── §9 NAVEGACIÓN ENTRE SEMANAS ─────────────────────────────────────────────
# sync.py solo opera sobre la semana actual: el usuario debe asegurarse de que
# Archivex muestre esa semana antes de arrancar. No se navega automáticamente.


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

    # Asegurar que Archivex tiene el foco (no el Terminal u otra app)
    focus_archivex()

    # Re-fetch bounds: la ventana puede haberse movido entre citas
    try:
        wx, wy, ww, wh = get_window_bounds()
    except RuntimeError as e:
        log.warning("No se pudo refrescar bounds de la ventana: %s", e)

    status = verify_slot_empty(sigs, day_offset=appt.day_offset, hour=appt.hour)
    if status != "empty":
        accion = ask_conflict_action(appt)
        if accion == "parar":
            raise StopSync()
        if accion == "saltar":
            log.info("SALTADA  | %s | %s %s | slot ocupado",
                     appt.patient, appt.date.strftime("%d/%m/%Y"), appt.start_time)
            return "saltada"

    # Scroll + click en el slot del día/hora correctos: Archivex pre-rellena fecha y hora
    click_slot(appt.day_offset, appt.hour, kb, wx, wy, ww, wh)

    if not verify_form_open(sigs):
        click_slot(appt.day_offset, appt.hour, kb, wx, wy, ww, wh)
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


# ─── §10 CONFIGURACIÓN DE DÍAS ───────────────────────────────────────────────
def ask_sync_days() -> set[int]:
    """
    Muestra los 7 días de la semana y deja al usuario elegir cuáles sincronizar.
    El default (Enter vacío) es Martes, Jueves, Viernes.
    Devuelve set de weekdays (0=lun … 6=dom).
    """
    _NOMBRES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    _DEFAULT = {1, 3, 4}   # martes, jueves, viernes

    while True:
        print("\n¿Qué días quieres sincronizar?")
        print("  (Enter para usar el predeterminado marcado con ✓)\n")
        for i, nombre in enumerate(_NOMBRES):
            marca = " ✓" if i in _DEFAULT else ""
            print(f"  {i + 1}  {nombre}{marca}")
        print()
        raw = input("Días [1-7 separados por espacio, o Enter]: ").strip()

        if not raw:
            return _DEFAULT

        try:
            seleccion = {int(d) - 1 for d in raw.split()}
            if seleccion and all(0 <= d <= 6 for d in seleccion):
                return seleccion
        except ValueError:
            pass
        print("  ⚠  Ingresa números del 1 al 7 separados por espacio (ej: 2 4 5)")


# ─── §11 MAIN ────────────────────────────────────────────────────────────────
def main() -> None:
    print("🗓  Archivex Sync")
    print("─" * 40)

    kb = load_knowledge()
    print(f"✅  Knowledge base cargado ({KNOWLEDGE})")

    # Preguntar qué días sincronizar
    sync_days = ask_sync_days()
    print(f"✅  Días a sincronizar: {sorted(sync_days)}")

    try:
        wx, wy, ww, wh = get_window_bounds()
    except RuntimeError as e:
        sys.exit(f"❌  {e}")
    print(f"✅  Archivex detectado: {ww}×{wh} en ({wx},{wy})")

    service = get_calendar_service()
    monday = date.today() - timedelta(days=date.today().weekday())
    sunday = monday + timedelta(days=6)
    print(f"📅  Semana actual: {monday.strftime('%d/%m')} – {sunday.strftime('%d/%m/%Y')}")

    appointments = get_week_appointments(service, monday)
    appointments = [a for a in appointments if a.day_offset in sync_days]
    print(f"📋  {len(appointments)} cita(s) a procesar")

    if not appointments:
        print("   Nada que sincronizar.")
        return

    print()
    print("⚠️   Asegúrate de que Archivex muestra esta semana en la vista semanal.")
    print("    Si la semana mostrada es otra, ajústala manualmente antes de continuar.")
    input("    Pulsa Enter cuando estés listo (Ctrl+C para cancelar)... ")

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
