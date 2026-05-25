"""
vision_driver.py — Automación de Archivex Clinical basada en visión con Claude API.

Elimina la necesidad de calibración de coordenadas. Claude analiza screenshots
y devuelve las coordenadas de los elementos UI pedidos.

Requiere:  ANTHROPIC_API_KEY en variables de entorno.
Modelo:    ARCHIVEX_VISION_MODEL (default: claude-3-5-haiku-20241022)
"""

import base64
import json
import logging
import os
import re
import subprocess
import time
from datetime import date
from io import BytesIO
from typing import Optional

import pyautogui

logger = logging.getLogger(__name__)

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
_MODEL  = os.getenv("ARCHIVEX_VISION_MODEL", "claude-3-5-haiku-20241022")

_client: Optional[object] = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def _b64_screenshot() -> str:
    """Captura la pantalla y devuelve PNG en base64."""
    buf = BytesIO()
    pyautogui.screenshot().save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


# ── Núcleo de visión ──────────────────────────────────────────────────────────

def find_coords(description: str, context: str = "") -> Optional[tuple[int, int]]:
    """
    Toma un screenshot y pregunta a Claude dónde está el elemento.
    Devuelve (x, y) en píxeles, o None si no se encuentra.
    """
    prompt = (
        "Estás automatizando Archivex Clinical, una app de citas médicas en macOS en español.\n"
        + (f"Contexto: {context}\n" if context else "")
        + f"Localiza este elemento: {description}\n\n"
        "Responde ÚNICAMENTE con JSON sin markdown:\n"
        '{"x": <entero>, "y": <entero>}\n'
        "Si el elemento no está visible: {\"x\": null, \"y\": null}"
    )

    resp = _get_client().messages.create(
        model=_MODEL,
        max_tokens=48,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": _b64_screenshot(),
            }},
            {"type": "text", "text": prompt},
        ]}],
    )

    raw = resp.content[0].text.strip()
    logger.debug("vision '%s' → %s", description[:50], raw)

    try:
        d = json.loads(raw)
        if d.get("x") is not None:
            return int(d["x"]), int(d["y"])
    except (json.JSONDecodeError, ValueError, TypeError):
        m = re.search(r'"x"\s*:\s*(\d+).*?"y"\s*:\s*(\d+)', raw, re.DOTALL)
        if m:
            return int(m.group(1)), int(m.group(2))

    return None


def click_element(
    description: str,
    context: str = "",
    double: bool = False,
    retries: int = 3,
) -> tuple[int, int]:
    """
    Localiza el elemento por descripción y hace clic.
    Lanza RuntimeError si no lo encuentra tras los reintentos.
    """
    for attempt in range(retries):
        coords = find_coords(description, context)
        if coords:
            x, y = coords
            (pyautogui.doubleClick if double else pyautogui.click)(x, y)
            logger.info(
                "clic%s '%s' → (%d,%d)",
                " doble" if double else "",
                description[:40],
                x,
                y,
            )
            return x, y
        if attempt < retries - 1:
            logger.debug(
                "reintento %d/%d: '%s'", attempt + 1, retries, description[:40]
            )
            time.sleep(1.5)

    raise RuntimeError(
        f"No encontrado tras {retries} intentos: {description[:60]}"
    )


# ── Acciones de alto nivel ────────────────────────────────────────────────────

def open_appointment_form(day_offset: int, hour: int, minute: int) -> bool:
    """
    Hace doble clic en el slot del calendario para el día/hora indicados.
    Devuelve True si el formulario de nueva cita se abrió correctamente.
    """
    day  = DIAS_ES[day_offset]
    t    = f"{hour:02d}:{minute:02d}"
    desc = (
        f"la celda vacía del calendario en la columna {day} "
        f"y la fila horaria de las {t} en la vista semanal"
    )
    click_element(
        desc,
        context="Vista semanal de Archivex Clinical con días como columnas y horas como filas.",
        double=True,
    )
    time.sleep(2.0)

    # Verificar que el formulario se abrió
    coords = find_coords(
        "el campo de texto para buscar el nombre del paciente dentro del formulario de nueva cita",
        context="Puede haberse abierto un diálogo modal para crear una nueva cita.",
    )
    return coords is not None


def fill_patient(patient_name: str) -> None:
    """Hace clic en el buscador, escribe el nombre y selecciona el primer resultado."""
    click_element(
        "el campo de búsqueda de nombre de paciente en el formulario de nueva cita",
        context="El formulario de nueva cita está abierto.",
    )
    time.sleep(0.4)

    # Seleccionar todo y pegar (soporta acentos y caracteres especiales)
    pyautogui.hotkey("command", "a")
    time.sleep(0.1)
    subprocess.run(["pbcopy"], input=patient_name.encode("utf-8"), check=True)
    pyautogui.hotkey("command", "v")
    time.sleep(2.5)

    click_element(
        "el primer resultado de la lista de autocompletado de pacientes bajo el campo de búsqueda",
        context="Tras escribir el nombre apareció un desplegable con sugerencias de pacientes.",
        retries=3,
    )
    time.sleep(0.8)


def save_appointment() -> None:
    """Hace clic en el botón de crear / guardar la cita."""
    click_element(
        "el botón principal para crear o guardar la cita "
        "(puede decir 'Crear cita', 'Guardar', 'Aceptar' o similar)",
        context="El formulario de cita está completo y listo para guardar.",
        retries=3,
    )
    time.sleep(1.5)


# ── Navegación semanal ────────────────────────────────────────────────────────

def _detect_current_monday() -> Optional[date]:
    """Pregunta a Claude qué lunes está mostrando el calendario."""
    prompt = (
        "Mira este calendario semanal de Archivex Clinical. "
        "¿Qué fecha tiene el lunes (primer día) de la semana que se muestra actualmente? "
        'Responde ÚNICAMENTE con JSON: {"date": "YYYY-MM-DD"} '
        "Si no puedes determinarlo con certeza: {\"date\": null}"
    )
    resp = _get_client().messages.create(
        model=_MODEL,
        max_tokens=32,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": _b64_screenshot(),
            }},
            {"type": "text", "text": prompt},
        ]}],
    )
    raw = resp.content[0].text.strip()
    try:
        d = json.loads(raw)
        if d.get("date"):
            return date.fromisoformat(d["date"])
    except Exception:
        pass
    return None


def navigate_to_week(target_monday: date) -> None:
    """Navega Archivex hasta la semana que contiene target_monday."""
    current = _detect_current_monday()
    if current is None:
        logger.warning("No se detectó la semana actual via visión — omitiendo navegación")
        return

    delta = (target_monday - current).days // 7
    if delta == 0:
        logger.info("Semana correcta ya visible")
        return

    btn_desc = (
        "el botón flecha derecha / 'semana siguiente' en la barra de navegación superior"
        if delta > 0
        else "el botón flecha izquierda / 'semana anterior' en la barra de navegación superior"
    )
    logger.info(
        "Navegando %d semana(s) %s", abs(delta), "adelante" if delta > 0 else "atrás"
    )
    for _ in range(abs(delta)):
        click_element(btn_desc, context="Barra de navegación del calendario semanal.")
        time.sleep(0.8)


# ── Utilidad ──────────────────────────────────────────────────────────────────

def is_available() -> bool:
    """True si ANTHROPIC_API_KEY está configurada y anthropic está instalado."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False
