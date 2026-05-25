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

CALIBRACIÓN (primera vez):
    Si los clics no dan en el sitio correcto, ajusta los valores
    en la sección CONFIG → CALIBRACIÓN más abajo.
"""

# ── Imports ───────────────────────────────────────────────────────────────────
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

SCOPES_CAL  = ["https://www.googleapis.com/auth/calendar.readonly"]
SCRIPT_DIR  = Path(__file__).parent
CONFIG_DIR  = Path.home() / ".config" / "archivex-sync"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CREDS_FILE  = SCRIPT_DIR / "credentials.json"
TOKEN_FILE  = CONFIG_DIR / "token_archivex.json"
LOG_FILE    = CONFIG_DIR / "archivex_sync.log"

APP_NAME    = "Archivex Clinical"   # nombre exacto de la app en macOS

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

# Velocidad de automatización (segundos entre acciones)
pyautogui.PAUSE    = 0.4
pyautogui.FAILSAFE = True  # mueve el ratón a la esquina superior izquierda para ABORTAR

# ── CALIBRACIÓN ───────────────────────────────────────────────────────────────
# Ajusta estos valores si los clics no dan en el sitio correcto.
# Son proporciones relativas al tamaño de la ventana de Archivex.

CAL = {
    # Píxeles desde el TOP de la ventana hasta donde empieza la rejilla del calendario
    "grid_top_px":    135,
    # Píxeles desde el BOTTOM de la ventana hasta donde termina la rejilla
    "grid_bottom_px": 145,
    # Píxeles de ancho de la columna de horas (la franja izquierda con "08:00", "09:00"…)
    "time_col_px":    65,
    # Hora en que empieza visualmente la rejilla (normalmente 8)
    "grid_start_h":   8,
    # Hora en que termina visualmente la rejilla (normalmente 20)
    "grid_end_h":     20,

    # Posición del buscador de pacientes dentro del formulario "Nueva cita"
    # (proporción relativa al ancho/alto de la ventana)
    "search_box_x":   0.245,   # ~25% desde la izquierda
    "search_box_y":   0.525,   # ~52% desde arriba

    # Desplazamiento vertical hasta el PRIMER resultado de la lista (en píxeles)
    "first_result_dy": 85,

    # Posición del botón "+ Crear cita"
    "crear_btn_x":    0.75,    # ~75% desde la izquierda
    "crear_btn_y":    0.87,    # ~87% desde arriba

    # Botones Retroceder / Avanzar en la barra del calendario
    "retroceder_x":   0.05,
    "avanzar_x":      0.95,
    "nav_btn_y":      0.88,    # altura de los botones de navegación
}

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


# ── HELPER: Grid metrics ───────────────────────────────────────────────────────

def calc_grid_metrics(
    wx: int, wy: int, ww: int, wh: int, hour: int, minute: int
) -> tuple[int, int, float, float, int]:
    """
    Calcula métricas del grid de calendario.

    Returns: (grid_h, grid_w, y_ratio, col_w, cell_y)
    """
    grid_h = wh - CAL["grid_top_px"] - CAL["grid_bottom_px"]
    grid_w = ww - CAL["time_col_px"]
    col_w = grid_w / 7
    total_min = (CAL["grid_end_h"] - CAL["grid_start_h"]) * 60
    event_min = (hour - CAL["grid_start_h"]) * 60 + minute
    y_ratio = event_min / total_min
    cell_y = int(wy + CAL["grid_top_px"] + y_ratio * grid_h)
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
    sunday = monday + timedelta(days=6)
    tz = datetime.now().astimezone().tzinfo
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

def focus_archivex() -> None:
    """Trae Archivex Clinical al primer plano."""
    process_name = get_archivex_process_name()
    sp.run(["osascript", "-e", f'tell application "{process_name}" to activate'])
    time.sleep(1.2)


def get_archivex_process_name() -> str:
    """Busca el nombre exacto del proceso de Archivex entre las apps abiertas."""
    script = '''
    tell application "System Events"
        set appNames to name of every process whose background only is false
        return appNames as string
    end tell
    '''
    out = sp.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()
    candidates = [n.strip() for n in out.split(",")]
    for name in candidates:
        if "archivex" in name.lower() or "archive" in name.lower():
            return name
    # Si no encontramos nada, devolvemos el nombre por defecto
    return APP_NAME


def get_window_bounds() -> tuple[int, int, int, int]:
    """Devuelve (x, y, ancho, alto) de la ventana de Archivex."""
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

    if not out or "," not in out:
        logger.warning("No pude detectar la ventana de Archivex automáticamente.")
        print("\n⚠️  Haz clic en cualquier parte de la ventana de Archivex Clinical")
        print("   y pulsa ENTER para continuar...")
        input()
        sw, sh = pyautogui.size()
        return 0, 0, sw, sh

    try:
        parts = [int(v.strip()) for v in out.split(",")]
        return parts[0], parts[1], parts[2], parts[3]
    except ValueError as e:
        logger.error(f"Error parseando bounds: '{out}' — {e}")
        sw, sh = pyautogui.size()
        return 0, 0, sw, sh


def navigate_to_week(monday: date) -> None:
    """Navega al lunes indicado pulsando Avanzar/Retroceder."""
    today           = date.today()
    current_monday  = today - timedelta(days=today.weekday())
    delta_weeks     = (monday - current_monday).days // 7

    if delta_weeks == 0:
        return

    wx, wy, ww, wh = get_window_bounds()
    clicks          = abs(delta_weeks)
    btn_y           = int(wy + wh * CAL["nav_btn_y"])

    if delta_weeks > 0:
        btn_x = int(wx + ww * CAL["avanzar_x"])
        label = "Avanzar"
    else:
        btn_x = int(wx + ww * CAL["retroceder_x"])
        label = "Retroceder"

    print(f"   📅 Navegando {clicks}x {label}…")
    for _ in range(clicks):
        pyautogui.click(btn_x, btn_y)
        time.sleep(0.6)


def click_calendar_slot(wx: int, wy: int, ww: int, wh: int,
                         day_offset: int, hour: int, minute: int) -> None:
    """Hace clic en la celda del calendario para el día y hora dados."""
    grid_h, grid_w, y_ratio, col_w, cell_y = calc_grid_metrics(wx, wy, ww, wh, hour, minute)
    cell_x = int(wx + CAL["time_col_px"] + day_offset * col_w + col_w / 2)
    pyautogui.click(cell_x, cell_y)
    time.sleep(1.5)  # esperar a que abra el formulario


def search_and_select_patient(wx: int, wy: int, ww: int, wh: int,
                               name: str) -> None:
    """Escribe el nombre en el buscador y selecciona el primer resultado."""
    import subprocess

    search_x = int(wx + ww * CAL["search_box_x"])
    search_y = int(wy + wh * CAL["search_box_y"])

    pyautogui.click(search_x, search_y)
    time.sleep(0.4)
    pyautogui.hotkey("command", "a")

    # Use clipboard to handle special characters (accents, etc)
    subprocess.run(["pbcopy"], input=name.encode("utf-8"), check=True)
    pyautogui.hotkey("command", "v")

    time.sleep(1.8)  # esperar resultados de búsqueda

    # Primer resultado está justo debajo del buscador
    pyautogui.click(search_x, search_y + CAL["first_result_dy"])
    time.sleep(0.5)


def click_crear_cita(wx: int, wy: int, ww: int, wh: int) -> None:
    """Pulsa el botón '+ Crear cita'."""
    btn_x = int(wx + ww * CAL["crear_btn_x"])
    btn_y = int(wy + wh * CAL["crear_btn_y"])
    pyautogui.click(btn_x, btn_y)
    time.sleep(1.0)


# ── SEGURIDAD: DETECCIÓN DE CONFLICTOS ────────────────────────────────────────

def get_cell_region(wx: int, wy: int, ww: int, wh: int,
                    day_offset: int, hour: int, minute: int) -> tuple[int, int, int, int]:
    """Devuelve (x, y, ancho, alto) de la celda del calendario."""
    grid_h, grid_w, y_ratio, col_w, cell_y = calc_grid_metrics(wx, wy, ww, wh, hour, minute)
    slot_h = grid_h / ((CAL["grid_end_h"] - CAL["grid_start_h"]) * 4)  # slots de 15 min

    cell_x = int(wx + CAL["time_col_px"] + day_offset * col_w + 4)
    return cell_x, cell_y, int(col_w - 8), int(slot_h * 4)  # celda de 1h


def is_slot_occupied(wx: int, wy: int, ww: int, wh: int,
                     day_offset: int, hour: int, minute: int) -> bool:
    """
    Detecta si una celda del calendario ya tiene una cita.

    Toma captura de la región y analiza si hay contenido (píxeles no blancos/grises).
    - variance > 300: indica contenido colorido (evento con fondo)
    - mean < 220: indica píxeles oscuros (texto/bloque gris)
    """
    from PIL import ImageStat

    cx, cy, cw, ch = get_cell_region(wx, wy, ww, wh, day_offset, hour, minute)
    screenshot = pyautogui.screenshot(region=(cx, cy, cw, ch))

    stat = ImageStat.Stat(screenshot.convert("L"))
    variance = stat.var[0]
    mean = stat.mean[0]

    has_content = variance > 300 or mean < 220
    return has_content


def ask_conflict_action(appt: Appointment) -> str:
    """
    Pausa la ejecución y pregunta al usuario qué hacer con un conflicto.
    Devuelve: 'crear' | 'saltar' | 'parar'
    """
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
    """Log an appointment action with status."""
    msg = (
        f"{status:<8} | "
        f"{appt.patient:<30} | "
        f"{appt.date.strftime('%d/%m/%Y')} {appt.start_time}-{appt.end_time}"
    )
    if note:
        msg += f" | {note}"
    logger.info(msg)


def log_session_header(n_citas: int, monday: date) -> None:
    """Log session header."""
    logger.info(f"SESIÓN — Semana {monday.strftime('%d/%m/%Y')} — {n_citas} cita(s)")


# ── PROCESADO CON SEGURIDAD ───────────────────────────────────────────────────

class ConflictStopException(Exception):
    """El usuario eligió parar todo al encontrar un conflicto."""
    pass


def process_appointment(appt: Appointment,
                         wx: int, wy: int, ww: int, wh: int) -> str:
    """
    Procesa una cita completa en Archivex con detección de conflictos.
    Devuelve: 'creada' | 'saltada' | 'error'
    Lanza ConflictStopException si el usuario elige parar.
    """
    # 1. Comprobar si el slot está ocupado ANTES de clicar
    if is_slot_occupied(wx, wy, ww, wh, appt.day_offset, appt.hour, appt.minute):
        accion = ask_conflict_action(appt)

        if accion == "parar":
            log(appt, "PARADO", "conflicto detectado — usuario paró")
            raise ConflictStopException()

        if accion == "saltar":
            log(appt, "SALTADA", "conflicto detectado — usuario saltó")
            return "saltada"

        # accion == "crear" → continúa igualmente
        log_note = "conflicto ignorado por usuario"
    else:
        log_note = ""

    # 2. Clic en el slot, búsqueda de paciente y confirmación
    click_calendar_slot(wx, wy, ww, wh, appt.day_offset, appt.hour, appt.minute)
    search_and_select_patient(wx, wy, ww, wh, appt.patient)
    click_crear_cita(wx, wy, ww, wh)

    log(appt, "CREADA", log_note)
    return "creada"

# ── MAIN ──────────────────────────────────────────────────────────────────────

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def seleccionar_dias(appointments: list[Appointment]) -> list[Appointment]:
    """Muestra las citas agrupadas por día y deja al usuario elegir cuáles sincronizar."""

    # Agrupar citas por día
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
            indices    = [int(x.strip()) for x in raw.split(",")]
            seleccion  = []
            for i in indices:
                if 1 <= i <= len(dias_disponibles):
                    seleccion.extend(dias_con_citas[dias_disponibles[i - 1]])
                else:
                    raise ValueError(f"Opción {i} no válida")
            return seleccion
        except ValueError as e:
            print(f"   ⚠️  {e}. Inténtalo de nuevo.")


def main() -> None:
    print("\n" + "═" * 50)
    print("   Archivex Sync — Google Calendar → Archivex")
    print("═" * 50 + "\n")

    # 1. Conectar con Google Calendar
    print("📅 Conectando con Google Calendar…")
    service = get_calendar_service()

    # 2. Semana objetivo (por defecto: semana actual)
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
      (muévelo a la esquina SUPERIOR IZQUIERDA para abortar en cualquier momento)
""")

    confirm = input("¿Continuar? (s/n): ").strip().lower()
    if confirm != "s":
        print("Cancelado.")
        return

    print("\n🤖 Empezando en 4 segundos…\n")
    time.sleep(4)

    # 5. Foco en Archivex y navegar a la semana
    focus_archivex()
    navigate_to_week(monday)

    # 6. Obtener posición de la ventana
    wx, wy, ww, wh = get_window_bounds()
    print(f"   🪟 Ventana: {ww}×{wh} en ({wx},{wy})\n")

    # 7. Procesar citas seleccionadas
    creadas = 0
    saltadas = 0
    errors: list[str] = []

    log_session_header(len(appointments), monday)

    for i, appt in enumerate(appointments, 1):
        print(f"[{i}/{len(appointments)}] {appt.patient} — {appt.date.strftime('%a %d/%m')} {appt.start_time}…", end=" ", flush=True)
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
    print(f"\n{'═' * 50}")
    print(f"✅ Creadas:  {creadas}")
    print(f"⏭  Saltadas: {saltadas}")
    print(f"❌ Errores:  {len(errors)}")
    if errors:
        print(f"   Revisar manualmente: {', '.join(errors)}")
    print(f"\n📄 Log guardado en: {LOG_FILE}")


if __name__ == "__main__":
    main()
