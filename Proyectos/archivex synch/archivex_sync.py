#!/usr/bin/env python3
"""
archivex_sync.py
─────────────────────────────────────────────────────────────────────────────
Sincroniza las citas de Google Calendar con Archivex Clinical (Mac).
Lee los eventos de la semana actual y los introduce automáticamente
en la app usando automatización de ratón/teclado.

USO:
    pip install -r requirements.txt
    python archivex_sync.py

REQUISITOS:
    - credentials.json en la misma carpeta (Google Cloud OAuth)
    - Archivex Clinical abierto y en vista SEMANAL antes de ejecutar
    - Permiso de Accesibilidad para Terminal:
      Preferencias del Sistema → Privacidad y Seguridad → Accesibilidad → añadir Terminal
"""

# ── Imports ───────────────────────────────────────────────────────────────────
import json
import logging
import subprocess as sp
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pyautogui
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── CONFIG ────────────────────────────────────────────────────────────────────

SCOPES_CAL = ["https://www.googleapis.com/auth/calendar.readonly"]
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = Path.home() / ".config" / "archivex-sync"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CREDS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token_archivex.json"
LOG_FILE   = CONFIG_DIR / "archivex_sync.log"
CAL_FILE   = CONFIG_DIR / "cal_config.json"

APP_NAME = "Archivex Clinical"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

pyautogui.PAUSE    = 0.4
pyautogui.FAILSAFE = True

# ── CALIBRACIÓN — valores por defecto ─────────────────────────────────────────

CAL_DEFAULTS: dict = {
    "grid_top_px":     135,
    "grid_bottom_px":  145,
    "time_col_px":     65,
    "grid_start_h":    8,
    "grid_end_h":      20,
    "search_box_x":    0.245,
    "search_box_y":    0.525,
    "first_result_dy": 85,
    "crear_btn_x":     0.75,
    "crear_btn_y":     0.87,
    "retroceder_x":    0.05,
    "avanzar_x":       0.95,
    "nav_btn_y":       0.88,
}


def load_cal() -> dict:
    """Carga calibración guardada; si no existe usa defaults."""
    if CAL_FILE.exists():
        saved = json.loads(CAL_FILE.read_text())
        # Fusionar con defaults por si faltan claves nuevas
        return {**CAL_DEFAULTS, **{k: v for k, v in saved.items() if not k.startswith("_")}}
    return dict(CAL_DEFAULTS)


CAL: dict = load_cal()


# ── CALIBRACIÓN INTERACTIVA ───────────────────────────────────────────────────

def _wait_for_position(prompt: str, countdown: int = 3) -> tuple[int, int]:
    """Cuenta atrás y captura la posición del ratón al llegar a 0."""
    print(f"\n  📍 {prompt}")
    print(f"     Posiciona el ratón y NO LO MUEVAS. Capturando en {countdown}s...")
    for i in range(countdown, 0, -1):
        x, y = pyautogui.position()
        print(f"     [{i}] Posición actual: ({x}, {y})   ", end="\r")
        time.sleep(1)
    x, y = pyautogui.position()
    print(f"     ✅ Capturado: ({x}, {y})                          ")
    return x, y


def run_calibration() -> None:
    """
    Guía al usuario por 6 puntos de la interfaz de Archivex,
    calcula los valores CAL y los guarda en cal_config.json.
    """
    print("\n" + "═" * 62)
    print("   Calibración de pantalla — Archivex Sync")
    print("═" * 62)
    print("""
Para cada punto posiciona el ratón EXACTAMENTE sobre el lugar
indicado y espera 3 segundos sin moverlo.

⚠️  Requisitos:
   • Archivex Clinical abierto en VISTA SEMANAL
   • La semana completa debe estar visible
""")
    input("  Presiona ENTER cuando Archivex esté visible y listo... ")

    # Obtener bounds de la ventana
    print("\n🔍 Detectando ventana de Archivex...")
    bounds = get_window_bounds(interactive=False)
    if bounds:
        wx, wy, ww, wh = bounds
        print(f"   ✅ Ventana: {ww}×{wh} en ({wx},{wy})")
    else:
        print("   ⚠️  No se detectó automáticamente.")
        print("   Haz clic en la ventana de Archivex y pulsa ENTER.")
        input()
        sw, sh = pyautogui.size()
        wx, wy, ww, wh = 0, 0, sw, sh

    # ── 6 puntos de calibración ──────────────────────────────────────────────

    print("\n─── PASO 1/6 ──────────────────────────────────────────────")
    print("    Esquina SUPERIOR-IZQUIERDA de la rejilla del calendario")
    print("    (primera celda del Lunes, justo tras la columna de horas)")
    gx1, gy1 = _wait_for_position("Esquina SUPERIOR-IZQUIERDA de la rejilla")

    print("\n─── PASO 2/6 ──────────────────────────────────────────────")
    print("    Esquina INFERIOR-DERECHA de la rejilla")
    print("    (última celda del Domingo, fila inferior)")
    gx2, gy2 = _wait_for_position("Esquina INFERIOR-DERECHA de la rejilla")

    print("\n─── PASO 3/6 ──────────────────────────────────────────────")
    print("    PRIMERA franja horaria visible (ej. 08:00)")
    print("    Apunta al centro vertical de esa franja")
    _, gy_start = _wait_for_position("Centro de la PRIMERA franja horaria (08:00)")
    hour_start = int(input("  ¿Qué hora indica esa franja? (ej: 8): ").strip() or "8")

    print("\n─── PASO 4/6 ──────────────────────────────────────────────")
    print("    ÚLTIMA franja horaria visible (ej. 20:00)")
    _, gy_end = _wait_for_position("Centro de la ÚLTIMA franja horaria visible")
    hour_end = int(input("  ¿Qué hora indica esa franja? (ej: 20): ").strip() or "20")

    print("\n─── PASO 5/6 ──────────────────────────────────────────────")
    print("    Campo de búsqueda de pacientes en el formulario 'Nueva cita'")
    print("    → Haz doble clic en un slot del calendario para abrirlo")
    input("  Presiona ENTER cuando el formulario 'Nueva cita' esté abierto... ")
    sbx, sby = _wait_for_position("CENTRO del campo de búsqueda de pacientes")

    print("\n─── PASO 6/6 ──────────────────────────────────────────────")
    print("    Botón 'Crear cita' o 'Guardar' del formulario")
    cbx, cby = _wait_for_position("Botón CREAR/GUARDAR cita")

    # ── Calcular valores ─────────────────────────────────────────────────────

    cal = dict(CAL_DEFAULTS)
    cal["grid_top_px"]    = max(0, gy1 - wy)
    cal["grid_bottom_px"] = max(0, wh - (gy2 - wy))
    cal["time_col_px"]    = max(0, gx1 - wx)
    cal["grid_start_h"]   = hour_start
    cal["grid_end_h"]     = hour_end
    cal["search_box_x"]   = round((sbx - wx) / ww, 3)
    cal["search_box_y"]   = round((sby - wy) / wh, 3)
    cal["crear_btn_x"]    = round((cbx - wx) / ww, 3)
    cal["crear_btn_y"]    = round((cby - wy) / wh, 3)
    cal["_meta"] = {
        "window":       {"x": wx, "y": wy, "w": ww, "h": wh},
        "grid_corners": {"top_left": [gx1, gy1], "bottom_right": [gx2, gy2]},
        "calibrated_at": datetime.now().isoformat(),
    }

    # ── Mostrar resultados ───────────────────────────────────────────────────

    print("\n" + "═" * 62)
    print("   ✅ Calibración completada")
    print("═" * 62)
    print()
    for k, v in cal.items():
        if not k.startswith("_"):
            print(f"   {k:<20} = {v}")

    CAL_FILE.write_text(json.dumps(cal, indent=2, ensure_ascii=False))
    logger.info(f"Calibración guardada en {CAL_FILE}")

    # Aplicar en memoria para que la sincronización de esta sesión use los nuevos valores
    global CAL
    CAL = {k: v for k, v in cal.items() if not k.startswith("_")}

    print(f"""
💾 Guardado en: {CAL_FILE}

⚠️  Revisa si es necesario ajustar manualmente:
   • first_result_dy  (píxeles desde el buscador hasta el primer resultado, defecto 85)
   • nav_btn_y        (altura de botones Retroceder/Avanzar, defecto 0.88)
""")


# ── MODELO DE DATOS ───────────────────────────────────────────────────────────

@dataclass
class Appointment:
    patient:    str
    date:       date
    start_time: str
    end_time:   str
    day_offset: int   # 0=Lunes … 6=Domingo
    hour:       int
    minute:     int


# ── HELPER: Grid metrics ──────────────────────────────────────────────────────

def calc_grid_metrics(
    wx: int, wy: int, ww: int, wh: int, hour: int, minute: int
) -> tuple[int, int, float, float, int]:
    """
    Calcula métricas del grid de calendario.
    Returns: (grid_h, grid_w, y_ratio, col_w, cell_y)
    """
    grid_h    = wh - CAL["grid_top_px"] - CAL["grid_bottom_px"]
    grid_w    = ww - CAL["time_col_px"]
    col_w     = grid_w / 7
    total_min = (CAL["grid_end_h"] - CAL["grid_start_h"]) * 60
    event_min = (hour - CAL["grid_start_h"]) * 60 + minute
    y_ratio   = event_min / total_min
    cell_y    = int(wy + CAL["grid_top_px"] + y_ratio * grid_h)
    return grid_h, grid_w, y_ratio, col_w, cell_y


# ── GOOGLE CALENDAR ───────────────────────────────────────────────────────────

def get_calendar_service():
    """Autentica con Google Calendar y devuelve el cliente."""
    creds: Optional[Credentials] = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES_CAL)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(f"\n❌ No se encontró credentials.json en {CREDS_FILE}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES_CAL)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_week_appointments(service, monday: date) -> list[Appointment]:
    """Devuelve los eventos con hora de la semana dada."""
    sunday   = monday + timedelta(days=6)
    tz       = datetime.now().astimezone().tzinfo
    time_min = datetime.combine(monday, datetime.min.time(), tzinfo=tz).isoformat()
    time_max = datetime.combine(sunday, datetime.max.time(), tzinfo=tz).isoformat()

    try:
        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except HttpError as e:
        print(f"❌ Error Google Calendar: {e}")
        sys.exit(1)

    appointments: list[Appointment] = []
    for ev in result.get("items", []):
        start_str = ev["start"].get("dateTime")
        end_str   = ev["end"].get("dateTime")
        if not start_str:
            continue  # evento de día completo → ignorar

        start_dt = datetime.fromisoformat(start_str)
        end_dt   = datetime.fromisoformat(end_str)

        appointments.append(Appointment(
            patient    = ev.get("summary", "").strip(),
            date       = start_dt.date(),
            start_time = start_dt.strftime("%H:%M"),
            end_time   = end_dt.strftime("%H:%M"),
            day_offset = start_dt.weekday(),
            hour       = start_dt.hour,
            minute     = start_dt.minute,
        ))

    return appointments


# ── AUTOMATIZACIÓN DE ARCHIVEX ────────────────────────────────────────────────

def get_archivex_process_name() -> str:
    """Busca el nombre exacto del proceso de Archivex entre las apps abiertas."""
    script = '''
    tell application "System Events"
        set appNames to name of every process whose background only is false
        return appNames as string
    end tell
    '''
    out = sp.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()
    for name in [n.strip() for n in out.split(",")]:
        if "archivex" in name.lower() or "archive" in name.lower():
            return name
    return APP_NAME


def focus_archivex() -> None:
    """Trae Archivex Clinical al primer plano."""
    sp.run(["osascript", "-e", f'tell application "{get_archivex_process_name()}" to activate'])
    time.sleep(1.2)


def get_window_bounds(interactive: bool = True) -> Optional[tuple[int, int, int, int]]:
    """
    Devuelve (x, y, ancho, alto) de la ventana de Archivex.
    Si interactive=True y no la detecta, pide al usuario que haga clic.
    Si interactive=False, devuelve None en caso de fallo.
    """
    process_name = get_archivex_process_name()
    script = f'''
    tell application "System Events"
        tell process "{process_name}"
            set pos to position of window 1
            set sz  to size of window 1
            return (item 1 of pos as string) & "," & (item 2 of pos as string) & "," & (item 1 of sz as string) & "," & (item 2 of sz as string)
        end tell
    end tell
    '''
    out = sp.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()

    if out and "," in out:
        try:
            parts = [int(v.strip()) for v in out.split(",")]
            return parts[0], parts[1], parts[2], parts[3]
        except ValueError as e:
            logger.error(f"Error parseando bounds: '{out}' — {e}")

    if not interactive:
        return None

    logger.warning("No pude detectar la ventana de Archivex automáticamente.")
    print("\n⚠️  Haz clic en cualquier parte de la ventana de Archivex Clinical")
    print("   y pulsa ENTER para continuar...")
    input()
    sw, sh = pyautogui.size()
    return 0, 0, sw, sh


def navigate_to_week(monday: date) -> None:
    """Navega al lunes indicado pulsando Avanzar/Retroceder."""
    today          = date.today()
    current_monday = today - timedelta(days=today.weekday())
    delta_weeks    = (monday - current_monday).days // 7

    if delta_weeks == 0:
        return

    bounds = get_window_bounds()
    if not bounds:
        return
    wx, wy, ww, wh = bounds
    clicks = abs(delta_weeks)
    btn_y  = int(wy + wh * CAL["nav_btn_y"])

    if delta_weeks > 0:
        btn_x, label = int(wx + ww * CAL["avanzar_x"]), "Avanzar"
    else:
        btn_x, label = int(wx + ww * CAL["retroceder_x"]), "Retroceder"

    print(f"   📅 Navegando {clicks}x {label}…")
    for _ in range(clicks):
        pyautogui.click(btn_x, btn_y)
        time.sleep(0.6)


def click_calendar_slot(wx: int, wy: int, ww: int, wh: int,
                        day_offset: int, hour: int, minute: int) -> None:
    """Hace clic en la celda del calendario para el día y hora dados."""
    _, _, _, col_w, cell_y = calc_grid_metrics(wx, wy, ww, wh, hour, minute)
    cell_x = int(wx + CAL["time_col_px"] + day_offset * col_w + col_w / 2)
    pyautogui.click(cell_x, cell_y)
    time.sleep(1.5)


def search_and_select_patient(wx: int, wy: int, ww: int, wh: int, name: str) -> None:
    """Escribe el nombre en el buscador vía clipboard (soporta acentos) y selecciona el primer resultado."""
    search_x = int(wx + ww * CAL["search_box_x"])
    search_y = int(wy + wh * CAL["search_box_y"])

    pyautogui.click(search_x, search_y)
    time.sleep(0.4)
    pyautogui.hotkey("command", "a")
    sp.run(["pbcopy"], input=name.encode("utf-8"), check=True)
    pyautogui.hotkey("command", "v")
    time.sleep(1.8)

    pyautogui.click(search_x, search_y + CAL["first_result_dy"])
    time.sleep(0.5)


def click_crear_cita(wx: int, wy: int, ww: int, wh: int) -> None:
    """Pulsa el botón '+ Crear cita'."""
    pyautogui.click(int(wx + ww * CAL["crear_btn_x"]), int(wy + wh * CAL["crear_btn_y"]))
    time.sleep(1.0)


# ── DETECCIÓN DE CONFLICTOS ───────────────────────────────────────────────────

def get_cell_region(wx: int, wy: int, ww: int, wh: int,
                    day_offset: int, hour: int, minute: int) -> tuple[int, int, int, int]:
    """Devuelve (x, y, ancho, alto) de la celda del calendario."""
    grid_h, _, _, col_w, cell_y = calc_grid_metrics(wx, wy, ww, wh, hour, minute)
    slot_h = grid_h / ((CAL["grid_end_h"] - CAL["grid_start_h"]) * 4)
    cell_x = int(wx + CAL["time_col_px"] + day_offset * col_w + 4)
    return cell_x, cell_y, int(col_w - 8), int(slot_h * 4)


def is_slot_occupied(wx: int, wy: int, ww: int, wh: int,
                     day_offset: int, hour: int, minute: int) -> bool:
    """
    Detecta si una celda del calendario ya tiene una cita.
    - variance > 300: contenido colorido (evento con fondo)
    - mean < 220: píxeles oscuros (texto/bloque gris)
    """
    from PIL import ImageStat

    cx, cy, cw, ch = get_cell_region(wx, wy, ww, wh, day_offset, hour, minute)
    screenshot = pyautogui.screenshot(region=(cx, cy, cw, ch))
    stat = ImageStat.Stat(screenshot.convert("L"))
    return stat.var[0] > 300 or stat.mean[0] < 220


def ask_conflict_action(appt: Appointment) -> str:
    """Devuelve: 'crear' | 'saltar' | 'parar'"""
    print(f"\n  ⚠️  CONFLICTO detectado: {appt.patient} — {appt.date.strftime('%a %d/%m')} {appt.start_time}")
    print("      El slot ya parece ocupado en Archivex.")
    print("      [C] Crear igualmente   [S] Saltar esta cita   [P] Parar todo")
    while True:
        resp = input("      ¿Qué hago? (c/s/p): ").strip().lower()
        if resp == "c":
            return "crear"
        if resp == "s":
            return "saltar"
        if resp == "p":
            return "parar"
        print("      Responde c, s o p.")


# ── LOG ───────────────────────────────────────────────────────────────────────

def log(appt: Appointment, status: str, note: str = "") -> None:
    msg = f"{status:<8} | {appt.patient:<30} | {appt.date.strftime('%d/%m/%Y')} {appt.start_time}-{appt.end_time}"
    if note:
        msg += f" | {note}"
    logger.info(msg)


def log_session_header(n_citas: int, monday: date) -> None:
    logger.info(f"SESIÓN — Semana {monday.strftime('%d/%m/%Y')} — {n_citas} cita(s)")


# ── PROCESADO ────────────────────────────────────────────────────────────────

class ConflictStopException(Exception):
    pass


def process_appointment(appt: Appointment, wx: int, wy: int, ww: int, wh: int) -> str:
    """
    Procesa una cita completa en Archivex con detección de conflictos.
    Devuelve: 'creada' | 'saltada'
    Lanza ConflictStopException si el usuario elige parar.
    """
    if is_slot_occupied(wx, wy, ww, wh, appt.day_offset, appt.hour, appt.minute):
        accion = ask_conflict_action(appt)
        if accion == "parar":
            log(appt, "PARADO", "conflicto detectado — usuario paró")
            raise ConflictStopException()
        if accion == "saltar":
            log(appt, "SALTADA", "conflicto detectado — usuario saltó")
            return "saltada"
        log_note = "conflicto ignorado por usuario"
    else:
        log_note = ""

    click_calendar_slot(wx, wy, ww, wh, appt.day_offset, appt.hour, appt.minute)
    search_and_select_patient(wx, wy, ww, wh, appt.patient)
    click_crear_cita(wx, wy, ww, wh)
    log(appt, "CREADA", log_note)
    return "creada"


# ── SELECCIÓN DE DÍAS ─────────────────────────────────────────────────────────

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def seleccionar_dias(appointments: list[Appointment]) -> list[Appointment]:
    """Muestra las citas agrupadas por día y deja al usuario elegir cuáles sincronizar."""
    dias_con_citas: dict[int, list[Appointment]] = {}
    for a in appointments:
        dias_con_citas.setdefault(a.day_offset, []).append(a)

    print("\n┌─────────────────────────────────────────────────────┐")
    print("│           Selección de días a sincronizar           │")
    print("├─────────────────────────────────────────────────────┤")

    dias_disponibles = sorted(dias_con_citas.keys())
    for idx, day_off in enumerate(dias_disponibles, 1):
        citas = dias_con_citas[day_off]
        fecha = citas[0].date.strftime("%d/%m")
        dia   = DIAS_SEMANA[day_off]
        print(f"│  [{idx}] {dia} {fecha} — {len(citas)} cita{'s' if len(citas) > 1 else ''}:")
        for c in citas:
            print(f"│       • {c.patient:<28} {c.start_time}–{c.end_time}")
    print("│  [T] Todos los días                                 │")
    print("│  [N] Ninguno (cancelar)                             │")
    print("└─────────────────────────────────────────────────────┘")

    while True:
        raw = input("\n¿Qué días sincronizas hoy? (ej: 1,3 o T o N): ").strip().upper()
        if raw == "N":
            return []
        if raw == "T":
            return appointments
        try:
            indices   = [int(x.strip()) for x in raw.split(",")]
            seleccion = []
            for i in indices:
                if 1 <= i <= len(dias_disponibles):
                    seleccion.extend(dias_con_citas[dias_disponibles[i - 1]])
                else:
                    raise ValueError(f"Opción {i} no válida")
            return seleccion
        except ValueError as e:
            print(f"   ⚠️  {e}. Inténtalo de nuevo.")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def _show_cal_status() -> None:
    """Muestra si la calibración viene de archivo o de defaults."""
    if CAL_FILE.exists():
        meta = json.loads(CAL_FILE.read_text()).get("_meta", {})
        ts   = meta.get("calibrated_at", "desconocido")
        print(f"   📐 Calibración: guardada el {ts[:16]}")
    else:
        print("   📐 Calibración: usando valores por defecto (sin calibrar)")


def main() -> None:
    print("\n" + "═" * 52)
    print("   Archivex Sync — Google Calendar → Archivex")
    print("═" * 52 + "\n")

    _show_cal_status()

    # ── Opción de calibración al inicio ──────────────────────────────────────
    print("\n  [C] Recalibrar pantalla ahora")
    print("  [ENTER] Continuar con la calibración actual\n")
    resp = input("  Opción: ").strip().lower()
    if resp == "c":
        run_calibration()
        print("\n✅ Calibración guardada. Continuando con la sincronización...\n")

    # 1. Conectar con Google Calendar
    print("\n📅 Conectando con Google Calendar…")
    service = get_calendar_service()

    # 2. Semana objetivo
    today  = date.today()
    monday = today - timedelta(days=today.weekday())
    print(f"📆 Semana: {monday.strftime('%d/%m/%Y')} → {(monday + timedelta(6)).strftime('%d/%m/%Y')}")

    # 3. Obtener citas
    all_appointments = get_week_appointments(service, monday)

    if not all_appointments:
        print("\n✅ No hay citas con hora en Google Calendar esta semana.")
        return

    # 4. Seleccionar días
    appointments = seleccionar_dias(all_appointments)
    if not appointments:
        print("Cancelado.")
        return

    print(f"\n✅ {len(appointments)} cita(s) seleccionadas para sincronizar.")
    print("""
⚠️  Antes de continuar asegúrate de:
   1. Archivex Clinical está abierto en VISTA SEMANAL
   2. Terminal tiene permiso de Accesibilidad
      (Ajustes → Privacidad → Accesibilidad → Terminal ✓)
   3. No moverás el ratón mientras se ejecuta
      (muévelo a la esquina SUPERIOR IZQUIERDA para abortar)
""")

    if input("¿Continuar? (s/n): ").strip().lower() != "s":
        print("Cancelado.")
        return

    print("\n🤖 Empezando en 4 segundos…\n")
    time.sleep(4)

    # 5. Foco y navegación
    focus_archivex()
    navigate_to_week(monday)

    # 6. Posición de la ventana
    bounds = get_window_bounds()
    if not bounds:
        print("❌ No se pudo detectar la ventana de Archivex.")
        return
    wx, wy, ww, wh = bounds
    print(f"   🪟 Ventana: {ww}×{wh} en ({wx},{wy})\n")

    # 7. Procesar citas
    creadas, saltadas = 0, 0
    errors: list[str] = []
    log_session_header(len(appointments), monday)

    for i, appt in enumerate(appointments, 1):
        print(f"[{i}/{len(appointments)}] {appt.patient} — {appt.date.strftime('%a %d/%m')} {appt.start_time}…",
              end=" ", flush=True)
        try:
            resultado = process_appointment(appt, wx, wy, ww, wh)
            if resultado == "creada":
                creadas += 1
                print("✅")
            elif resultado == "saltada":
                saltadas += 1
                print("⏭  saltada")
            time.sleep(0.8)
        except ConflictStopException:
            print("\n⛔ Parado por conflicto.")
            break
        except Exception as ex:
            print(f"❌ ({ex})")
            log(appt, "ERROR", str(ex))
            errors.append(appt.patient)
            time.sleep(1)

    # 8. Resumen
    print(f"\n{'═' * 52}")
    print(f"✅ Creadas:  {creadas}")
    print(f"⏭  Saltadas: {saltadas}")
    print(f"❌ Errores:  {len(errors)}")
    if errors:
        print(f"   Revisar manualmente: {', '.join(errors)}")
    print(f"\n📄 Log guardado en: {LOG_FILE}")


if __name__ == "__main__":
    main()
