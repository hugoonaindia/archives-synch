# 🧠 Memory Vault — Proyectos

Vault de memoria persistente para agentes AI. Cada proyecto tiene su propio subdirectorio con:

| Archivo | Propósito |
|---------|-----------|
| `project_state.md` | Estado actual: tests, coverage, versión, deuda técnica |
| `decisions.md` | ADRs y decisiones clave de arquitectura |
| `session_log.md` | Bitácora cronológica de sesiones de desarrollo |
| `scratchpad.md` | Notas temporales del agente durante la sesión |

## Proyectos

- [[psych-billing-app/project_state|psych-billing-app]] — Desktop app (Python, CTk)
- [[equilibria/project_state|equilibria]] — 
- [[LSTM RL/project_state|LSTM RL]] — ML project
- [[RObot gmail/project_state|RObot gmail]] — Automation
- [[Trader LSTM/project_state|Trader LSTM]] — Trading
- [[trader supersimple/project_state|trader supersimple]] — Trading

## Reglas

1. El agente **lee** `project_state.md` + `decisions.md` al iniciar cada sesión
2. El agente **escribe** en `scratchpad.md` durante la sesión
3. Al finalizar, **append** a `session_log.md` y **actualiza** `project_state.md`
4. `decisions.md` es **solo append** — no se editan entradas existentes
