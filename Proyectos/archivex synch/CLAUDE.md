# Archivex Sync

**Goal**: Leer Google Calendar (semana actual) y crear las citas en Archivex Clinical via pyautogui. Excluye lunes y miércoles.

**Stack**: Python 3.12+, anthropic SDK (Opus 4.7 + Haiku w/ prompt caching), pyautogui, Google Calendar API

**Tests**: `pytest -q --tb=short`

**Lint**: `ruff check .`

**Spec**: docs/SPEC.md

**Memory**: memory/MEMORY.md

**Plan**: docs/superpowers/plans/2026-05-25-archivex-sync-rewrite.md

## Dos scripts

- `recon.py` — ejecutar UNA VEZ con Archivex abierto en vista semanal → produce `~/.config/archivex-sync/ui_knowledge.json`
- `sync.py` — ejecutar cada semana → lee Google Calendar, entra citas en Archivex

## Seguridad

- `credentials.json`, `token_*.json`, `ui_knowledge.json` NUNCA se commitean
- Están en `.gitignore`
