# Architecture Decision Records (ADRs)

Registro de decisiones arquitectónicas significativas en Gmail Bulk Trash.

Format: [ADR template](https://github.com/joelparkerhenderson/architecture_decision_record)

## Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-001](ADR-001-senders-persistence.md) | JSON Local File vs Database | ✅ Accepted | 2026-05-25 |
| [ADR-002](ADR-002-argparse-over-click.md) | argparse vs Click/Typer | ✅ Accepted | 2026-05-25 |
| [ADR-003](ADR-003-batch-size-1000.md) | Batch Size 1000 for batchModify | ✅ Accepted | 2026-05-25 |

## How to Read

1. **Status** → Aceptado (✅), Rechazado (❌), Pendiente (⏳)
2. **Context** → Por qué necesitábamos decidir
3. **Decision** → Qué elegimos
4. **Rationale** → Por qué es la mejor opción
5. **Consequences** → Trade-offs y mitigation strategies

## Adding New ADRs

Cuando una decisión arquitectónica es significativa (afecta múltiples módulos, es difícil de revertir, o tiene trade-offs importantes), crea un ADR:

```
docs/adrs/ADR-NNN-descriptive-title.md
```

Sigue el template en ADR-001.
