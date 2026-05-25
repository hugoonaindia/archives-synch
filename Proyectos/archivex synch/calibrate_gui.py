#!/usr/bin/env python3
"""
calibrate_gui.py — Calibración visual paso a paso para Archivex Sync

Guía al usuario por todos los puntos de calibración necesarios,
muestra coordenadas en tiempo real y persiste los datos en:
  ~/.config/archivex-sync/cal_config.json

USO:
    python calibrate_gui.py
    (o desde archivex_sync.py pulsando [C] al inicio)
"""

import json
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Optional

import pyautogui
from pynput import keyboard as pynput_keyboard

# ── Rutas ────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".config" / "archivex-sync"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CAL_FILE   = CONFIG_DIR / "cal_config.json"

# ── Colores ───────────────────────────────────────────────────────────────────

C = {
    "bg":        "#0f1117",
    "card":      "#1a1d27",
    "border":    "#2a2d3e",
    "primary":   "#7c6af7",
    "primary_h": "#9d8fff",
    "success":   "#22c55e",
    "warning":   "#f59e0b",
    "text":      "#e2e8f0",
    "muted":     "#64748b",
    "capture":   "#f97316",
    "capture_h": "#fb923c",
    "done":      "#10b981",
}

# ── Definición de pasos ───────────────────────────────────────────────────────

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

STEPS: list[dict] = [
    {
        "id":      "intro",
        "title":   "Bienvenido a la calibración",
        "icon":    "🎯",
        "type":    "intro",
        "desc":    (
            "Este asistente te guiará paso a paso para calibrar las coordenadas "
            "de la interfaz de Archivex Clinical.\n\n"
            "Antes de continuar asegúrate de que:\n"
            "  • Archivex Clinical está abierto\n"
            "  • Estás en la VISTA SEMANAL\n"
            "  • La semana completa es visible\n\n"
            "Pulsa → para comenzar."
        ),
    },
    {
        "id":    "grid_tl",
        "title": "Esquina superior-izquierda del grid",
        "icon":  "↖",
        "type":  "capture_point",
        "desc":  (
            "Coloca el ratón en la esquina SUPERIOR-IZQUIERDA de la rejilla del "
            "calendario.\n\n"
            "Es el punto donde empieza la primera celda del LUNES, justo a la "
            "derecha de la columna de horas (08:00, 09:00…).\n\n"
            "Posiciona el ratón allí y pulsa CAPTURAR."
        ),
        "captures": ["x", "y"],
        "result_key": "grid_tl",
        "hint":  "Justo donde el grid empieza, tras la columna de horas",
    },
    {
        "id":    "grid_br",
        "title": "Esquina inferior-derecha del grid",
        "icon":  "↘",
        "type":  "capture_point",
        "desc":  (
            "Coloca el ratón en la esquina INFERIOR-DERECHA de la rejilla.\n\n"
            "Es el último píxel visible de la celda del DOMINGO, en la fila "
            "más baja del calendario."
        ),
        "captures": ["x", "y"],
        "result_key": "grid_br",
        "hint":  "Última celda visible del domingo",
    },
    {
        "id":    "hour_start",
        "title": "Primera franja horaria visible",
        "icon":  "🕗",
        "type":  "capture_y_input",
        "desc":  (
            "Coloca el ratón en el CENTRO VERTICAL de la primera franja horaria "
            "visible en el calendario.\n\n"
            "Ej: si el calendario empieza a las 08:00, apunta al centro de esa "
            "fila horizontal.\n\n"
            "Luego indica qué hora es en el campo inferior."
        ),
        "captures": ["y"],
        "result_key": "hour_start",
        "input_label": "¿Qué hora indica? (ej: 8)",
        "input_default": "8",
        "hint": "Centro vertical de la primera hora",
    },
    {
        "id":    "hour_end",
        "title": "Última franja horaria visible",
        "icon":  "🕗",
        "type":  "capture_y_input",
        "desc":  (
            "Coloca el ratón en el CENTRO VERTICAL de la ÚLTIMA franja horaria "
            "visible.\n\n"
            "Ej: si el calendario termina a las 20:00, apunta al centro de esa fila."
        ),
        "captures": ["y"],
        "result_key": "hour_end",
        "input_label": "¿Qué hora indica? (ej: 20)",
        "input_default": "20",
        "hint": "Centro vertical de la última hora",
    },
]

# Añadir un paso por cada día de la semana
for _i, _dia in enumerate(DIAS):
    STEPS.append({
        "id":      f"col_{_dia.lower()[:3]}",
        "title":   f"Columna {_dia}",
        "icon":    "📅",
        "type":    "capture_x",
        "desc":    (
            f"Coloca el ratón en el CENTRO HORIZONTAL de la columna del {_dia.upper()}.\n\n"
            "La altura no importa — solo necesitamos la posición izquierda-derecha "
            "para saber exactamente dónde hacer clic en ese día.\n\n"
            f"({_i + 1} de 7 columnas)"
        ),
        "captures":    ["x"],
        "result_key":  f"col_{_dia.lower()[:3]}",
        "day_index":   _i,
        "hint":        f"Centro horizontal de la columna del {_dia}",
    })

STEPS += [
    {
        "id":    "search_box",
        "title": "Campo de búsqueda de pacientes",
        "icon":  "🔍",
        "type":  "capture_point",
        "desc":  (
            "Abre el formulario 'Nueva cita' haciendo doble clic en un slot del "
            "calendario. Una vez abierto el formulario:\n\n"
            "Coloca el ratón en el CENTRO del campo de búsqueda de pacientes "
            "(donde se escribe el nombre) y pulsa CAPTURAR."
        ),
        "captures":   ["x", "y"],
        "result_key": "search_box",
        "hint":       "Campo de búsqueda dentro del formulario",
    },
    {
        "id":    "crear_btn",
        "title": "Botón 'Crear cita'",
        "icon":  "✅",
        "type":  "capture_point",
        "desc":  (
            "Con el formulario aún abierto, coloca el ratón sobre el botón "
            "CREAR CITA (o Guardar) y pulsa CAPTURAR.\n\n"
            "Puedes cerrar el formulario sin guardar después."
        ),
        "captures":   ["x", "y"],
        "result_key": "crear_btn",
        "hint":       "Botón de guardar/crear dentro del formulario",
    },
    {
        "id":    "summary",
        "title": "Resumen y guardar",
        "icon":  "💾",
        "type":  "summary",
        "desc":  "Verifica los valores capturados y guarda la calibración.",
    },
]

TOTAL_STEPS = len(STEPS)


# ── App principal ─────────────────────────────────────────────────────────────

class CalibrationApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root       = root
        self.step_idx   = 0
        self.results:   dict = {}
        self.countdown_job: Optional[str] = None
        self.countdown_val  = 0
        self._mouse_job: Optional[str] = None
        self._kb_listener: Optional[pynput_keyboard.Listener] = None

        self._setup_window()
        self._build_ui()
        self._update_mouse_loop()
        self._start_keyboard_listener()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.render_step()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.root.title("Archivex Sync — Calibración")
        self.root.configure(bg=C["bg"])
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.geometry("460x720+40+40")

        # Fuentes
        self.f_title  = tkfont.Font(family="Helvetica Neue", size=16, weight="bold")
        self.f_body   = tkfont.Font(family="Helvetica Neue", size=13)
        self.f_mono   = tkfont.Font(family="Menlo",          size=14, weight="bold")
        self.f_small  = tkfont.Font(family="Helvetica Neue", size=11)
        self.f_icon   = tkfont.Font(family="Helvetica Neue", size=32)

    def _build_ui(self) -> None:
        root = self.root

        # ── Barra superior ───────────────────────────────────────────────────
        top = tk.Frame(root, bg=C["card"], height=56)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="🎯  Archivex Sync — Calibración",
                 bg=C["card"], fg=C["text"],
                 font=tkfont.Font(family="Helvetica Neue", size=13, weight="bold"),
                 anchor="w", padx=16).pack(side="left", fill="y")

        # ── Progreso ─────────────────────────────────────────────────────────
        prog_frame = tk.Frame(root, bg=C["bg"], pady=10)
        prog_frame.pack(fill="x", padx=16)

        self.prog_label = tk.Label(prog_frame, text="", bg=C["bg"],
                                   fg=C["muted"], font=self.f_small, anchor="e")
        self.prog_label.pack(side="right")

        self.progress = ttk.Progressbar(prog_frame, length=420,
                                        mode="determinate", maximum=TOTAL_STEPS - 1)
        self.progress.pack(side="left", fill="x", expand=True)

        # ── Tarjeta de paso ───────────────────────────────────────────────────
        self.card = tk.Frame(root, bg=C["card"], padx=20, pady=20)
        self.card.pack(fill="both", padx=16, pady=(0, 8))

        # Icono + título
        header = tk.Frame(self.card, bg=C["card"])
        header.pack(fill="x", pady=(0, 12))

        self.lbl_icon  = tk.Label(header, text="", bg=C["card"],
                                  fg=C["primary"], font=self.f_icon, width=2)
        self.lbl_icon.pack(side="left")

        self.lbl_title = tk.Label(header, text="", bg=C["card"],
                                  fg=C["text"], font=self.f_title,
                                  anchor="w", justify="left", wraplength=360)
        self.lbl_title.pack(side="left", padx=(10, 0))

        # Descripción
        self.lbl_desc = tk.Label(self.card, text="", bg=C["card"],
                                 fg=C["text"], font=self.f_body,
                                 anchor="w", justify="left", wraplength=420)
        self.lbl_desc.pack(fill="x", pady=(0, 14))

        # Panel de coordenadas en vivo
        self.coord_frame = tk.Frame(self.card, bg=C["border"], pady=10, padx=16)
        self.coord_frame.pack(fill="x", pady=(0, 12))

        tk.Label(self.coord_frame, text="📍  Posición del ratón",
                 bg=C["border"], fg=C["muted"], font=self.f_small).pack(anchor="w")

        self.lbl_coords = tk.Label(self.coord_frame, text="X: —    Y: —",
                                   bg=C["border"], fg=C["primary"], font=self.f_mono)
        self.lbl_coords.pack(anchor="w", pady=(4, 0))

        self.lbl_hint = tk.Label(self.coord_frame, text="",
                                 bg=C["border"], fg=C["muted"], font=self.f_small)
        self.lbl_hint.pack(anchor="w", pady=(2, 0))

        # Input extra (para pasos de hora)
        self.input_frame = tk.Frame(self.card, bg=C["card"])
        self.input_frame.pack(fill="x", pady=(0, 8))

        self.lbl_input = tk.Label(self.input_frame, text="",
                                  bg=C["card"], fg=C["text"], font=self.f_body)
        self.lbl_input.pack(side="left")

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self.input_frame, textvariable=self.entry_var,
                              font=self.f_mono, width=6,
                              bg=C["border"], fg=C["text"],
                              insertbackground=C["text"],
                              relief="flat", bd=4)
        self.entry.pack(side="left", padx=(8, 0))

        # Botón capturar + countdown
        self.btn_capture = tk.Button(
            self.card, text="📍  Capturar  [ ESPACIO ]",
            font=tkfont.Font(family="Helvetica Neue", size=14, weight="bold"),
            bg=C["capture"], fg="white", activebackground=C["capture_h"],
            relief="flat", bd=0, padx=16, pady=10,
            cursor="hand2", command=self.start_countdown,
        )
        self.btn_capture.pack(fill="x", pady=(4, 0))

        # Badge de capturado
        self.lbl_captured = tk.Label(self.card, text="",
                                     bg=C["card"], fg=C["success"],
                                     font=tkfont.Font(family="Helvetica Neue",
                                                      size=12, weight="bold"))
        self.lbl_captured.pack(pady=(6, 0))

        # ── Panel de resultados ───────────────────────────────────────────────
        res_outer = tk.Frame(root, bg=C["bg"])
        res_outer.pack(fill="both", padx=16, expand=True)

        tk.Label(res_outer, text="Valores capturados",
                 bg=C["bg"], fg=C["muted"], font=self.f_small,
                 anchor="w").pack(fill="x")

        self.results_frame = tk.Frame(res_outer, bg=C["card"], padx=10, pady=8)
        self.results_frame.pack(fill="both", expand=True)

        self.results_text = tk.Text(
            self.results_frame, bg=C["card"], fg=C["text"],
            font=tkfont.Font(family="Menlo", size=10),
            relief="flat", bd=0, state="disabled",
            height=8, wrap="none",
        )
        self.results_text.pack(fill="both", expand=True)

        # ── Navegación ────────────────────────────────────────────────────────
        nav = tk.Frame(root, bg=C["bg"], pady=10)
        nav.pack(fill="x", padx=16)

        self.btn_back = tk.Button(
            nav, text="← Anterior",
            bg=C["border"], fg=C["text"],
            activebackground=C["card"],
            relief="flat", bd=0, padx=14, pady=8,
            font=self.f_body, cursor="hand2",
            command=self.go_back,
        )
        self.btn_back.pack(side="left")

        self.btn_next = tk.Button(
            nav, text="Siguiente →",
            bg=C["primary"], fg="white",
            activebackground=C["primary_h"],
            relief="flat", bd=0, padx=18, pady=8,
            font=tkfont.Font(family="Helvetica Neue", size=13, weight="bold"),
            cursor="hand2",
            command=self.go_next,
        )
        self.btn_next.pack(side="right")

        self.btn_save = tk.Button(
            nav, text="💾  Guardar calibración",
            bg=C["done"], fg="white",
            activebackground="#059669",
            relief="flat", bd=0, padx=18, pady=8,
            font=tkfont.Font(family="Helvetica Neue", size=13, weight="bold"),
            cursor="hand2",
            command=self.save_calibration,
        )
        self.btn_save.pack(side="right")

    # ── Mouse tracking ────────────────────────────────────────────────────────

    def _update_mouse_loop(self) -> None:
        try:
            x, y = pyautogui.position()
            self.lbl_coords.config(text=f"X: {x:<6}  Y: {y:<6}")
        except Exception:
            pass
        self._mouse_job = self.root.after(80, self._update_mouse_loop)

    # ── Teclado global ────────────────────────────────────────────────────────

    def _start_keyboard_listener(self) -> None:
        def on_press(key: pynput_keyboard.Key) -> None:
            if key == pynput_keyboard.Key.space:
                # thread-safe: schedule en el hilo de tkinter
                self.root.after(0, self._on_space_pressed)
            elif key == pynput_keyboard.Key.esc:
                self.root.after(0, self._cancel_countdown)

        self._kb_listener = pynput_keyboard.Listener(on_press=on_press, daemon=True)
        self._kb_listener.start()

    def _on_space_pressed(self) -> None:
        step = STEPS[self.step_idx]
        if step["type"] in ("capture_point", "capture_x", "capture_y_input"):
            self.start_countdown()

    def _cancel_countdown(self) -> None:
        if self.countdown_job:
            self.root.after_cancel(self.countdown_job)
            self.countdown_job = None
            self.btn_capture.config(text="📍  Capturar  [ ESPACIO ]")

    def _on_close(self) -> None:
        if self._kb_listener:
            self._kb_listener.stop()
        self.root.destroy()

    # ── Render ────────────────────────────────────────────────────────────────

    def render_step(self) -> None:
        step = STEPS[self.step_idx]

        # Progreso
        pct = max(0, self.step_idx)
        self.progress["value"] = pct
        self.prog_label.config(
            text=f"Paso {self.step_idx + 1} / {TOTAL_STEPS}"
        )

        # Contenido
        self.lbl_icon.config(text=step["icon"])
        self.lbl_title.config(text=step["title"])
        self.lbl_desc.config(text=step["desc"])
        self.lbl_captured.config(text="")
        self.lbl_hint.config(text=step.get("hint", ""))

        stype = step["type"]

        # Coordenadas + captura
        show_coord  = stype in ("capture_point", "capture_x", "capture_y_input")
        show_input  = stype == "capture_y_input"
        show_cap    = show_coord

        self.coord_frame.pack(fill="x", pady=(0, 12)) if show_coord else self.coord_frame.pack_forget()
        self.btn_capture.pack(fill="x", pady=(4, 0)) if show_cap else self.btn_capture.pack_forget()

        if show_input:
            self.lbl_input.config(text=step.get("input_label", "Valor:"))
            self.entry_var.set(step.get("input_default", ""))
            self.input_frame.pack(fill="x", pady=(0, 8))
        else:
            self.input_frame.pack_forget()

        # Resumen
        if stype == "summary":
            self.coord_frame.pack_forget()
            self.btn_capture.pack_forget()
            self.input_frame.pack_forget()
            self._render_summary_in_desc()

        # Marca ya capturado si existe
        key = step.get("result_key")
        if key and key in self.results:
            self._show_captured_badge(key)

        # Botones nav
        self.btn_back.config(state="normal" if self.step_idx > 0 else "disabled")

        is_last = self.step_idx == TOTAL_STEPS - 1
        self.btn_next.pack_forget() if is_last else self.btn_next.pack(side="right")
        self.btn_save.pack(side="right") if is_last else self.btn_save.pack_forget()

        # Resetear countdown si había uno activo
        if self.countdown_job:
            self.root.after_cancel(self.countdown_job)
            self.countdown_job = None
        self.btn_capture.config(text="📍  Capturar  [ ESPACIO ]")

        self._refresh_results_panel()

    def _show_captured_badge(self, key: str) -> None:
        val = self.results.get(key)
        if val is None:
            return
        if isinstance(val, (list, tuple)):
            txt = f"✅  Capturado: ({', '.join(str(v) for v in val)})"
        else:
            txt = f"✅  Capturado: {val}"
        self.lbl_captured.config(text=txt)

    def _render_summary_in_desc(self) -> None:
        total   = len([s for s in STEPS if s.get("result_key")])
        captured = len(self.results)
        missing  = total - captured
        if missing:
            self.lbl_desc.config(
                text=f"⚠️  Faltan {missing} punto(s) por capturar.\n"
                     "Vuelve atrás con ← para completarlos antes de guardar.\n\n"
                     + self._summary_text()
            )
        else:
            self.lbl_desc.config(
                text="✅  Todos los puntos capturados. Pulsa Guardar.\n\n"
                     + self._summary_text()
            )

    def _summary_text(self) -> str:
        lines = []
        for step in STEPS:
            key = step.get("result_key")
            if not key:
                continue
            val = self.results.get(key)
            icon = "✅" if val is not None else "⬜"
            if isinstance(val, (list, tuple)):
                v = f"({', '.join(str(x) for x in val)})"
            elif val is not None:
                v = str(val)
            else:
                v = "—"
            lines.append(f"{icon} {step['title']}: {v}")
        return "\n".join(lines)

    def _refresh_results_panel(self) -> None:
        lines = []
        for step in STEPS:
            key = step.get("result_key")
            if not key:
                continue
            val = self.results.get(key)
            if val is None:
                continue
            if isinstance(val, (list, tuple)):
                v = f"({', '.join(str(x) for x in val)})"
            else:
                v = str(val)
            lines.append(f"  {step['title'][:28]:<28}  {v}")

        self.results_text.config(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("end", "\n".join(lines) if lines else "  (ninguno aún)")
        self.results_text.config(state="disabled")

    # ── Countdown + captura ───────────────────────────────────────────────────

    def start_countdown(self) -> None:
        if self.countdown_job:
            return
        self.countdown_val = 4
        self._tick_countdown()

    def _tick_countdown(self) -> None:
        n = self.countdown_val
        if n > 0:
            self.btn_capture.config(text=f"📍  Capturando en  {n}…")
            self.countdown_val -= 1
            self.countdown_job = self.root.after(1000, self._tick_countdown)
        else:
            self.countdown_job = None
            self._do_capture()
            self.btn_capture.config(text="📍  Capturar  [ ESPACIO ]")

    def _do_capture(self) -> None:
        step = STEPS[self.step_idx]
        key  = step.get("result_key")
        if not key:
            return

        x, y = pyautogui.position()
        stype = step["type"]

        if stype == "capture_point":
            self.results[key] = [x, y]
        elif stype == "capture_x":
            self.results[key] = x
        elif stype == "capture_y_input":
            hour_raw = self.entry_var.get().strip()
            try:
                hour = int(hour_raw)
            except ValueError:
                messagebox.showwarning("Valor inválido", f"'{hour_raw}' no es un número válido.")
                return
            self.results[key] = {"y": y, "hour": hour}

        self._show_captured_badge(key)
        self._refresh_results_panel()

    # ── Navegación ────────────────────────────────────────────────────────────

    def go_next(self) -> None:
        if self.step_idx < TOTAL_STEPS - 1:
            self.step_idx += 1
            self.render_step()

    def go_back(self) -> None:
        if self.step_idx > 0:
            self.step_idx -= 1
            self.render_step()

    # ── Guardar ───────────────────────────────────────────────────────────────

    def save_calibration(self) -> None:
        r = self.results

        # Validar mínimos obligatorios
        required = ["grid_tl", "grid_br", "hour_start", "hour_end",
                    "search_box", "crear_btn"]
        day_keys = [f"col_{d.lower()[:3]}" for d in DIAS]
        required += day_keys

        missing = [k for k in required if k not in r]
        if missing:
            names = [s["title"] for s in STEPS if s.get("result_key") in missing]
            messagebox.showerror(
                "Calibración incompleta",
                "Faltan los siguientes puntos:\n\n" + "\n".join(f"• {n}" for n in names)
            )
            return

        # Extraer window bounds
        wx, wy = self._detect_window_origin()

        tl = r["grid_tl"]
        br = r["grid_br"]

        col_centers = [r[k] for k in day_keys]

        cal = {
            "grid_top_px":     max(0, tl[1] - wy),
            "grid_bottom_px":  max(0, (wy + self._window_h()) - br[1]),
            "grid_start_h":    r["hour_start"]["hour"],
            "grid_end_h":      r["hour_end"]["hour"],
            "col_centers_x":   col_centers,
            "search_box_x":    round((r["search_box"][0] - wx) / self._window_w(), 3),
            "search_box_y":    round((r["search_box"][1] - wy) / self._window_h(), 3),
            "first_result_dy": 85,
            "crear_btn_x":     round((r["crear_btn"][0] - wx) / self._window_w(), 3),
            "crear_btn_y":     round((r["crear_btn"][1] - wy) / self._window_h(), 3),
            "retroceder_x":    0.05,
            "avanzar_x":       0.95,
            "nav_btn_y":       0.88,
            "_meta": {
                "window":       {"x": wx, "y": wy,
                                 "w": self._window_w(), "h": self._window_h()},
                "raw_results":  {k: (list(v) if isinstance(v, list) else v)
                                 for k, v in r.items()},
                "calibrated_at": datetime.now().isoformat(),
            },
        }

        CAL_FILE.write_text(json.dumps(cal, indent=2, ensure_ascii=False))

        messagebox.showinfo(
            "✅ Calibración guardada",
            f"Los datos se guardaron en:\n{CAL_FILE}\n\nPuedes cerrar esta ventana."
        )
        self.root.destroy()

    # ── Helpers de ventana ────────────────────────────────────────────────────

    def _get_archivex_bounds(self) -> Optional[tuple[int, int, int, int]]:
        script = '''
        tell application "System Events"
            repeat with proc in (every process whose background only is false)
                set n to name of proc
                if n contains "Archivex" or n contains "Archive" then
                    tell proc
                        set pos to position of window 1
                        set sz  to size of window 1
                        return (item 1 of pos as string) & "," & (item 2 of pos as string) & "," & (item 1 of sz as string) & "," & (item 2 of sz as string)
                    end tell
                end if
            end repeat
            return ""
        end tell
        '''
        out = subprocess.run(["osascript", "-e", script],
                             capture_output=True, text=True).stdout.strip()
        if out and "," in out:
            try:
                p = [int(v.strip()) for v in out.split(",")]
                return p[0], p[1], p[2], p[3]
            except ValueError:
                pass
        return None

    def _detect_window_origin(self) -> tuple[int, int]:
        b = self._get_archivex_bounds()
        return (b[0], b[1]) if b else (0, 0)

    def _window_w(self) -> int:
        b = self._get_archivex_bounds()
        return b[2] if b else pyautogui.size()[0]

    def _window_h(self) -> int:
        b = self._get_archivex_bounds()
        return b[3] if b else pyautogui.size()[1]


# ── Entry point ───────────────────────────────────────────────────────────────

def run_calibration_gui() -> None:
    """Lanza la GUI de calibración. Bloqueante hasta que el usuario cierra."""
    root = tk.Tk()
    CalibrationApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_calibration_gui()
