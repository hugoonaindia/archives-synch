# Top Senders — Análisis interactivo de remitentes

**Fecha:** 2026-05-25
**Autor:** Hugo (vía brainstorming)

---

## 1. Objetivo

Añadir un modo interactivo `--top-senders` que analice la bandeja de entrada, identifique los remitentes más frecuentes y permita al usuario tomar acciones masivas sobre ellos (trash, blocklist, dry-run).

## 2. Problema que resuelve

El usuario tiene que adivinar qué remitentes están saturando su bandeja. Actualmente debe:
1. Revisar manualmente su bandeja
2. Pensar "¿quién me escribe más?"
3. Añadir esos remitentes uno por uno con `--add-sender`

Con `--top-senders`, el script escanea automáticamente y presenta los datos, permitiendo actuar directamente.

## 3. Interfaz CLI

### Nuevos argumentos

| Flag | Tipo | Default | Descripción |
|------|------|---------|-------------|
| `--top-senders` | `store_true` | `False` | Activa el modo análisis interactivo |
| `--top-limit` | `int` | `20` | Cuántos top senders mostrar |
| `--days` | `int` | `90` | Ventana de tiempo para el análisis (últimos N días) |

### Interacción con flags existentes

| Combinación | Comportamiento |
|-------------|----------------|
| `--top-senders` solo | Busca en últimos 90 días (default) |
| `--top-senders --days 30` | Busca en últimos 30 días |
| `--top-senders --before 2025-01-01` | Analiza correos anteriores a esa fecha |
| `--top-senders --after 2025-06-01 --before 2025-12-31` | Rango específico |
| `--top-senders --query "category:promotions"` | Analiza solo promociones |
| `--top-senders --query "from:linkedin.com"` | Analiza un remitente concreto (poco útil, pero válido) |

**Regla de precedencia:** `--days` es un atajo para `before:today-N`. Si se usa junto con `--before`/`--after`, se combinan (AND). Si el usuario quiere escanear TODO el inbox, omite `--days`.

### Uso

```bash
# Análisis por defecto (últimos 90 días, top 20)
python3 gmail_bulk_trash.py --top-senders

# Top 5 de los últimos 30 días
python3 gmail_bulk_trash.py --top-senders --top-limit 5 --days 30

# Combinado con query específica
python3 gmail_bulk_trash.py --top-senders --query "category:promotions"

# Análisis + añadir a blocklist lo que selecciones
python3 gmail_bulk_trash.py --top-senders --days 365
```

## 4. Flujo interactivo

### Pantalla principal

```
═══ Top Senders (últimos 90 días) ═══
Escaneando... ████████████████████████ 100% (8,432 mensajes)

  #  Remitente                          Correos    Último
 ──────────────────────────────────────────────────────────────
  1  newsletter@promo.com                 1,247    2026-05-20
  2  notifications@linkedin.com             312    2026-05-22
  3  no-reply@amazon.com                    145    2026-05-18
  4  spam@ads.com                            89    2026-05-23
  5  noreply@dropbox.com                     67    2026-05-15
 ...

Selecciona remitente (#), (a)ñadir todos a blocklist, (q)uit: _
```

### Menú de acciones por remitente

```
✉️ newsletter@promo.com (1,247 emails)
  [1] Trash all — mover 1,247 emails a la papelera
  [2] Dry-run — simular cuántos se borrarían
  [3] Add to blocklist — añadir a lista negra
  [4] ← Volver a lista
  [q] Salir

Acción: _
```

### Acción rápida desde lista principal

```
Opción (a): Añadir todos los top senders visibles a blocklist de una vez.
```

## 5. Arquitectura

### Nuevas funciones

```
gmail_bulk_trash.py
├── get_top_senders(service, max_msgs, top_n)
│   ├── get_all_ids() → lista de IDs (reutilizada)
│   ├── extract_senders_from_ids(service, ids)
│   │   └── messages.get(userId='me', id=msg_id, format='metadata', metadataHeaders=['From'])
│   │   └── usa api_call_with_retry() existente
│   └── Counter → sort → top N
│
├── interactive_sender_menu(service, top_senders, senders_data)
│   ├── display_table(top_senders)
│   ├── loop: select → action → execute → back
│   └── uses existing: batch_trash, add_sender
│
└── main() — new branch when --top-senders
```

### Flujo en main()

```
if args.top_senders:
    service = get_service()
    ids = get_all_ids(service, query_con_dias)
    top = get_top_senders(service, ids, args.top_limit)
    interactive_sender_menu(service, top)
    return
```

## 6. Extracción de remitentes

### Llamada API

```python
msg = service.users().messages().get(
    userId='me',
    id=msg_id,
    format='metadata',
    metadataHeaders=['From']
).execute()
```

El response incluye:
```json
{
  "id": "18abc...",
  "payload": {
    "headers": [
      {"name": "From", "value": "Newsletter <newsletter@promo.com>"}
    ]
  }
}
```

### Normalización

```python
import re

def parse_email(from_header: str) -> str:
    # "Newsletter <newsletter@promo.com>" → "newsletter@promo.com"
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).strip().lower()
    return from_header.strip().lower()
```

## 7. Performance y quota

| Operación | Quota/call | Límite | Para 10,000 msgs |
|-----------|-----------|--------|-------------------|
| `messages.list` (páginas) | 1 unit | 250/s | ~20 calls = 20 units |
| `messages.get` (cada msg) | 5 units | 250/s | 10,000 calls = 50,000 units |
| **Total** | | | **~50,020 units (~200s)** |

- Barra de progreso con ETA durante el escaneo (reutiliza patrón de `batch_trash`)
- El retry exponencial existente maneja rate limits
- Limitación práctica: `--days` evita escanear inbox completos enormes

## 8. Validación

### Tests

| Test | Descripción |
|------|-------------|
| `test_parse_email_simple` | `"user@x.com"` → `"user@x.com"` |
| `test_parse_email_with_name` | `"User <user@x.com>"` → `"user@x.com"` |
| `test_parse_email_multi_angle` | `"<a@x.com> <b@x.com>"` → `"a@x.com"` |
| `test_get_top_senders_empty` | Lista vacía → `[]` |
| `test_interactive_add_blocklist` | Mock input/output → verifica save_senders |

### Linting

```bash
python -m pytest tests/ -v
```

## 9. Fuera de alcance (para futuras iteraciones)

- Concurrencia/paralelismo en escaneo (ThreadPoolExecutor)
- Exportar reporte a CSV
- Modo no-interactivo (`--top-senders --json`)
- Clasificación inteligente (newsletters vs notificaciones vs personales)
- Estadísticas de almacenamiento (tamaño total por remitente)

---

## 10. Historial

| Fecha | Cambio |
|-------|--------|
| 2026-05-25 | Spec inicial — Top Senders interactivo |
