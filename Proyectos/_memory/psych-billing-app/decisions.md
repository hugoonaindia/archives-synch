# Decisiones — psych-billing-app

## 2026-05-28 — Monolito confirmado por diseño

**Contexto:** Se había modularizado app.py → core.py + app.py, pero el usuario revirtió explícitamente.

**Decisión:** Mantener single-file monolith (app.py, ~1758 líneas). Toda la lógica de negocio, UI y dialogs en un archivo.

**Consecuencias:** Mantenibilidad ligeramente menor, pero simplicidad de deployment y desarrollo. Se compensa con tests exhaustivos (234 tests, 86% cobertura).

**Alternativas consideradas:** core.py extraído, ui_dialogs.py extraído — ambos revertidos.

## 2026-05-28 — Sync sin modales

**Contexto:** La sincronización con Google Calendar mostraba `mb.showinfo` + `mb.showwarning` modales, congelando la UI post-sync.

**Decisión:** Eliminar todos los modales del flujo de sync. El resumen se muestra en la `sync_label`. Los eventos de fin de semana se agrupan en el label en vez de mostrar un warning por cada uno.

**Consecuencias:** UI responsiva post-sync. Feedback visible pero no bloqueante.

## 2026-05-28 — do_sync siempre sincroniza semana actual

**Contexto:** `do_sync()` usaba `self.week_start` (la semana visible en el calendario), que podía ser una semana diferente si el usuario navegó antes de sincronizar.

**Decisión:** `do_sync()` ahora siempre llama `sync_calendar(get_week_start(0))`, ignorando la navegación del calendario.

**Consecuencias:** El usuario siempre sincroniza la semana real actual, independientemente de la semana que esté viendo.

## 2026-05-28 — Memory vault con Obsidian

**Contexto:** La ventana de contexto del AI se satura con historial de sesiones anteriores. Necesidad de memoria persistente entre sesiones.

**Decisión:** Crear `_memory/` vault con markdown estructurado por proyecto. El AI lee `project_state.md` + `decisions.md` al iniciar, escribe `session_log.md` al finalizar.

**Consecuencias:** Contexto del AI más limpio. Memoria permanente entre sesiones. Compatible con Obsidian como vault.
