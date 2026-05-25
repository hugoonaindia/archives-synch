# Opus Recon + Knowledge Base — Design Spec
*2026-05-25 | Archivex Sync*

## Goal

Replace the current approach (Haiku API call per action + fragile pixel-based slot detection) with a two-phase system:

1. **Recon** (once, manual): Opus 4.7 studies the Archivex Clinical UI and produces a persistent `ui_knowledge.json`
2. **Production** (every sync): zero API calls for navigation; 3 cached Haiku calls for semantic verification

This eliminates the `is_slot_occupied()` false-positive bug and reduces per-appointment API cost by ~90%.

---

## Problem Being Solved

### Bug: false positive "slot occupied"
`is_slot_occupied()` uses pixel variance/mean heuristics on a SkiaSharp canvas app. Grid lines, anti-aliasing, and adjacent slot rendering produce values that trigger false positives. The only robust fix is semantic visual understanding.

### Cost: $0.006/appointment
`vision_driver.py` calls Haiku for every navigation action. With the knowledge base, navigation is free — Haiku is called only at 3 critical verification checkpoints, using prompt caching.

---

## Architecture

### New files

```
recon.py                     — Opus 4.7 reconnaissance script (run once)
knowledge_driver.py          — Navigation using ui_knowledge.json (replaces vision_driver.py)
verifier.py                  — 3 Haiku-cached semantic checkpoints
~/.config/archivex-sync/
  ui_knowledge.json          — Learned UI layout (coords + visual signatures)
```

### Kept files (unchanged)
```
archivex_sync.py             — Orchestrator: updated to use knowledge_driver + verifier
vision_driver.py             — Kept as fallback if ui_knowledge.json is missing
calibrate_gui.py             — Kept as secondary fallback
```

### Mode selection (auto-detect in `main()`)
```
1. ui_knowledge.json exists → knowledge_driver + verifier  (PRIMARY)
2. ANTHROPIC_API_KEY set    → vision_driver                (FALLBACK)
3. cal_config.json exists   → calibrate mode               (LEGACY FALLBACK)
```

---

## Module Design

### `recon.py` — Run once with `python archivex_sync.py --recon`

**Responsibilities:**
- Verify Archivex is open and in weekly calendar view
- Take screenshots of the app in 4 states: calendar (empty slot visible), calendar (occupied slot visible), new appointment form open, patient autocomplete visible
- Call Opus 4.7 with all screenshots and a structured prompt requesting `ui_knowledge.json`
- Validate the response (all required keys present, coords in [0,1] range)
- Save to `~/.config/archivex-sync/ui_knowledge.json`
- Print a human-readable summary of what was learned

**`ui_knowledge.json` schema:**
```json
{
  "version": 1,
  "recon_date": "2026-05-25",
  "window": { "x": 0, "y": 0, "w": 1440, "h": 900 },
  "grid": {
    "start_hour": 8,
    "end_hour": 20,
    "header_height_pct": 0.08,
    "col_offsets_pct": [0.10, 0.24, 0.38, 0.52, 0.66, 0.80, 0.94],
    "first_row_y_pct": 0.10,
    "last_row_y_pct": 0.98
  },
  "elements": {
    "nav_prev_pct":        { "x": 0.05, "y": 0.04 },
    "nav_next_pct":        { "x": 0.95, "y": 0.04 },
    "patient_search_pct":  { "x": 0.45, "y": 0.35 },
    "first_result_pct":    { "x": 0.45, "y": 0.42 },
    "save_btn_pct":        { "x": 0.65, "y": 0.85 }
  },
  "visual_signatures": {
    "empty_slot":         "descripción en lenguaje natural de un slot vacío",
    "occupied_slot":      "descripción de un slot con cita (fondo coloreado, texto de paciente)",
    "form_open":          "descripción del formulario modal de nueva cita visible",
    "patient_selected":   "descripción de cuando un paciente ha sido elegido del autocomplete",
    "appointment_saved":  "descripción del estado tras guardar (formulario cerrado, cita visible)"
  }
}
```

**Error handling:**
- Archivex not open → clear message, exit
- Opus response missing required keys → print what's missing, abort (don't save partial)
- Save fails → print error, suggest checking `~/.config/archivex-sync/` permissions

---

### `knowledge_driver.py` — Zero-API navigation

**Responsibilities:**
- Load and cache `ui_knowledge.json` (singleton, loaded once per process)
- Detect current Archivex window bounds via AppleScript at runtime
- Compute absolute pixel coordinates from relative percentages + current window bounds
- Expose the same interface as `vision_driver.py` for drop-in compatibility:
  - `open_appointment_form(day_offset, hour, minute) → bool`
  - `fill_patient(patient_name) → None`
  - `save_appointment() → None`
  - `navigate_to_week(target_monday) → None`
  - `is_available() → bool`  ← True if ui_knowledge.json exists

**Coordinate calculation:**
```python
def _abs(pct_x: float, pct_y: float) -> tuple[int, int]:
    wx, wy, ww, wh = _get_window_bounds()
    return int(wx + pct_x * ww), int(wy + pct_y * wh)
```

**Slot coordinate calculation:**
```python
def _slot_coords(day_offset: int, hour: int, minute: int) -> tuple[int, int]:
    g = _kb["grid"]
    x_pct = g["col_offsets_pct"][day_offset]
    total_hours = g["end_hour"] - g["start_hour"]
    y_pct = g["first_row_y_pct"] + (
        (hour - g["start_hour"] + minute / 60) / total_hours
        * (g["last_row_y_pct"] - g["first_row_y_pct"])
    )
    return _abs(x_pct, y_pct)
```

**`navigate_to_week()`:** takes a screenshot of the week header region (coords from knowledge base), calls Haiku once (cached prefix) to read the displayed monday date, then clicks nav_prev / nav_next the right number of times. This is one extra cached call per sync session (not per appointment).

**Error handling:**
- `ui_knowledge.json` not found → `is_available()` returns False → orchestrator falls back to vision_driver
- Window not found (Archivex closed) → raise `RuntimeError("Archivex no está abierto")`

---

### `verifier.py` — 3 semantic checkpoints with Haiku + prompt caching

**Responsibilities:**
- Build the cached prompt prefix once (contains `visual_signatures` from knowledge base)
- Expose 3 verification functions, each taking a fresh screenshot:
  - `verify_slot_empty(day_offset, hour, minute) → Literal["empty", "occupied", "uncertain"]`
  - `verify_form_open() → bool`
  - `verify_saved() → bool`

**Prompt caching strategy:**
```
[CACHED PREFIX — loaded once]
  System context: you are verifying Archivex Clinical state
  Visual signatures: <entire visual_signatures dict as structured text>

[FRESH PER CALL]
  Screenshot (base64)
  Question: "Is the slot at column 2, row 10:00 empty or occupied?"
```

Cached tokens: ~500 tokens × $0.30/Mtok input cached = **$0.00015 per verification**

**Behavior on "uncertain":**
- `verify_slot_empty` returns `"uncertain"` → treat as occupied (safe default), ask user

**`process_appointment` updated flow:**
```
1. verify_slot_empty()      → if occupied/uncertain: ask_conflict_action()
2. knowledge_driver.open_appointment_form()
3. verify_form_open()       → if False: retry once, then stop+warn
4. knowledge_driver.fill_patient()
5. knowledge_driver.save_appointment()
6. verify_saved()           → if False: warn user (appointment may not have saved)
```

---

## Interface Compatibility

`archivex_sync.py` currently calls:
```python
use_vision = _vd.is_available()
resultado = process_appointment_vision(appt)   # uses vision_driver
resultado = process_appointment(appt, ...)     # uses calibration
```

Updated to:
```python
import knowledge_driver as _kd
import vision_driver as _vd

if _kd.is_available():
    use_mode = "knowledge"
elif _vd.is_available():
    use_mode = "vision"
else:
    use_mode = "calibration"
```

`process_appointment_knowledge(appt)` added alongside existing functions — no existing code removed.

---

## CLI Interface

```bash
# Normal sync (auto-selects best available mode)
python archivex_sync.py

# Run reconnaissance (requires Archivex open in weekly view)
python archivex_sync.py --recon

# Force vision mode (skip knowledge base)
python archivex_sync.py --mode vision

# Show which mode would be used
python archivex_sync.py --status
```

---

## Testing

New tests in `tests/test_knowledge_driver.py`:
- `test_load_knowledge_valid` — loads a fixture JSON, asserts schema
- `test_abs_coords_calculation` — verifies relative→absolute conversion
- `test_slot_coords_at_boundaries` — 8:00 and 20:00 produce expected y range
- `test_is_available_false_missing_file` — no ui_knowledge.json → False
- `test_is_available_true_existing_file` — file exists → True

New tests in `tests/test_verifier.py`:
- `test_verify_slot_empty_returns_empty` — mock Haiku response "empty"
- `test_verify_slot_occupied_returns_occupied` — mock Haiku response "occupied"
- `test_verify_form_open_true` — mock Haiku response True
- `test_verify_saved_false_warns` — verify_saved False triggers warning path

`recon.py` is not unit-tested (requires live Archivex + Opus API); integration test documented in README.

Target: ≥ 80% overall coverage (currently uncovered).

---

## Out of Scope

- Fine-tuning or training a local model
- Automatic re-recon on staleness detection (manual trigger only)
- Multi-monitor support (single primary display assumed)
- Archivex version detection

---

## Success Criteria

- [ ] `python archivex_sync.py --recon` produces valid `ui_knowledge.json`
- [ ] Sync runs with zero API calls for navigation (verified via mock)
- [ ] `is_slot_occupied()` false-positive bug no longer reproducible
- [ ] Per-appointment API cost ≤ $0.001 (3 cached Haiku calls)
- [ ] All new tests pass, overall coverage ≥ 80%
- [ ] Existing calibration and vision fallback modes still work
