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
| 4 | Task 4: Archivex window detection via AppleScript | ✨ Feature | Open |
| 5 | Task 5: Haiku verifier with prompt caching | ✨ Feature | Open |
| 6 | Task 6: Appointment processor — pyautogui actions | ✨ Feature | Open |
| 7 | Task 7: Week navigation | ✨ Feature | Open |
| 8 | Task 8: Main sync loop — conflict handling + main() | ✨ Feature | Open |
| 9 | Task 9: recon.py — Opus 4.7 reconnaissance | ✨ Feature | Open |
| 10 | Task 10: Update .gitignore + smoke test | ✨ Feature | Open |

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
