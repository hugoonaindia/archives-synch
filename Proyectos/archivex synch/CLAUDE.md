# Archivex Sync

**Goal**: Automatizar la creación de citas en Archivex Clinical leyendo eventos de Google Calendar via UI automation (pyautogui + AppleScript).

**Stack**: Python 3.12+, pyautogui, tkinter, Google Calendar API (OAuth2)

**Tests**: `pytest -q --tb=short`

**Lint**: `ruff check .`

**Spec**: docs/SPEC.md

**Memory**: memory/MEMORY.md

## Reglas de seguridad

- `credentials.json` y `token_*.json` NUNCA se commitean
- Tokens en `~/.config/archivex-sync/` (fuera del repo)
- `.gitignore` bloquea todos los archivos de credenciales

## Ejecución

```bash
python archivex_sync.py          # menú principal
python calibrate_gui.py          # calibración GUI directa
```

## Calibración

Los valores CAL se guardan en `~/.config/archivex-sync/cal_config.json`.
`col_centers_x` es una lista de 7 coordenadas X absolutas (Lun→Dom).
