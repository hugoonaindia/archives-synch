# ADR-003: Batch Size of 1000 for batchModify

## Status
✅ ACCEPTED

## Context
Gmail API `messages.batchModify` permite hasta 1000 IDs por llamada. El trade-off es:
- **Batch grande (1000)**: Menos llamadas HTTP, pero más datos en memoria si hay delay
- **Batch pequeño (100)**: Más tolerancia a fallos, pero 10x más llamadas HTTP

## Decision
Usar `BATCH_SIZE = 1000` (máximo permitido).

## Rationale
- **API quota efficiency**: Gmail quota es 250 unidades/segundo. 1000 IDs en 1 llamada = 1 unidad.
- **Speed**: Borrar 100k correos en 100 llamadas vs 1000 llamadas = 10x más rápido
- **Memory safety**: 1000 IDs es ~10KB en memoria (negligible)
- **Official recommendation**: Google Cloud recomienda usar máximo batch size para operaciones bulk

## Consequences
### Positivos
- Mejor performance (10x menos latencia HTTP)
- Menos chance de timeout (menos requests = menos lugares para fallar)
- Eficiencia de quota (máximo throughput)

### Negativos
- Si 1 request falla, hay que reintentar 1000 IDs (vs 100)
- Ligeramente más memoria durante ejecución (trivial)

## Mitigation
- Agregar retry logic si un batch falla (TODO: feature future)
- Logging de qué batch falló para facilitar resume parcial

---

**Decision Date**: 2026-05-25
**Reviewed By**: SUPERREVISION PASADA 3
**Related**: Task 6 (batch_trash optimization)
