#!/usr/bin/env python3
"""
calibrate_archivex.py
─────────────────────────────────────────────────────────────────────────────
Script de calibración interactivo para Archivex Clinical.

Guía al usuario para hacer clic en 6 puntos clave de la interfaz.
Calcula automáticamente todos los valores CAL y los guarda en cal_config.json.

USO:
    python calibrate_archivex.py
"""

import json
import subprocess
import time
from pathlib import Path

import pyautogui

SCRIPT_DIR = Path(__file__).parent
CAL_FILE   = SCRIPT_DIR / "cal_config.json"


def get_window_bounds() -> tuple[int, int, int, int]:
    """Obtiene los bounds de la ventana de Archivex."""
    script = '''
    tell application "System Events"
        tell process "Archivex Clinical"
            set pos to position of window 1
            set sz  to size of window 1
            return (item 1 of pos as string) & "," & (item 2 of pos as string) & "," & (item 1 of sz as string) & "," & (item 2 of sz as string)
        end tell
    end tell
    '''
    out = subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()
    if not out or "," not in out:
        return None
    try:
        parts = [int(v.strip()) for v in out.split(",")]
        return parts[0], parts[1], parts[2], parts[3]
    except ValueError:
        return None


def wait_for_click(prompt: str, countdown: int = 3) -> tuple[int, int]:
    """Espera a que el usuario posicione el ratón y captura las coordenadas."""
    print(f"\n  📍 {prompt}")
    print(f"     Posiciona el ratón y NO LO MUEVAS. Capturando en {countdown}s...")
    for i in range(countdown, 0, -1):
        x, y = pyautogui.position()
        print(f"     [{i}] Posición actual: ({x}, {y})", end="\r")
        time.sleep(1)
    x, y = pyautogui.position()
    print(f"     ✅ Capturado: ({x}, {y})                    ")
    return x, y


def run_calibration() -> dict:
    print("\n" + "═" * 60)
    print("   Archivex Sync — Calibración de pantalla")
    print("═" * 60)
    print("""
Este script te guiará para calibrar las coordenadas de la interfaz.
Para cada punto, posiciona el ratón EXACTAMENTE sobre el lugar
indicado y espera 3 segundos sin mover el ratón.

⚠️  Requisitos:
   • Archivex Clinical abierto en VISTA SEMANAL
   • La semana debe estar visible completa
""")
    input("  Presiona ENTER cuando Archivex esté visible y listo...")

    # Detectar ventana
    print("\n🔍 Detectando ventana de Archivex...")
    bounds = get_window_bounds()
    if bounds:
        wx, wy, ww, wh = bounds
        print(f"   ✅ Ventana detectada: {ww}×{wh} en ({wx},{wy})")
    else:
        print("   ⚠️  No se detectó automáticamente. Haz clic en la ventana y pulsa ENTER.")
        input()
        wx, wy = 0, 0
        sw, sh = pyautogui.size()
        ww, wh = sw, sh

    print("""
─────────────────────────────────────────────────────────────
PASO 1/6: Esquina SUPERIOR IZQUIERDA de la rejilla
          (donde empieza la primera celda del lunes, justo
           después de la columna de horas, en la fila de arriba)
─────────────────────────────────────────────────────────────""")
    gx1, gy1 = wait_for_click("Posiciona el ratón en la esquina SUPERIOR-IZQUIERDA de la rejilla")

    print("""
─────────────────────────────────────────────────────────────
PASO 2/6: Esquina INFERIOR DERECHA de la rejilla
          (última celda del domingo, en la fila de abajo)
─────────────────────────────────────────────────────────────""")
    gx2, gy2 = wait_for_click("Posiciona el ratón en la esquina INFERIOR-DERECHA de la rejilla")

    print("""
─────────────────────────────────────────────────────────────
PASO 3/6: Hora de inicio visible en el borde izquierdo
          (p.ej. si el calendario empieza en 08:00, apunta
           al centro de esa primera franja horaria)
─────────────────────────────────────────────────────────────""")
    _, gy_start = wait_for_click("Posiciona el ratón en el centro de la PRIMERA franja horaria (08:00)")

    print("""
─────────────────────────────────────────────────────────────
PASO 4/6: Última hora visible (p.ej. 20:00 o 21:00)
─────────────────────────────────────────────────────────────""")
    _, gy_end = wait_for_click("Posiciona el ratón en el centro de la ÚLTIMA franja horaria visible")

    # Necesitamos abrir el formulario de nueva cita para calibrar el buscador
    print("""
─────────────────────────────────────────────────────────────
PASO 5/6: Campo de búsqueda de pacientes
          Haz DOBLE CLIC en cualquier slot del calendario para
          abrir el formulario "Nueva cita". Una vez abierto,
          posiciona el ratón sobre el campo de búsqueda.
─────────────────────────────────────────────────────────────""")
    input("  Presiona ENTER cuando el formulario 'Nueva cita' esté abierto...")
    sbx, sby = wait_for_click("Posiciona el ratón en el CENTRO del campo de búsqueda de pacientes")

    print("""
─────────────────────────────────────────────────────────────
PASO 6/6: Botón '+ Crear cita' o 'Guardar'
─────────────────────────────────────────────────────────────""")
    cbx, cby = wait_for_click("Posiciona el ratón sobre el botón CREAR/GUARDAR cita")

    # Calcular valores CAL
    grid_top_px    = gy1 - wy
    grid_bottom_px = wh - (gy2 - wy)
    time_col_px    = gx1 - wx
    grid_start_h = 8
    grid_end_h = grid_start_h + 12  # default 12 horas visibles

    # Búsqueda como proporción de la ventana
    search_box_x = round((sbx - wx) / ww, 3)
    search_box_y = round((sby - wy) / wh, 3)

    # Botón crear como proporción
    crear_btn_x = round((cbx - wx) / ww, 3)
    crear_btn_y = round((cby - wy) / wh, 3)

    cal = {
        "grid_top_px":    max(0, grid_top_px),
        "grid_bottom_px": max(0, grid_bottom_px),
        "time_col_px":    max(0, time_col_px),
        "grid_start_h":   grid_start_h,
        "grid_end_h":     grid_end_h,
        "search_box_x":   search_box_x,
        "search_box_y":   search_box_y,
        "first_result_dy": 85,
        "crear_btn_x":    crear_btn_x,
        "crear_btn_y":    crear_btn_y,
        "retroceder_x":   0.05,
        "avanzar_x":      0.95,
        "nav_btn_y":      0.88,
        "_meta": {
            "window": {"x": wx, "y": wy, "w": ww, "h": wh},
            "grid_corners": {
                "top_left":     [gx1, gy1],
                "bottom_right": [gx2, gy2],
            },
            "raw_search":  [sbx, sby],
            "raw_btn":     [cbx, cby],
        }
    }

    return cal


def main() -> None:
    cal = run_calibration()

    print("\n" + "═" * 60)
    print("   ✅ Calibración completada")
    print("═" * 60)
    print("\n📐 Valores calculados:\n")
    for k, v in cal.items():
        if k != "_meta":
            print(f"   {k:<20} = {v}")

    # Guardar JSON
    CAL_FILE.write_text(json.dumps(cal, indent=2))
    print(f"\n💾 Guardado en: {CAL_FILE}")

    # Preguntar si actualizar archivex_sync.py automáticamente
    print("\n¿Actualizar archivex_sync.py con estos valores? (s/n): ", end="")
    resp = input().strip().lower()
    if resp == "s":
        patch_main_script(cal)
        print("✅ archivex_sync.py actualizado.")

    print(f"""
⚠️  Revisa también manualmente:
   • grid_start_h  (hora de inicio del calendario, defecto: 8)
   • grid_end_h    (hora de fin del calendario, defecto: 20)
   • first_result_dy (píxeles debajo del buscador hasta primer resultado, defecto: 85)

Puedes editar estos en: {CAL_FILE}
Y volver a aplicar con: python calibrate_archivex.py --apply
""")


def patch_main_script(cal: dict) -> None:
    """Sobreescribe el bloque CAL en archivex_sync.py con los nuevos valores."""
    sync_file = SCRIPT_DIR / "archivex_sync.py"
    source    = sync_file.read_text(encoding="utf-8")

    new_cal = f"""CAL = {{
    "grid_top_px":    {cal['grid_top_px']},
    "grid_bottom_px": {cal['grid_bottom_px']},
    "time_col_px":    {cal['time_col_px']},
    "grid_start_h":   {cal['grid_start_h']},
    "grid_end_h":     {cal['grid_end_h']},
    "search_box_x":   {cal['search_box_x']},
    "search_box_y":   {cal['search_box_y']},
    "first_result_dy": {cal['first_result_dy']},
    "crear_btn_x":    {cal['crear_btn_x']},
    "crear_btn_y":    {cal['crear_btn_y']},
    "retroceder_x":   {cal['retroceder_x']},
    "avanzar_x":      {cal['avanzar_x']},
    "nav_btn_y":      {cal['nav_btn_y']},
}}"""

    # Reemplazar bloque CAL
    import re
    pattern = r"CAL\s*=\s*\{[^}]+\}"
    updated = re.sub(pattern, new_cal, source, flags=re.DOTALL)
    sync_file.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--apply":
        # Solo aplicar un cal_config.json existente
        if not CAL_FILE.exists():
            print(f"❌ No encontré {CAL_FILE}. Ejecuta primero sin --apply.")
            sys.exit(1)
        cal = json.loads(CAL_FILE.read_text())
        patch_main_script(cal)
        print("✅ Valores aplicados a archivex_sync.py desde cal_config.json")
    else:
        main()
