#!/usr/bin/env python3
"""
recon.py — Reconocimiento visual de Archivex Clinical con Opus 4.7

Ejecutar UNA VEZ (o cuando cambie la pantalla/app) con Archivex abierto
en vista semanal:

    python recon.py

Produce:  ~/.config/archivex-sync/ui_knowledge.json

Requisitos:
  - Archivex Clinical abierto en vista semanal
  - ANTHROPIC_API_KEY configurada
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from datetime import date
from io import BytesIO
from pathlib import Path

import pyautogui
from openai import OpenAI

# ─── CONSTANTES ──────────────────────────────────────────────────────────────
CONFIG_DIR     = Path.home() / ".config" / "archivex-sync"
OUTPUT_PATH    = CONFIG_DIR / "ui_knowledge.json"
MODEL_RECON    = os.getenv(
    "ARCHIVEX_RECON_MODEL", "nvidia/nemotron-nano-12b-v2-vl:free"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1"

_REQUIRED_KEYS       = {"version", "grid", "elements", "visual_signatures"}
_REQUIRED_GRID       = {"start_hour", "end_hour", "col_offsets_pct",
                        "first_row_y_pct", "last_row_y_pct"}
_REQUIRED_ELEMENTS   = {"nav_prev_pct", "nav_next_pct", "patient_search_pct",
                        "first_result_pct", "save_btn_pct"}
_REQUIRED_SIGNATURES = {"empty_slot", "occupied_slot", "form_open",
                        "patient_selected", "appointment_saved"}


# ─── VALIDACIÓN ──────────────────────────────────────────────────────────────
def validate_recon_output(kb: dict) -> None:
    """
    Valida el JSON producido por Opus.
    Lanza ValueError con mensaje descriptivo si algo está mal.
    """
    for k in _REQUIRED_KEYS:
        if k not in kb:
            raise ValueError(
                f"Falta la clave raíz: '{k}' (grid, elements, visual_signatures requeridos)"
            )

    for k in _REQUIRED_GRID:
        if k not in kb["grid"]:
            raise ValueError(f"grid: falta '{k}'")

    cols = kb["grid"].get("col_offsets_pct", [])
    if len(cols) != 7:
        raise ValueError(
            f"col_offsets_pct debe tener exactamente 7 valores (uno por día), tiene {len(cols)}"
        )

    for k in _REQUIRED_ELEMENTS:
        if k not in kb["elements"]:
            raise ValueError(f"elements: falta '{k}'")
        for axis in ("x", "y"):
            val = kb["elements"][k].get(axis, -1)
            if not (0.0 <= val <= 1.0):
                raise ValueError(
                    f"elements.{k}.{axis} = {val} fuera de rango [0, 1]. "
                    "Las coordenadas deben ser relativas (0.0 a 1.0)."
                )

    for k in _REQUIRED_SIGNATURES:
        if k not in kb["visual_signatures"]:
            raise ValueError(f"visual_signatures: falta '{k}'")


# ─── CAPTURA DE PANTALLA ─────────────────────────────────────────────────────
def _screenshot_b64() -> str:
    buf = BytesIO()
    pyautogui.screenshot().save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ─── PROMPT PARA OPUS ────────────────────────────────────────────────────────
_RECON_PROMPT = """\
Estás analizando Archivex Clinical, una aplicación de gestión de citas médicas en macOS.
La aplicación usa una interfaz de calendario semanal renderizada con SkiaSharp (canvas),
por lo que NO tiene elementos de accesibilidad estándar.

Analiza cuidadosamente el/los screenshot(s) y produce un JSON con EXACTAMENTE esta estructura.
Todas las coordenadas deben ser RELATIVAS al tamaño de la ventana (valores entre 0.0 y 1.0).
La esquina superior izquierda de la ventana es (0.0, 0.0) y la inferior derecha es (1.0, 1.0).

Devuelve ÚNICAMENTE el JSON, sin markdown, sin explicaciones:

{
  "version": 1,
  "recon_date": "RECON_DATE",
  "window": {"x": <int>, "y": <int>, "w": <int>, "h": <int>},
  "grid": {
    "start_hour": <int, hora inicio cuadrícula ej. 8>,
    "end_hour": <int, hora fin cuadrícula ej. 20>,
    "col_offsets_pct": [<7 floats, x relativa del centro de cada columna Lun-Dom>],
    "first_row_y_pct": <float, y relativa de la primera fila horaria>,
    "last_row_y_pct": <float, y relativa de la última fila horaria>
  },
  "elements": {
    "nav_prev_pct":       {"x": <float>, "y": <float>},
    "nav_next_pct":       {"x": <float>, "y": <float>},
    "patient_search_pct": {"x": <float>, "y": <float>},
    "first_result_pct":   {"x": <float>, "y": <float>},
    "save_btn_pct":       {"x": <float>, "y": <float>}
  },
  "visual_signatures": {
    "empty_slot":        "<descripción de cómo se ve un slot vacío>",
    "occupied_slot":     "<descripción de un slot con cita (fondo coloreado, texto)>",
    "form_open":         "<descripción del formulario modal de nueva cita abierto>",
    "patient_selected":  "<descripción de cuando un paciente está seleccionado>",
    "appointment_saved": "<descripción del estado tras guardar la cita exitosamente>"
  }
}

Si el formulario no está visible en los screenshots, infiere patient_search_pct, first_result_pct
y save_btn_pct de la posición típica de formularios modales en este tipo de aplicación.
"""


# ─── RECONOCIMIENTO ──────────────────────────────────────────────────────────
def run_recon() -> dict:
    """
    Toma screenshots de Archivex y llama al modelo de visión para producir ui_knowledge.json.
    """
    client = OpenAI(
        base_url=OPENROUTER_URL,
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    print("📸  Capturando screenshot 1/2 — calendario...")
    shot1 = _screenshot_b64()
    print("   ✓  Screenshot 1 capturado")
    print("   ℹ️   Haz doble clic en un slot vacío para abrir el formulario de cita.")
    print("   ℹ️   Tienes 5 segundos...")
    time.sleep(5)

    print("📸  Capturando screenshot 2/2 — formulario (si está abierto)...")
    shot2 = _screenshot_b64()
    print("   ✓  Screenshot 2 capturado\n")

    print(f"🤖  Enviando a {MODEL_RECON} para análisis...")
    prompt = _RECON_PROMPT.replace("RECON_DATE", date.today().isoformat())

    resp = client.chat.completions.create(
        model=MODEL_RECON,
        max_tokens=2000,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Screenshot 1 (vista calendario):"},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{shot1}"}},
            {"type": "text", "text": "Screenshot 2 (formulario si estaba abierto):"},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{shot2}"}},
            {"type": "text", "text": prompt},
        ]}],
    )

    raw = resp.choices[0].message.content.strip()

    # Extraer JSON si viene envuelto en markdown
    if "```" in raw:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        raw   = raw[start:end]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"❌  El modelo devolvió JSON inválido: {e}\n\nRespuesta:\n{raw}")


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🔍  Archivex Recon — Análisis visual con {MODEL_RECON}")
    print("─" * 50)
    print("   Archivex Clinical debe estar abierto en vista semanal.")
    input("   Pulsa ENTER cuando esté listo...")

    kb = run_recon()

    print("🔎  Validando resultado...")
    try:
        validate_recon_output(kb)
    except ValueError as e:
        sys.exit(f"❌  El JSON de Opus no es válido: {e}")

    OUTPUT_PATH.write_text(
        json.dumps(kb, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅  Guardado en: {OUTPUT_PATH}")
    print("\n📋  Resumen:")
    print(f"   • Grid: {kb['grid']['start_hour']}h – {kb['grid']['end_hour']}h")
    print(f"   • Columnas: {kb['grid']['col_offsets_pct']}")
    print(f"   • Firmas visuales: {list(kb['visual_signatures'].keys())}")
    print("\n   Ahora puedes ejecutar:  python sync.py")


if __name__ == "__main__":
    main()
