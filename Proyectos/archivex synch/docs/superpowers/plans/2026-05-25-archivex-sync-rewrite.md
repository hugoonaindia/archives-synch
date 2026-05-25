# Archivex Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two Python scripts — `recon.py` (Opus 4.7 maps Archivex UI once) and `sync.py` (monolith that reads Google Calendar and enters appointments into Archivex, skipping Mon/Wed).

**Architecture:** `recon.py` takes screenshots of Archivex, calls Opus 4.7, and saves `~/.config/archivex-sync/ui_knowledge.json` with relative coordinates and visual signatures. `sync.py` loads that file, reads current week from Google Calendar, filters Mon/Wed, and drives Archivex via pyautogui — using Haiku with prompt caching only for the 3 semantic verification checkpoints.

**Tech Stack:** Python 3.12+, anthropic SDK (Opus 4.7 + Haiku w/ prompt caching), pyautogui, Pillow, google-api-python-client, google-auth-oauthlib, pytest.

---

## File Map

```
recon.py                              ← reconnaissance script (run once)
sync.py                               ← monolithic sync script (run weekly)
requirements.txt                      ← all dependencies
pyproject.toml                        ← ruff + pytest config
CLAUDE.md                             ← project instructions
tests/
  __init__.py
  test_sync.py                        ← unit tests for sync.py sections
  test_recon.py                       ← unit tests for recon.py validation
~/.config/archivex-sync/
  ui_knowledge.json                   ← produced by recon.py (never committed)
  token_calendar.json                 ← Google OAuth token (never committed)
```

`credentials.json` lives in the project root (already present, already in .gitignore).

---

## Task 1: Project foundation

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `CLAUDE.md`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
anthropic>=0.40.0
pyautogui>=0.9.54
Pillow>=10.2.0
pyscreeze>=0.1.30
google-auth>=2.28.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.108.0
pytest>=8.0.0
pytest-cov>=5.0.0
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--tb=short -q"
```

- [ ] **Step 3: Create `CLAUDE.md`**

```markdown
# Archivex Sync

**Goal**: Leer Google Calendar (semana actual) y crear las citas en Archivex Clinical via pyautogui. Excluye lunes y miércoles.

**Stack**: Python 3.12+, anthropic SDK, pyautogui, Google Calendar API

**Tests**: `pytest -q --tb=short`

**Lint**: `ruff check .`

## Dos scripts

- `recon.py` — ejecutar UNA VEZ con Archivex abierto en vista semanal
- `sync.py` — ejecutar cada semana

## Seguridad

- `credentials.json`, `token_*.json`, `ui_knowledge.json` NUNCA se commitean
- Están en `.gitignore`
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty file)

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 6: Verify ruff and pytest are available**

```bash
ruff check . && pytest --collect-only
```

Expected: no errors, "no tests ran" message.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pyproject.toml CLAUDE.md tests/__init__.py
git commit -m "chore: project foundation — deps, lint, test config"
```

---

## Task 2: Appointment dataclass + Google Calendar reader + Mon/Wed filter

**Files:**
- Create: `sync.py` (first sections only: imports, constants, types, calendar reader)
- Create: `tests/test_sync.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sync.py`:

```python
"""Unit tests for sync.py."""
import sys
from datetime import date
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture(autouse=True)
def mock_pyautogui():
    sys.modules["pyautogui"] = Mock()
    yield
    for mod in ["sync"]:
        sys.modules.pop(mod, None)


@pytest.fixture
def sync(tmp_path):
    """Load sync module after mocks are in place."""
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    import sync as s
    return s


class TestAppointment:
    def test_creation(self, sync):
        appt = sync.Appointment(
            patient="Ana García",
            date=date(2026, 5, 26),
            start_time="09:00",
            end_time="10:00",
            day_offset=1,   # Tuesday
            hour=9,
            minute=0,
        )
        assert appt.patient == "Ana García"
        assert appt.day_offset == 1


class TestGetWeekAppointments:
    def _make_service(self, items):
        svc = MagicMock()
        svc.events().list().execute.return_value = {"items": items}
        return svc

    def test_empty_calendar(self, sync):
        svc = self._make_service([])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert result == []

    def test_parses_timed_event(self, sync):
        svc = self._make_service([{
            "summary": "Patient: Hugo",
            "start": {"dateTime": "2026-05-26T09:00:00+02:00"},
            "end":   {"dateTime": "2026-05-26T10:00:00+02:00"},
        }])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert len(result) == 1
        assert result[0].patient == "Patient: Hugo"
        assert result[0].start_time == "09:00"
        assert result[0].day_offset == 1   # Tuesday

    def test_skips_all_day_events(self, sync):
        svc = self._make_service([{
            "summary": "Holiday",
            "start": {"date": "2026-05-26"},
            "end":   {"date": "2026-05-27"},
        }])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert result == []

    def test_skips_monday(self, sync):
        # 2026-05-25 is a Monday
        svc = self._make_service([{
            "summary": "Patient: Lunes",
            "start": {"dateTime": "2026-05-25T10:00:00+02:00"},
            "end":   {"dateTime": "2026-05-25T11:00:00+02:00"},
        }])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert result == []

    def test_skips_wednesday(self, sync):
        # 2026-05-27 is a Wednesday
        svc = self._make_service([{
            "summary": "Patient: Miércoles",
            "start": {"dateTime": "2026-05-27T10:00:00+02:00"},
            "end":   {"dateTime": "2026-05-27T11:00:00+02:00"},
        }])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert result == []

    def test_keeps_tuesday_and_thursday(self, sync):
        svc = self._make_service([
            {
                "summary": "Patient: Martes",
                "start": {"dateTime": "2026-05-26T09:00:00+02:00"},
                "end":   {"dateTime": "2026-05-26T10:00:00+02:00"},
            },
            {
                "summary": "Patient: Jueves",
                "start": {"dateTime": "2026-05-28T11:00:00+02:00"},
                "end":   {"dateTime": "2026-05-28T12:00:00+02:00"},
            },
        ])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert len(result) == 2
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_sync.py -v
```

Expected: `ModuleNotFoundError: No module named 'sync'`

- [ ] **Step 3: Create `sync.py` with the calendar sections**

```python
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
from anthropic import Anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ─── §2 CONSTANTS ────────────────────────────────────────────────────────────
CONFIG_DIR    = Path.home() / ".config" / "archivex-sync"
KNOWLEDGE     = CONFIG_DIR / "ui_knowledge.json"
TOKEN_PATH    = CONFIG_DIR / "token_calendar.json"
CREDS_PATH    = Path("credentials.json")
SCOPES        = ["https://www.googleapis.com/auth/calendar.readonly"]
MODEL_VERIFY  = os.getenv("ARCHIVEX_VERIFY_MODEL", "claude-haiku-4-5")
SKIP_DAYS     = {0, 2}   # Monday=0, Wednesday=2
LOG_PATH      = CONFIG_DIR / "sync.log"

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
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
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
        if "dateTime" not in start:       # all-day event → skip
            continue
        dt_start = datetime.fromisoformat(start["dateTime"])
        dt_end   = datetime.fromisoformat(end["dateTime"])
        if dt_start.weekday() in SKIP_DAYS:   # Mon or Wed → skip
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
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_sync.py -v
```

Expected: 8 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat(sync): Appointment dataclass + Calendar reader + Mon/Wed filter"
```

---

## Task 3: Knowledge base loader + coordinate calculator

**Files:**
- Modify: `sync.py` (add §5 Knowledge Base section)
- Modify: `tests/test_sync.py` (add TestKnowledge class)

- [ ] **Step 1: Write failing tests — append to `tests/test_sync.py`**

```python
class TestKnowledge:
    KB_FIXTURE = {
        "version": 1,
        "recon_date": "2026-05-25",
        "window": {"x": 0, "y": 0, "w": 1440, "h": 900},
        "grid": {
            "start_hour": 8,
            "end_hour": 20,
            "col_offsets_pct": [0.10, 0.24, 0.38, 0.52, 0.66, 0.80, 0.94],
            "first_row_y_pct": 0.10,
            "last_row_y_pct": 0.98,
        },
        "elements": {
            "nav_prev_pct":       {"x": 0.05, "y": 0.04},
            "nav_next_pct":       {"x": 0.95, "y": 0.04},
            "patient_search_pct": {"x": 0.45, "y": 0.35},
            "first_result_pct":   {"x": 0.45, "y": 0.42},
            "save_btn_pct":       {"x": 0.65, "y": 0.85},
        },
        "visual_signatures": {
            "empty_slot":      "slot vacío sin color de fondo",
            "occupied_slot":   "slot con fondo coloreado y nombre de paciente",
            "form_open":       "modal de nueva cita visible con campo de búsqueda",
            "patient_selected": "nombre de paciente relleno en el campo",
            "appointment_saved": "formulario cerrado, cita visible en el calendario",
        },
    }

    def test_validate_knowledge_valid(self, sync):
        sync.validate_knowledge(self.KB_FIXTURE)   # should not raise

    def test_validate_knowledge_missing_key(self, sync):
        bad = {k: v for k, v in self.KB_FIXTURE.items() if k != "grid"}
        with pytest.raises(KeyError):
            sync.validate_knowledge(bad)

    def test_abs_coords_top_left(self, sync):
        x, y = sync.abs_coords(0.0, 0.0, wx=100, wy=50, ww=1440, wh=900)
        assert x == 100
        assert y == 50

    def test_abs_coords_center(self, sync):
        x, y = sync.abs_coords(0.5, 0.5, wx=0, wy=0, ww=1000, wh=800)
        assert x == 500
        assert y == 400

    def test_slot_coords_first_col_start_hour(self, sync):
        kb = self.KB_FIXTURE
        x, y = sync.slot_coords(
            day_offset=0, hour=8, minute=0,
            kb=kb, wx=0, wy=0, ww=1440, wh=900,
        )
        # col 0 → x_pct=0.10 → x=144
        assert x == int(0.10 * 1440)
        # hour=8 = start → y at first_row_y_pct → 0.10 * 900 = 90
        assert y == int(0.10 * 900)

    def test_slot_coords_last_col_end_hour(self, sync):
        kb = self.KB_FIXTURE
        x, y = sync.slot_coords(
            day_offset=6, hour=20, minute=0,
            kb=kb, wx=0, wy=0, ww=1440, wh=900,
        )
        assert x == int(0.94 * 1440)
        assert y == int(0.98 * 900)
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_sync.py::TestKnowledge -v
```

Expected: `AttributeError: module 'sync' has no attribute 'validate_knowledge'`

- [ ] **Step 3: Add §5 Knowledge Base to `sync.py`**

Add after the `get_week_appointments` function:

```python
# ─── §5 KNOWLEDGE BASE ───────────────────────────────────────────────────────
_REQUIRED_KEYS = {"version", "grid", "elements", "visual_signatures"}
_REQUIRED_ELEMENTS = {"nav_prev_pct", "nav_next_pct", "patient_search_pct",
                      "first_result_pct", "save_btn_pct"}
_REQUIRED_GRID = {"start_hour", "end_hour", "col_offsets_pct",
                  "first_row_y_pct", "last_row_y_pct"}


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
    """Carga ui_knowledge.json desde ~/.config/archivex-sync/. Aborta si no existe."""
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
    row_span = g["last_row_y_pct"] - g["first_row_y_pct"]
    y_pct = g["first_row_y_pct"] + (
        (hour - g["start_hour"] + minute / 60.0) / total_hours * row_span
    )
    return abs_coords(x_pct, y_pct, wx, wy, ww, wh)
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
pytest tests/test_sync.py -v
```

Expected: all PASSED (8 calendar + 6 knowledge = 14 total).

- [ ] **Step 5: Lint**

```bash
ruff check .
```

Expected: no issues.

- [ ] **Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat(sync): knowledge base loader + coordinate calculator"
```

---

## Task 4: Archivex window detection via AppleScript

**Files:**
- Modify: `sync.py` (add §6 Window Detection)
- Modify: `tests/test_sync.py` (add TestWindowDetection)

- [ ] **Step 1: Write failing tests — append to `tests/test_sync.py`**

```python
class TestWindowDetection:
    def test_get_window_bounds_parses_output(self, sync, monkeypatch):
        mock_run = MagicMock()
        mock_run.return_value.stdout = "100,50,1440,900\n"
        monkeypatch.setattr("subprocess.run", mock_run)
        wx, wy, ww, wh = sync.get_window_bounds()
        assert wx == 100
        assert wy == 50
        assert ww == 1440
        assert wh == 900

    def test_get_window_bounds_raises_if_not_open(self, sync, monkeypatch):
        mock_run = MagicMock()
        mock_run.return_value.stdout = ""
        monkeypatch.setattr("subprocess.run", mock_run)
        with pytest.raises(RuntimeError, match="Archivex"):
            sync.get_window_bounds()
```

- [ ] **Step 2: Run — confirm fail**

```bash
pytest tests/test_sync.py::TestWindowDetection -v
```

Expected: `AttributeError: module 'sync' has no attribute 'get_window_bounds'`

- [ ] **Step 3: Add §6 to `sync.py`**

```python
# ─── §6 ARCHIVEX WINDOW ──────────────────────────────────────────────────────
_APPLESCRIPT_BOUNDS = """\
tell application "System Events"
    tell process "Archivex Clinical"
        set b to position of window 1 & size of window 1
        return (item 1 of b as text) & "," & (item 2 of b as text) & "," & \\
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
```

- [ ] **Step 4: Run — confirm all pass**

```bash
pytest tests/test_sync.py -v
```

Expected: 16 PASSED.

- [ ] **Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat(sync): Archivex window detection via AppleScript"
```

---

## Task 5: Haiku verifier with prompt caching

**Files:**
- Modify: `sync.py` (add §7 Verifier)
- Modify: `tests/test_sync.py` (add TestVerifier)

- [ ] **Step 1: Write failing tests — append to `tests/test_sync.py`**

```python
class TestVerifier:
    SIGNATURES = {
        "empty_slot":       "slot vacío sin color de fondo",
        "occupied_slot":    "slot con fondo coloreado y nombre de paciente",
        "form_open":        "modal de nueva cita visible con campo de búsqueda",
        "patient_selected": "nombre de paciente relleno en el campo",
        "appointment_saved": "formulario cerrado, cita visible en el calendario",
    }

    def _mock_haiku(self, mock_anthropic, text: str):
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = msg

    def test_verify_slot_empty_returns_empty(self, sync, monkeypatch):
        mock_ant = MagicMock()
        self._mock_haiku(mock_ant, "empty")
        monkeypatch.setattr("sync.Anthropic", mock_ant)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake_b64")
        result = sync.verify_slot_empty(self.SIGNATURES, day_offset=1, hour=9)
        assert result == "empty"

    def test_verify_slot_empty_returns_occupied(self, sync, monkeypatch):
        mock_ant = MagicMock()
        self._mock_haiku(mock_ant, "occupied")
        monkeypatch.setattr("sync.Anthropic", mock_ant)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake_b64")
        result = sync.verify_slot_empty(self.SIGNATURES, day_offset=1, hour=9)
        assert result == "occupied"

    def test_verify_slot_empty_returns_uncertain_on_unknown(self, sync, monkeypatch):
        mock_ant = MagicMock()
        self._mock_haiku(mock_ant, "I cannot determine this")
        monkeypatch.setattr("sync.Anthropic", mock_ant)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake_b64")
        result = sync.verify_slot_empty(self.SIGNATURES, day_offset=1, hour=9)
        assert result == "uncertain"

    def test_verify_form_open_true(self, sync, monkeypatch):
        mock_ant = MagicMock()
        self._mock_haiku(mock_ant, "yes")
        monkeypatch.setattr("sync.Anthropic", mock_ant)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake_b64")
        assert sync.verify_form_open(self.SIGNATURES) is True

    def test_verify_form_open_false(self, sync, monkeypatch):
        mock_ant = MagicMock()
        self._mock_haiku(mock_ant, "no")
        monkeypatch.setattr("sync.Anthropic", mock_ant)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake_b64")
        assert sync.verify_form_open(self.SIGNATURES) is False

    def test_verify_saved_true(self, sync, monkeypatch):
        mock_ant = MagicMock()
        self._mock_haiku(mock_ant, "yes")
        monkeypatch.setattr("sync.Anthropic", mock_ant)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake_b64")
        assert sync.verify_saved(self.SIGNATURES) is True
```

- [ ] **Step 2: Run — confirm fail**

```bash
pytest tests/test_sync.py::TestVerifier -v
```

Expected: `AttributeError: module 'sync' has no attribute 'verify_slot_empty'`

- [ ] **Step 3: Add §7 to `sync.py`**

```python
# ─── §7 VERIFIER (Haiku + prompt caching) ────────────────────────────────────
def _screenshot_b64() -> str:
    """Captura la pantalla y devuelve PNG en base64."""
    buf = BytesIO()
    pyautogui.screenshot().save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _build_cache_prefix(signatures: dict) -> str:
    """Construye el texto del prefijo cacheado a partir de las firmas visuales."""
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


def _ask_haiku(question: str, signatures: dict) -> str:
    """
    Envía screenshot + pregunta a Haiku con el prefijo cacheado.
    Devuelve el texto de la respuesta en minúsculas.
    """
    client = Anthropic()
    cache_text = _build_cache_prefix(signatures)
    resp = client.messages.create(
        model=MODEL_VERIFY,
        max_tokens=10,
        system=[{
            "type": "text",
            "text": cache_text,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": _screenshot_b64(),
            }},
            {"type": "text", "text": question},
        ]}],
    )
    return resp.content[0].text.strip().lower()


def verify_slot_empty(signatures: dict, day_offset: int, hour: int) -> str:
    """
    Verifica si el slot está vacío o tiene una cita.
    Devuelve: 'empty' | 'occupied' | 'uncertain'
    """
    days_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    question = (
        f"¿El slot del calendario del {days_es[day_offset]} a las {hour:02d}:00 "
        f"está vacío o tiene una cita?\n"
        "Responde ÚNICAMENTE con: empty (si está vacío) u occupied (si tiene cita)."
    )
    raw = _ask_haiku(question, signatures)
    if "empty" in raw:
        return "empty"
    if "occupied" in raw:
        return "occupied"
    return "uncertain"


def verify_form_open(signatures: dict) -> bool:
    """
    Verifica si el formulario de nueva cita está abierto.
    """
    question = (
        "¿Está visible el formulario modal de nueva cita con el campo de búsqueda de paciente?\n"
        "Responde ÚNICAMENTE con: yes o no."
    )
    raw = _ask_haiku(question, signatures)
    return "yes" in raw


def verify_saved(signatures: dict) -> bool:
    """
    Verifica si la cita fue guardada (formulario cerrado, cita en calendario).
    """
    question = (
        "¿Se cerró el formulario de cita y la nueva cita es visible en el calendario?\n"
        "Responde ÚNICAMENTE con: yes o no."
    )
    raw = _ask_haiku(question, signatures)
    return "yes" in raw
```

- [ ] **Step 4: Run — confirm all pass**

```bash
pytest tests/test_sync.py -v
```

Expected: 22 PASSED.

- [ ] **Step 5: Lint**

```bash
ruff check .
```

- [ ] **Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat(sync): Haiku verifier with prompt caching for 3 semantic checkpoints"
```

---

## Task 6: Appointment processor — pyautogui actions

**Files:**
- Modify: `sync.py` (add §8 Appointment Processor)
- Modify: `tests/test_sync.py` (add TestProcessor)

- [ ] **Step 1: Write failing tests — append to `tests/test_sync.py`**

```python
class TestProcessor:
    KB = {
        "elements": {
            "patient_search_pct": {"x": 0.45, "y": 0.35},
            "first_result_pct":   {"x": 0.45, "y": 0.42},
            "save_btn_pct":       {"x": 0.65, "y": 0.85},
        }
    }
    WINDOW = (0, 0, 1440, 900)

    def test_open_slot_calls_double_click(self, sync, monkeypatch):
        calls = []
        monkeypatch.setattr("sync.pyautogui.doubleClick",
                            lambda x, y: calls.append((x, y)))
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        sync.open_slot(300, 400)
        assert calls == [(300, 400)]

    def test_save_appointment_clicks_save_button(self, sync, monkeypatch):
        clicks = []
        monkeypatch.setattr("sync.pyautogui.click",
                            lambda x, y: clicks.append((x, y)))
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        wx, wy, ww, wh = self.WINDOW
        sync.save_appointment(self.KB, wx, wy, ww, wh)
        expected_x = int(0.65 * 1440)
        expected_y = int(0.85 * 900)
        assert (expected_x, expected_y) in clicks

    def test_fill_patient_writes_to_clipboard(self, sync, monkeypatch):
        clipboard = []
        monkeypatch.setattr("subprocess.run",
                            lambda cmd, **kw: clipboard.append(kw.get("input", b"")))
        monkeypatch.setattr("sync.pyautogui.click", lambda x, y: None)
        monkeypatch.setattr("sync.pyautogui.hotkey", lambda *a: None)
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        wx, wy, ww, wh = self.WINDOW
        sync.fill_patient("Ana García", self.KB, wx, wy, ww, wh)
        assert b"Ana García" in clipboard
```

- [ ] **Step 2: Run — confirm fail**

```bash
pytest tests/test_sync.py::TestProcessor -v
```

- [ ] **Step 3: Add §8 to `sync.py`**

```python
# ─── §8 APPOINTMENT PROCESSOR ────────────────────────────────────────────────
def open_slot(x: int, y: int) -> None:
    """Doble clic en el slot del calendario para abrir el formulario."""
    pyautogui.doubleClick(x, y)
    time.sleep(2.0)


def fill_patient(patient: str, kb: dict,
                 wx: int, wy: int, ww: int, wh: int) -> None:
    """
    Hace clic en el campo de búsqueda, pega el nombre via pbcopy
    y selecciona el primer resultado del autocomplete.
    """
    sx, sy = abs_coords(
        kb["elements"]["patient_search_pct"]["x"],
        kb["elements"]["patient_search_pct"]["y"],
        wx, wy, ww, wh,
    )
    pyautogui.click(sx, sy)
    time.sleep(0.4)

    # pbcopy soporta acentos y caracteres especiales
    subprocess.run(["pbcopy"], input=patient.encode("utf-8"), check=True)
    pyautogui.hotkey("command", "a")
    time.sleep(0.1)
    pyautogui.hotkey("command", "v")
    time.sleep(2.5)   # esperar autocomplete

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
```

- [ ] **Step 4: Run — confirm all pass**

```bash
pytest tests/test_sync.py -v
```

Expected: 25 PASSED.

- [ ] **Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat(sync): appointment processor — open slot, fill patient, save"
```

---

## Task 7: Week navigation

**Files:**
- Modify: `sync.py` (add §9 Navigation)
- Modify: `tests/test_sync.py` (add TestNavigation)

- [ ] **Step 1: Write failing tests — append to `tests/test_sync.py`**

```python
class TestNavigation:
    KB = {
        "elements": {
            "nav_prev_pct": {"x": 0.05, "y": 0.04},
            "nav_next_pct": {"x": 0.95, "y": 0.04},
        },
        "visual_signatures": {"empty_slot": "..."},
    }
    WIN = (0, 0, 1440, 900)

    def test_detect_monday_parses_date(self, sync, monkeypatch):
        mock_ant = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(text='{"date": "2026-05-25"}')]
        mock_ant.Anthropic.return_value.messages.create.return_value = msg
        monkeypatch.setattr("sync.Anthropic", mock_ant)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake")
        result = sync.detect_displayed_monday()
        assert result == date(2026, 5, 25)

    def test_detect_monday_returns_none_on_null(self, sync, monkeypatch):
        mock_ant = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(text='{"date": null}')]
        mock_ant.Anthropic.return_value.messages.create.return_value = msg
        monkeypatch.setattr("sync.Anthropic", mock_ant)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake")
        result = sync.detect_displayed_monday()
        assert result is None

    def test_navigate_clicks_next_twice(self, sync, monkeypatch):
        clicks = []
        monkeypatch.setattr("sync.detect_displayed_monday",
                            lambda: date(2026, 5, 25))   # current Monday shown
        monkeypatch.setattr("sync.pyautogui.click",
                            lambda x, y: clicks.append((x, y)))
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        wx, wy, ww, wh = self.WIN
        target = date(2026, 6, 8)   # 2 weeks ahead
        sync.navigate_to_week(target, self.KB, wx, wy, ww, wh)
        expected_x = int(0.95 * 1440)
        assert clicks.count((expected_x, int(0.04 * 900))) == 2

    def test_navigate_no_clicks_if_already_correct(self, sync, monkeypatch):
        clicks = []
        monkeypatch.setattr("sync.detect_displayed_monday",
                            lambda: date(2026, 5, 25))
        monkeypatch.setattr("sync.pyautogui.click",
                            lambda x, y: clicks.append((x, y)))
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        wx, wy, ww, wh = self.WIN
        sync.navigate_to_week(date(2026, 5, 25), self.KB, wx, wy, ww, wh)
        assert clicks == []
```

- [ ] **Step 2: Run — confirm fail**

```bash
pytest tests/test_sync.py::TestNavigation -v
```

- [ ] **Step 3: Add §9 to `sync.py`**

```python
# ─── §9 NAVIGATION ───────────────────────────────────────────────────────────
def detect_displayed_monday() -> Optional[date]:
    """
    Pregunta a Haiku qué lunes muestra actualmente el calendario.
    Devuelve la fecha o None si no se puede determinar.
    """
    client = Anthropic()
    resp = client.messages.create(
        model=MODEL_VERIFY,
        max_tokens=32,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": _screenshot_b64(),
            }},
            {"type": "text", "text": (
                "Mira este calendario semanal de Archivex Clinical. "
                "¿Qué fecha tiene el lunes (primer día) de la semana visible? "
                'Responde ÚNICAMENTE con JSON: {"date": "YYYY-MM-DD"} '
                'o {"date": null} si no puedes determinarlo.'
            )},
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


def navigate_to_week(target_monday: date, kb: dict,
                     wx: int, wy: int, ww: int, wh: int) -> None:
    """
    Navega Archivex hasta la semana de target_monday
    haciendo clic en los botones de semana anterior/siguiente.
    """
    current = detect_displayed_monday()
    if current is None:
        log.warning("No se pudo detectar la semana actual — omitiendo navegación")
        return
    delta = (target_monday - current).days // 7
    if delta == 0:
        return

    if delta > 0:
        btn = kb["elements"]["nav_next_pct"]
    else:
        btn = kb["elements"]["nav_prev_pct"]

    bx, by = abs_coords(btn["x"], btn["y"], wx, wy, ww, wh)
    for _ in range(abs(delta)):
        pyautogui.click(bx, by)
        time.sleep(0.8)
```

- [ ] **Step 4: Run — confirm all pass**

```bash
pytest tests/test_sync.py -v
```

Expected: 29 PASSED.

- [ ] **Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat(sync): week navigation — detect current week + click prev/next"
```

---

## Task 8: Main sync loop — wire everything + conflict handling

**Files:**
- Modify: `sync.py` (add §10 Conflict + §11 Main)
- Modify: `tests/test_sync.py` (add TestConflict + TestMain)

- [ ] **Step 1: Write failing tests — append to `tests/test_sync.py`**

```python
class TestConflict:
    def test_ask_conflict_crear(self, sync, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "c")
        appt = sync.Appointment("X", date(2026, 5, 26), "09:00", "10:00", 1, 9, 0)
        assert sync.ask_conflict_action(appt) == "crear"

    def test_ask_conflict_saltar(self, sync, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "s")
        appt = sync.Appointment("X", date(2026, 5, 26), "09:00", "10:00", 1, 9, 0)
        assert sync.ask_conflict_action(appt) == "saltar"

    def test_ask_conflict_parar(self, sync, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "p")
        appt = sync.Appointment("X", date(2026, 5, 26), "09:00", "10:00", 1, 9, 0)
        assert sync.ask_conflict_action(appt) == "parar"


class TestProcessAppointment:
    KB_FIXTURE = {
        "grid": {
            "start_hour": 8, "end_hour": 20,
            "col_offsets_pct": [0.10, 0.24, 0.38, 0.52, 0.66, 0.80, 0.94],
            "first_row_y_pct": 0.10, "last_row_y_pct": 0.98,
        },
        "elements": {
            "nav_prev_pct":       {"x": 0.05, "y": 0.04},
            "nav_next_pct":       {"x": 0.95, "y": 0.04},
            "patient_search_pct": {"x": 0.45, "y": 0.35},
            "first_result_pct":   {"x": 0.45, "y": 0.42},
            "save_btn_pct":       {"x": 0.65, "y": 0.85},
        },
        "visual_signatures": {
            "empty_slot": "...", "occupied_slot": "...",
            "form_open": "...", "patient_selected": "...",
            "appointment_saved": "...",
        },
    }

    def _appt(self, sync):
        return sync.Appointment("Ana García", date(2026, 5, 26), "09:00", "10:00", 1, 9, 0)

    def test_process_creates_when_slot_empty(self, sync, monkeypatch):
        monkeypatch.setattr("sync.verify_slot_empty", lambda sigs, **kw: "empty")
        monkeypatch.setattr("sync.open_slot", lambda x, y: None)
        monkeypatch.setattr("sync.verify_form_open", lambda sigs: True)
        monkeypatch.setattr("sync.fill_patient", lambda *a, **kw: None)
        monkeypatch.setattr("sync.save_appointment", lambda *a: None)
        monkeypatch.setattr("sync.verify_saved", lambda sigs: True)
        result = sync.process_appointment(
            self._appt(sync), self.KB_FIXTURE, 0, 0, 1440, 900
        )
        assert result == "creada"

    def test_process_asks_on_conflict(self, sync, monkeypatch):
        monkeypatch.setattr("sync.verify_slot_empty", lambda sigs, **kw: "occupied")
        monkeypatch.setattr("builtins.input", lambda _: "s")
        result = sync.process_appointment(
            self._appt(sync), self.KB_FIXTURE, 0, 0, 1440, 900
        )
        assert result == "saltada"

    def test_process_raises_on_parar(self, sync, monkeypatch):
        monkeypatch.setattr("sync.verify_slot_empty", lambda sigs, **kw: "occupied")
        monkeypatch.setattr("builtins.input", lambda _: "p")
        with pytest.raises(sync.StopSync):
            sync.process_appointment(
                self._appt(sync), self.KB_FIXTURE, 0, 0, 1440, 900
            )
```

- [ ] **Step 2: Run — confirm fail**

```bash
pytest tests/test_sync.py::TestConflict tests/test_sync.py::TestProcessAppointment -v
```

- [ ] **Step 3: Add §10 and §11 to `sync.py`**

```python
# ─── §10 CONFLICT HANDLING ───────────────────────────────────────────────────
class StopSync(Exception):
    """Raised when the user chooses to stop the entire sync."""


def ask_conflict_action(appt: Appointment) -> str:
    """
    Pregunta al usuario qué hacer con un conflicto.
    Devuelve: 'crear' | 'saltar' | 'parar'
    """
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
    Crea una cita en Archivex.
    Devuelve: 'creada' | 'saltada'
    Lanza StopSync si el usuario elige parar.
    """
    sigs = kb["visual_signatures"]

    # 1. Verificar si el slot está libre
    status = verify_slot_empty(sigs, day_offset=appt.day_offset, hour=appt.hour)
    if status != "empty":
        accion = ask_conflict_action(appt)
        if accion == "parar":
            raise StopSync()
        if accion == "saltar":
            log.info("SALTADA  | %s | %s %s | slot ocupado",
                     appt.patient, appt.date.strftime("%d/%m/%Y"), appt.start_time)
            return "saltada"
        # "crear" → ignorar el conflicto y continuar

    # 2. Abrir formulario
    sx, sy = slot_coords(appt.day_offset, appt.hour, appt.minute,
                         kb, wx, wy, ww, wh)
    open_slot(sx, sy)

    if not verify_form_open(sigs):
        # Reintento
        open_slot(sx, sy)
        if not verify_form_open(sigs):
            log.warning("SALTADA  | %s | %s %s | formulario no se abrió",
                        appt.patient, appt.date.strftime("%d/%m/%Y"), appt.start_time)
            print(f"  ⚠️  Formulario no se abrió para {appt.patient}. Saltando.")
            return "saltada"

    # 3. Rellenar paciente + guardar
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
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    print("🗓  Archivex Sync")
    print("─" * 40)

    # Cargar knowledge base
    kb = load_knowledge()
    sigs = kb["visual_signatures"]
    print(f"✅  Knowledge base cargado ({KNOWLEDGE})")

    # Detectar ventana de Archivex
    try:
        wx, wy, ww, wh = get_window_bounds()
    except RuntimeError as e:
        sys.exit(f"❌  {e}")
    print(f"✅  Archivex detectado: {ww}×{wh} en ({wx},{wy})")

    # Autenticar Google Calendar
    service = get_calendar_service()
    monday = date.today() - timedelta(days=date.today().weekday())
    print(f"📅  Semana del {monday.strftime('%d/%m/%Y')}")

    # Obtener citas (ya filtradas sin lun/mié)
    appointments = get_week_appointments(service, monday)
    print(f"📋  {len(appointments)} cita(s) a procesar "
          f"(lunes y miércoles excluidos)")

    if not appointments:
        print("   Nada que sincronizar.")
        return

    # Navegar a la semana correcta en Archivex
    navigate_to_week(monday, kb, wx, wy, ww, wh)

    # Procesar citas
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

    print(f"\n─" * 40)
    print(f"✅  Creadas: {creadas}   ⏭  Saltadas: {saltadas}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_sync.py -v
```

Expected: 35 PASSED.

- [ ] **Step 5: Lint**

```bash
ruff check .
```

- [ ] **Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat(sync): main loop — conflict handling, process_appointment, main()"
```

---

## Task 9: `recon.py` — Opus 4.7 reconnaissance

**Files:**
- Create: `recon.py`
- Create: `tests/test_recon.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_recon.py`:

```python
"""Unit tests for recon.py validation logic."""
import sys
from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def mock_pyautogui():
    sys.modules["pyautogui"] = Mock()
    yield
    sys.modules.pop("recon", None)


@pytest.fixture
def recon():
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    import recon as r
    return r


class TestValidateKnowledge:
    VALID = {
        "version": 1,
        "recon_date": "2026-05-25",
        "window": {"x": 0, "y": 0, "w": 1440, "h": 900},
        "grid": {
            "start_hour": 8,
            "end_hour": 20,
            "col_offsets_pct": [0.1, 0.24, 0.38, 0.52, 0.66, 0.80, 0.94],
            "first_row_y_pct": 0.10,
            "last_row_y_pct": 0.98,
        },
        "elements": {
            "nav_prev_pct":       {"x": 0.05, "y": 0.04},
            "nav_next_pct":       {"x": 0.95, "y": 0.04},
            "patient_search_pct": {"x": 0.45, "y": 0.35},
            "first_result_pct":   {"x": 0.45, "y": 0.42},
            "save_btn_pct":       {"x": 0.65, "y": 0.85},
        },
        "visual_signatures": {
            "empty_slot":        "slot vacío",
            "occupied_slot":     "slot ocupado",
            "form_open":         "formulario abierto",
            "patient_selected":  "paciente seleccionado",
            "appointment_saved": "cita guardada",
        },
    }

    def test_valid_knowledge_passes(self, recon):
        recon.validate_recon_output(self.VALID)   # no exception

    def test_missing_grid_raises(self, recon):
        bad = {k: v for k, v in self.VALID.items() if k != "grid"}
        with pytest.raises(ValueError, match="grid"):
            recon.validate_recon_output(bad)

    def test_wrong_col_count_raises(self, recon):
        bad = {**self.VALID, "grid": {**self.VALID["grid"],
               "col_offsets_pct": [0.1, 0.2]}}  # only 2 instead of 7
        with pytest.raises(ValueError, match="7"):
            recon.validate_recon_output(bad)

    def test_coord_out_of_range_raises(self, recon):
        bad = {**self.VALID, "elements": {
            **self.VALID["elements"],
            "nav_next_pct": {"x": 1.5, "y": 0.04},   # x > 1.0
        }}
        with pytest.raises(ValueError, match="rango"):
            recon.validate_recon_output(bad)

    def test_missing_visual_signature_raises(self, recon):
        bad = {**self.VALID, "visual_signatures": {
            k: v for k, v in self.VALID["visual_signatures"].items()
            if k != "empty_slot"
        }}
        with pytest.raises(ValueError, match="empty_slot"):
            recon.validate_recon_output(bad)
```

- [ ] **Step 2: Run — confirm fail**

```bash
pytest tests/test_recon.py -v
```

Expected: `ModuleNotFoundError: No module named 'recon'`

- [ ] **Step 3: Create `recon.py`**

```python
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
import sys
import time
from datetime import date
from io import BytesIO
from pathlib import Path

import pyautogui
from anthropic import Anthropic

# ─── CONSTANTES ──────────────────────────────────────────────────────────────
CONFIG_DIR   = Path.home() / ".config" / "archivex-sync"
OUTPUT_PATH  = CONFIG_DIR / "ui_knowledge.json"
MODEL_RECON  = "claude-opus-4-7"

_REQUIRED_KEYS        = {"version", "grid", "elements", "visual_signatures"}
_REQUIRED_GRID        = {"start_hour", "end_hour", "col_offsets_pct",
                         "first_row_y_pct", "last_row_y_pct"}
_REQUIRED_ELEMENTS    = {"nav_prev_pct", "nav_next_pct", "patient_search_pct",
                         "first_result_pct", "save_btn_pct"}
_REQUIRED_SIGNATURES  = {"empty_slot", "occupied_slot", "form_open",
                         "patient_selected", "appointment_saved"}


# ─── VALIDACIÓN ──────────────────────────────────────────────────────────────
def validate_recon_output(kb: dict) -> None:
    """
    Valida el JSON producido por Opus.
    Lanza ValueError con mensaje descriptivo si algo está mal.
    """
    for k in _REQUIRED_KEYS:
        if k not in kb:
            raise ValueError(f"Falta la clave raíz: '{k}'")

    for k in _REQUIRED_GRID:
        if k not in kb["grid"]:
            raise ValueError(f"grid: falta '{k}'")

    cols = kb["grid"].get("col_offsets_pct", [])
    if len(cols) != 7:
        raise ValueError(f"col_offsets_pct debe tener exactamente 7 valores (uno por día), tiene {len(cols)}")

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

Analiza cuidadosamente el screenshot y produce un JSON con EXACTAMENTE esta estructura.
Todas las coordenadas deben ser RELATIVAS al tamaño de la ventana (valores entre 0.0 y 1.0).
La esquina superior izquierda de la ventana es (0.0, 0.0) y la inferior derecha es (1.0, 1.0).

Devuelve ÚNICAMENTE el JSON, sin markdown, sin explicaciones:

{
  "version": 1,
  "recon_date": "YYYY-MM-DD",
  "window": {"x": <int>, "y": <int>, "w": <int>, "h": <int>},
  "grid": {
    "start_hour": <int, hora inicio cuadrícula ej. 8>,
    "end_hour": <int, hora fin cuadrícula ej. 20>,
    "col_offsets_pct": [<7 floats, x relativa del centro de cada columna día: Lun,Mar,Mié,Jue,Vie,Sáb,Dom>],
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
    "empty_slot":        "<descripción de cómo se ve un slot vacío en el calendario>",
    "occupied_slot":     "<descripción de cómo se ve un slot con una cita existente>",
    "form_open":         "<descripción de cuándo el formulario de nueva cita está abierto>",
    "patient_selected":  "<descripción de cuándo un paciente ha sido seleccionado del autocomplete>",
    "appointment_saved": "<descripción del estado tras guardar la cita exitosamente>"
  }
}

Campos patient_search_pct y first_result_pct: si el formulario no está visible en este
screenshot, infiere las coordenadas probables basándote en el diseño típico de formularios
modales en aplicaciones de calendario médico.
"""


# ─── RECONOCIMIENTO ──────────────────────────────────────────────────────────
def run_recon() -> dict:
    """
    Toma screenshots de Archivex en múltiples estados y llama a Opus 4.7
    para producir ui_knowledge.json.
    """
    client = Anthropic()

    print("📸  Capturando screenshots del calendario...")
    screenshots = []

    # Screenshot 1: estado actual (calendario semanal)
    screenshots.append(_screenshot_b64())

    print("   ✓  Screenshot 1/2: vista del calendario")
    print("   ℹ️   Doble clic en un slot vacío para abrir el formulario de nueva cita.")
    print("   ℹ️   Tienes 5 segundos para hacerlo...")
    time.sleep(5)

    # Screenshot 2: con formulario abierto (si el usuario lo abrió)
    screenshots.append(_screenshot_b64())
    print("   ✓  Screenshot 2/2: formulario (si estaba abierto)\n")

    print("🤖  Enviando a Opus 4.7 para análisis...")
    content = []
    for i, shot in enumerate(screenshots, 1):
        content.append({"type": "text", "text": f"Screenshot {i}:"})
        content.append({"type": "image", "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": shot,
        }})
    content.append({"type": "text", "text": _RECON_PROMPT.replace(
        "YYYY-MM-DD", date.today().isoformat()
    )})

    resp = client.messages.create(
        model=MODEL_RECON,
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )

    raw = resp.content[0].text.strip()

    # Extraer JSON si viene envuelto en markdown
    if "```" in raw:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        raw   = raw[start:end]

    try:
        kb = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"❌  Opus devolvió JSON inválido: {e}\n\nRespuesta:\n{raw}")

    return kb


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    print("🔍  Archivex Recon — Análisis visual con Opus 4.7")
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
```

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```

Expected: all PASSED (35 sync + 5 recon = 40 total).

- [ ] **Step 5: Final lint check**

```bash
ruff check .
```

Expected: no issues.

- [ ] **Step 6: Final commit**

```bash
git add recon.py tests/test_recon.py
git commit -m "feat(recon): Opus 4.7 reconnaissance — produces ui_knowledge.json"
```

---

## Task 10: Update `.gitignore` + smoke test

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Update `.gitignore`**

```gitignore
# Secrets & tokens
credentials.json
token_*.json
ui_knowledge.json

# Python
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/
```

- [ ] **Step 2: Verify nothing sensitive is tracked**

```bash
git status
```

Expected: only `.gitignore` shown if modified.

- [ ] **Step 3: Smoke test imports**

```bash
python -c "import sync; print('sync OK')"
python -c "import recon; print('recon OK')"
```

Expected: both print OK without errors.

- [ ] **Step 4: Run full test suite**

```bash
pytest -v --tb=short
```

Expected: 40 PASSED, 0 failed.

- [ ] **Step 5: Final commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore + verify smoke tests pass"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Opus 4.7 recon → `ui_knowledge.json` (Task 9)
- ✅ Google Calendar OAuth2 reader (Task 2)
- ✅ Monday + Wednesday filter (Task 2, `SKIP_DAYS = {0, 2}`)
- ✅ Current week always (Task 2, `date.today() - timedelta(days=weekday)`)
- ✅ Coordinate calculator from relative pct (Task 3)
- ✅ Archivex window detection (Task 4)
- ✅ Haiku verifier with prompt caching (Task 5)
- ✅ Slot empty semantic check (replaces pixel heuristic) (Task 5)
- ✅ open_slot / fill_patient / save_appointment (Task 6)
- ✅ Week navigation (Task 7)
- ✅ Conflict handling — ask crear/saltar/parar (Task 8)
- ✅ Monolithic sync.py with main() (Task 8)
- ✅ Form not opened → retry once then skip (Task 8)
- ✅ saved verification warning (Task 8)

**Type consistency:** All functions use `abs_coords(pct_x, pct_y, wx, wy, ww, wh)` consistently. `slot_coords` passes same args. `verify_slot_empty(signatures, day_offset=, hour=)` matches test and implementation.

**No placeholders found.**
