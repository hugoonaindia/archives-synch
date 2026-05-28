# Project State — psych-billing-app

## Meta
- **Última actualización:** 2026-05-28
- **Versión:** 1.2.0
- **Rating:** GOLD 9.25/10

## Tests
- **Total:** 234
- **Pasados:** 234
- **Fallados:** 0
- **Cobertura:** 86%

## Lint
- **Estado:** ✅ limpio (`ruff check .`)

## Stack
- Python 3.13, CustomTkinter, pytest, ruff
- Google Calendar API (readonly), Fernet encryption, RapidFuzz

## Deuda Técnica
| ID | Prioridad | Descripción | Estado |
|----|-----------|-------------|--------|
| REV-1-005 | ⚠️ | app.py monolito (1700+ líneas) | by design |
| REV-1-008 | ⚠️ | Smoke test CI con xvfb | deferred |
| REV-1-011 | 🟢 | Type hints en UI | completado |
| REV-1-012 | 🟢 | CHANGELOG | completado (v1.2.0) |

## Próximo
Bugfixes, features del spec, o nueva iteración de deuda técnica.
