# Archivex Sync — Spec
*Auto-bootstrapped 2026-05-25*

## Goal

Automatizar la entrada de citas clínicas: leer eventos de Google Calendar para la semana actual y reproducirlos en Archivex Clinical via mouse/teclado (pyautogui + AppleScript), incluyendo un flujo de calibración GUI interactivo para adaptar las coordenadas a cualquier resolución de pantalla.

## Architecture

```
archivex_sync.py        — CLI principal + lógica de sync + orquestación
vision_driver.py        — Automatización via Claude API vision (modo sin calibración)
calibrate_gui.py        — GUI tkinter paso a paso (13 pasos, coordenadas en tiempo real)
tests/
  test_archivex_sync.py — Unit tests (pytest)
~/.config/archivex-sync/
  cal_config.json       — Persistencia de calibración
  token_*.json          — OAuth tokens (fuera del repo)
  archivex_sync.log     — Log de operaciones
```

**Modos de automatización** (auto-detect en runtime):
- 🤖 **Visión** (si `ANTHROPIC_API_KEY` configurado): screenshot → Claude haiku → coords → clic — sin calibración
- 📐 **Calibración** (fallback): coordenadas guardadas en `cal_config.json`

## §1. Backlog

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1 | Fix ruff 16 issues (lint gate rojo) | 🚨 CI | ✅ Done |
| 2 | GitHub Actions CI (pytest + ruff en push) | ⚡ P0 | ✅ Done |
| 3 | Log rotation: RotatingFileHandler (max 5MB × 3 archivos) | ⚠️ Debt | ✅ Done |
| 4 | Eliminar calibrate_archivex.py (supersedido por GUI) | ⚠️ Debt | ✅ Done |
| 5 | Manejo Archivex no abierto: mensaje claro al usuario | ✨ Feature | ✅ Done |
| 6 | vision_driver.py — automación via Claude API, sin calibración | ✨ Feature | ✅ Done |
| 7 | Añadir `first_result_dy` calibración a GUI (paso dedicado) | ✨ Feature | Open |
| 8 | Test E2E completo con pyautogui + vision mockeados | ✨ Feature | Open |
| 9 | Launcher shell alias / script de inicio | ✨ Feature | Open |
| 10 | Cobertura de tests ≥ 80% (vision + sync paths) | ⚠️ Debt | Open |

## §2. Historial

## §2. Bootstrap + lint + CI + debt cleanup — 2026-05-25

- **Qué**: Bootstrap CLAUDE.md/SPEC.md/MEMORY.md; fix ruff 16 issues; CI workflow; log rotation; remove legacy calibrate_archivex.py; detect Archivex not running.
- **Por qué**: Producción requiere gate de calidad limpio, CI, y UX robusta.
- **Tests**: 10 passing | lint: clean
- **Próximo**: `first_result_dy` calibración GUI (paso dedicado) o Launcher script

## §3. vision_driver — automación Claude API sin calibración — 2026-05-25

- **Qué**: Nuevo módulo `vision_driver.py` que elimina la necesidad de calibración manual. Toma screenshots, llama a Claude haiku, parsea coords JSON, hace clic via pyautogui. Auto-detect en `main()`: si `ANTHROPIC_API_KEY` está configurada usa visión, si no usa calibración.
- **Por qué**: Archivex Clinical es una app .NET MAUI/SkiaSharp — sin soporte de Apple Accessibility API. La visión vía LLM es el único método viable sin coordenadas hardcodeadas.
- **Tests**: 15 passing | lint: clean | 5 nuevos tests en TestVisionDriver
- **Decisión**: Se usó claude-3-5-haiku-20241022 (más barato con visión, ~$0.006/cita). Fallback regex para JSON con texto extra. Reintentos ×3 en click_element.
- **Próximo**: `first_result_dy` calibración GUI (§7) o cobertura ≥ 80% (§10)
