# Archivex Sync — Spec
*Bootstrapped 2026-05-25 — plan en docs/superpowers/plans/2026-05-25-archivex-sync-rewrite.md*

## Goal

Dos scripts Python:
1. `recon.py` — Opus 4.7 analiza Archivex Clinical visualmente y guarda `ui_knowledge.json` con coordenadas relativas y firmas visuales
2. `sync.py` — monolito que lee Google Calendar (semana actual), filtra lunes y miércoles, y crea las citas restantes en Archivex via pyautogui + Haiku cacheado para verificaciones semánticas

## Architecture

```
recon.py          ← reconocimiento Opus 4.7 (una vez)
sync.py           ← monolito de sync (cada semana)
requirements.txt
pyproject.toml
tests/
  test_sync.py
  test_recon.py
~/.config/archivex-sync/
  ui_knowledge.json    (producido por recon, nunca commiteado)
  token_calendar.json  (OAuth, nunca commiteado)
```

## §1. Backlog

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1 | Task 1: Project foundation (requirements, pyproject, tests/__init__) | ✨ Feature | ✅ Done |
| 2 | Task 2: Appointment dataclass + Calendar reader + Mon/Wed filter | ✨ Feature | ✅ Done |
| 3 | Task 3: Knowledge base loader + coordinate calculator | ✨ Feature | ✅ Done |
| 4 | Task 4: Archivex window detection via AppleScript | ✨ Feature | ✅ Done |
| 5 | Task 5: Haiku verifier with prompt caching | ✨ Feature | ✅ Done |
| 6 | Task 6: Appointment processor — pyautogui actions | ✨ Feature | ✅ Done |
| 7 | Task 7: Week navigation | ✨ Feature | ✅ Done |
| 8 | Task 8: Main sync loop — conflict handling + main() | ✨ Feature | ✅ Done |
| 9 | Task 9: recon.py — Opus 4.7 reconnaissance | ✨ Feature | ✅ Done |
| 10 | Task 10: Update .gitignore + smoke test | ✨ Feature | ✅ Done |

## §2. Historial

## §2. Task 1 — Project foundation — 2026-05-25

- **Qué**: requirements.txt, pyproject.toml (ruff+pytest config), tests/__init__.py, CLAUDE.md
- **Por qué**: Backlog #1 — prerequisito de todo
- **Tests**: 0 (aún no hay) | lint: clean
- **Próximo**: Task 2 — Appointment dataclass + Calendar reader + Mon/Wed filter

## §3. Task 2 — Appointment + Calendar reader + Mon/Wed filter — 2026-05-25

- **Qué**: Dataclass Appointment, get_week_appointments() con filtro SKIP_DAYS={0,2}, OAuth2 stub
- **Por qué**: Backlog #2
- **Tests**: 7 passing | lint: clean
- **Próximo**: Task 3 — Knowledge base loader + coordinate calculator

## §4. Task 3 — Knowledge base + coordinate calculator — 2026-05-25

- **Qué**: validate_knowledge(), load_knowledge(), abs_coords(), slot_coords() en §5 de sync.py
- **Por qué**: Backlog #3
- **Tests**: 13 passing | lint: clean
- **Próximo**: Task 4 — Archivex window detection via AppleScript

## §5. Tasks 4-10 — sync.py completo + recon.py — 2026-05-25

- **Qué**: §6 window detection (AppleScript), §7 Haiku verifier (prompt caching), §8 pyautogui processor, §9 navigation (detect_displayed_monday + navigate_to_week), §10 conflict handling + StopSync, §11 main(). Más recon.py completo con validate_recon_output() y Opus 4.7.
- **Por qué**: Backlog #4-10 — completar el sistema desde cero
- **Tests**: 39 passing | lint: clean | smoke: OK
- **Decisión**: Bug en plan original — mock usaba `mock_ant.Anthropic.return_value` pero debía ser `mock_ant.return_value`. Corregido en tests.
- **Próximo**: Sistema completo — ejecutar `python recon.py` con Archivex abierto para generar ui_knowledge.json

## §6. Migración OpenRouter (Anthropic SDK → OpenAI SDK) — 2026-05-25

- **Qué**: Reemplaza `anthropic>=0.40.0` por `openai>=1.0.0`. sync.py y recon.py usan `OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)`. Formato de imagen cambia a `image_url`. Respuesta pasa de `resp.content[0].text` a `resp.choices[0].message.content`. `_ask_haiku` renombrado a `_ask_llm`. Modelo por defecto: `meta-llama/llama-3.2-11b-vision-instruct:free`.
- **Por qué**: Usuario tiene OPENROUTER_API_KEY (no ANTHROPIC_API_KEY). Usa modelos gratuitos de OpenRouter.
- **Tests**: 39 passing | lint: clean
- **Decisión**: Se mantiene el mismo modelo free para recon y verify. Se puede sobreescribir con `ARCHIVEX_RECON_MODEL` / `ARCHIVEX_VERIFY_MODEL`.
- **Próximo**: Ejecutar `python recon.py` con Archivex abierto para generar ui_knowledge.json

## §7. Hardening: validación de API key y timeout — 2026-05-25

- **Qué**: Mueve validación de `OPENROUTER_API_KEY` de `detect_displayed_monday()` a `main()`. Añade timeout=60s en `_ask_llm()` y timeout=120s en `recon.py:run_recon()`. Mejora manejo de excepciones con logging específico. Envuelve API call en try/except para aislar fallos.
- **Por qué**: Tests fallaban porque `detect_displayed_monday()` validaba la API key antes de que los mocks pudieran ejecutarse. Validar al startup (no por función) permite mocking limpio. Timeouts previenen cuelgues indefinidos. Logging mejora diagnóstico.
- **Tests**: 39 passing (34 test_sync.py + 5 test_recon.py) | lint: clean
- **Decisión**: Validar entorno una sola vez al startup (main), no en funciones individuales. Esto sigue arquitectura de validación de externalidades al inicio.
- **Próximo**: Sistema completo — está listo para usar
