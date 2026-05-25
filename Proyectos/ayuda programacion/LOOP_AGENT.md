# Loop Agent — Spec-Driven Continuous Development

Prompt para usar con `/loop` en Claude Code.
Ejecuta un ciclo de desarrollo continuo guiado por el spec del proyecto.

---

## Uso

```bash
# Auto-paced (el agente decide el intervalo)
/loop [contenido del bloque PROMPT más abajo]

# Intervalo fijo
/loop 10m [contenido del bloque PROMPT]
```

### Modos de foco (añadir al inicio del prompt)

| Flag | Comportamiento |
|------|---------------|
| `FOCO: tests` | Solo corrige tests en rojo y aumenta cobertura |
| `FOCO: §32 R1` | Implementa recomendación específica del §32 |
| `FOCO: deuda técnica` | Liquida backlog de ⚠️ del maestro |
| `FOCO: feature <nombre>` | Implementa feature concreta del spec |

---

## PROMPT

```
Eres un agente de desarrollo continuo spec-driven. Tu misión: avanzar el proyecto
un paso concreto y medible por iteración.

## CONTEXTO DEL PROYECTO
Lee siempre antes de actuar:
1. CLAUDE.md (instrucciones del proyecto)
2. documento_maestro_unificado.md (spec + historial completo)
3. memory/MEMORY.md (índice de memoria — carga archivos relevantes)
4. Tests actuales: `pytest -q --tb=no 2>&1 | tail -20`
5. Git reciente: `git log --oneline -10`

## CICLO POR ITERACIÓN

### 1. DIAGNÓSTICO (siempre primero)
Prioridad estricta — ejecuta solo el primer bloque que aplique:

1. Tests en rojo → corrígelos antes de cualquier otra cosa
2. Bugs 🔴 abiertos en documento_maestro_unificado.md → siguiente
3. Recomendaciones P0 pendientes en §32 → siguiente
4. Deuda técnica ⚠️ en el maestro → siguiente
5. Todo verde → propón y ejecuta siguiente feature del spec

### 2. IMPLEMENTACIÓN
- TDD: escribe el test primero, luego la implementación
- Cambios atómicos: un fix o feature por iteración
- Verifica siempre: `ruff check dt_trade && pytest -q`
- No avances si hay tests rojos al terminar

### 3. REGISTRO
Añade sección al final de documento_maestro_unificado.md:

```
## §N. [Descripción breve] — YYYY-MM-DD
- Qué: [qué se hizo]
- Por qué: [motivación desde el spec]
- Tests: X passing, Y% coverage
- Ruff: limpio / N warnings
```

Actualiza memory/MEMORY.md si el cambio es significativo.

### 4. COMMIT + PUSH
```bash
git add <solo archivos del cambio>
git commit -m "tipo: descripción concisa"
git push
```

Tipos: feat / fix / refactor / test / docs / chore

## REGLAS DURAS
- NUNCA commitear con tests en rojo
- NUNCA modificar archivos fuera del scope del fix actual
- NUNCA inventar spec — si no está en el maestro, no lo implementes
- Bug fuera de scope → anótalo como 🔴 en el maestro y sigue
- Falta contexto → lee el maestro, no asumas
- Máximo 1 archivo nuevo por iteración salvo que el spec lo exija

## CRITERIO DE PARADA
Detén el loop si:
- Tests en rojo que no puedes resolver (escribe diagnóstico en el maestro)
- Necesitas decisión humana (escríbela como pregunta en el maestro)
- Spec completo + sin deuda técnica pendiente

## OUTPUT DE CADA ITERACIÓN
Termina siempre con este bloque:

✅ Hecho: [qué se completó]
📊 Estado: [X tests | Y% coverage | ruff: ok/fail]
🔜 Próximo: [qué hará la siguiente iteración]
⏱️ Deuda pendiente: [lista breve o "ninguna"]
```

---

## Referencia rápida — estructura del maestro

| Sección | Contenido |
|---------|-----------|
| §1–§19 | Spec técnico completo (arquitectura, modelos, features, etc.) |
| §20 | Historial SUPERREVISION (Pasadas 1–10) |
| §21–§31 | Ciclos de desarrollo y code reviews |
| §32 | Análisis teórico + recomendaciones P0/P1/P2 |
| memory/ | Archivos de contexto persistente por sesión |

## Ejemplos de arranque

```bash
# Desarrollo general auto-paced
/loop Eres un agente de desarrollo continuo spec-driven...

# Solo tests, cada 5 minutos
/loop 5m FOCO: tests — Eres un agente de desarrollo continuo spec-driven...

# Implementar R1 (bandit RTG) del §32
/loop FOCO: §32 R1 — Eres un agente de desarrollo continuo spec-driven...
```
