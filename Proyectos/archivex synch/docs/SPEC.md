# Archivex Sync — Spec
*Auto-bootstrapped 2026-05-25*

## Goal

Automatizar la entrada de citas clínicas: leer eventos de Google Calendar para la semana actual y reproducirlos en Archivex Clinical via mouse/teclado (pyautogui + AppleScript), incluyendo un flujo de calibración GUI interactivo para adaptar las coordenadas a cualquier resolución de pantalla.

## Architecture

```
archivex_sync.py        — CLI principal + lógica de sync + orquestación
calibrate_gui.py        — GUI tkinter paso a paso (13 pasos, coordenadas en tiempo real)
calibrate_archivex.py   — CLI de calibración legacy (mantener por compatibilidad)
tests/
  test_archivex_sync.py — Unit tests (pytest)
~/.config/archivex-sync/
  cal_config.json       — Persistencia de calibración
  token_*.json          — OAuth tokens (fuera del repo)
  archivex_sync.log     — Log de operaciones
```

## §1. Backlog

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1 | Fix ruff 16 issues (lint gate rojo) | 🚨 CI | ✅ Done |
| 2 | GitHub Actions CI (pytest + ruff en push) | ⚡ P0 | ✅ Done |
| 3 | Log rotation: RotatingFileHandler (max 5MB × 3 archivos) | ⚠️ Debt | ✅ Done |
| 4 | Eliminar calibrate_archivex.py (supersedido por GUI) | ⚠️ Debt | ✅ Done |
| 5 | Manejo Archivex no abierto: mensaje claro al usuario | ✨ Feature | ✅ Done |
| 6 | Añadir `first_result_dy` calibración a GUI (paso dedicado) | ✨ Feature | Open |
| 7 | Test E2E completo con pyautogui mockeado | ✨ Feature | Open |
| 8 | Launcher shell alias / script de inicio | ✨ Feature | Open |

## §2. Historial
<!-- iterations logged here -->

## §2. Bootstrap + lint + CI + debt cleanup — 2026-05-25

- **Qué**: Bootstrap CLAUDE.md/SPEC.md/MEMORY.md; fix ruff 16 issues; CI workflow; log rotation; remove legacy calibrate_archivex.py; detect Archivex not running.
- **Por qué**: Producción requiere gate de calidad limpio, CI, y UX robusta.
- **Tests**: 10 passing | lint: clean
- **Próximo**: `first_result_dy` calibración GUI (paso dedicado) o Launcher script
