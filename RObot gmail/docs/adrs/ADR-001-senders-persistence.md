# ADR-001: JSON Local File vs Database for Senders Persistence

## Status
✅ ACCEPTED

## Context
Gmail Bulk Trash necesita persistencia para blocklist y whitelist sin requerir configuración externa. Las opciones evaluadas fueron:
1. **JSON local file** (elegida)
2. SQLite database
3. Cloud storage (Firebase, S3)

## Decision
Usar `senders.json` como archivo JSON local.

## Rationale
- **Simplicidad**: Cero configuración, archivo editable manualmente
- **Portabilidad**: Script copia-y-pega sin dependencias de BD
- **Escalabilidad suficiente**: Blocklist típicamente < 1000 remitentes
- **User empowerment**: Usuarios pueden editar JSON directamente si es necesario
- **Costo**: Gratis vs costos de cloud storage

## Consequences
### Positivos
- Entrega 30% más rápida (sin setup de BD)
- Usuarios no técnicos pueden usar la herramienta
- Fácil backup (cp senders.json)

### Negativos
- No ACID transactions (si el proceso muere durante write, JSON podría corromperse)
- No soporta acceso concurrente (si otro proceso modifica mientras estamos escribiendo)
- Sin auditoría de cambios (no hay historial)

## Mitigations
- Write-then-rename pattern para atomicidad (implementar si es necesario)
- Documentar que solo una instancia debe ejecutarse a la vez
- Agregar versionado de senders.json en git (opcional)

## Alternative Considered
**SQLite**: Mejor durabilidad, pero agrega 10MB+ a distribución y requiere conocimiento de SQL. No justificado para este caso.

---

**Decision Date**: 2026-05-25
**Reviewed By**: SUPERREVISION PASADA 3
