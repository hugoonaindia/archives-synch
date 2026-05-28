# equilibria

**Goal**: Flask web app para gestión de práctica terapéutica.

**Stack**: Python, Flask

**Tests**: pytest -q --tb=short

**Lint**: ruff check .

**Master Doc**: DOCUMENTO_MAESTRO.md

**Vault**: `../_memory/equilibria/` (abrir como vault de Obsidian)

## Memoria Persistente (Engram)
Este proyecto usa Engram para memoria persistente entre sesiones:
- `mem_search --project equilibria` — buscar memorias previas
- `mem_save --project equilibria` — guardar hitos y decisiones
- `mem_context --project equilibria` — contexto de la sesión anterior
