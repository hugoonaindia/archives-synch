# Session Log — psych-billing-app

## 2026-05-28

**Cambios:**
- Fix: GUI tests ya no cuelgan en headless (mb.showinfo mockeado en ctk_mocks)
- Docs: CHANGELOG.md actualizado con todos los cambios post-v1.1.0
- Chore: `__version__` bumped a 1.2.0
- Docs: Master doc actualizado (REV-1-011/012 cerrados, 005 by design)
- Fix: `do_sync()` ahora siempre sincroniza semana actual (get_week_start(0))
- Fix: Eliminados modales post-sync (mb.showinfo/mb.showwarning) — feedback en sync_label
- Refactor: `_handle_sync_results()` sin parámetro `parent`, sin mb.showinfo
- Infra: Instalado Engram v1.16.0 para memoria persistente entre sesiones
- Infra: Creado _memory/ vault con project_state, decisions, session_log
- Infra: Actualizados CLAUDE.md de 6 proyectos con instrucciones Engram

**Próximo:** Bugfixes, features del spec, o iteración de deuda técnica.
