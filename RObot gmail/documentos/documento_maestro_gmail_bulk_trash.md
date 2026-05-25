# Documento Maestro — Gmail Bulk Trash
*Creado: 2026-05-24 | Autor: Hugo*

---

## 1. Visión General

**Gmail Bulk Trash** es una herramienta de línea de comandos en Python para limpiar masivamente el correo de Gmail. Permite mover a la papelera miles de correos en segundos usando la API de Gmail con llamadas en batch (hasta 1000 por llamada).

### Problema que resuelve
Gmail acumula spam, newsletters y correos de promociones que consumen almacenamiento y dificultan encontrar correos importantes. Las herramientas nativas de Gmail son lentas para limpiezas masivas.

### Solución
Script CLI que:
- Acepta filtros flexibles en sintaxis Gmail
- Gestiona una lista persistente de remitentes bloqueados (blocklist)
- Protege remitentes importantes (whitelist)
- Permite simular antes de borrar (dry-run)
- Procesa miles de correos en lotes eficientes

---

## 2. Estado Actual

### Versión base (implementada)
| Feature | Estado |
|---|---|
| Mover a papelera por query Gmail | ✅ Funcional |
| Barra de progreso | ✅ Funcional |
| Auto-instalación de dependencias | ✅ Funcional |
| Autenticación OAuth2 | ✅ Funcional |
| Batch de 1000 mensajes por llamada | ✅ Funcional |
| Query configurable (hardcoded) | ✅ Funcional |

### Versión objetivo (backlog)
| Feature | Estado | Prioridad |
|---|---|---|
| CLI con argparse completo | 🔴 Pendiente | P0 |
| `--dry-run` (simular sin borrar) | 🔴 Pendiente | P0 |
| Blocklist persistente (`senders.json`) | 🔴 Pendiente | P0 |
| `--add-sender` / `--remove-sender` | 🔴 Pendiente | P0 |
| `--list-senders` | 🔴 Pendiente | P0 |
| Whitelist persistente | 🔴 Pendiente | P0 |
| `--add-whitelist` / `--remove-whitelist` | 🔴 Pendiente | P0 |
| Query dinámica desde blocklist | 🔴 Pendiente | P1 |
| `--query` como argumento CLI | 🔴 Pendiente | P1 |
| `--before` / `--after` (filtro por fecha) | 🔴 Pendiente | P1 |
| ETA en barra de progreso | 🔴 Pendiente | P2 |
| Tiempo total al finalizar | 🔴 Pendiente | P2 |

---

## 3. Arquitectura

### Archivos del proyecto

```
RObot gmail/
├── gmail_bulk_trash.py          # Script principal
├── senders.json                 # Blocklist y whitelist (se crea al usar --add-sender)
├── credentials.json             # OAuth2 credentials (Google Cloud Console)
├── token.json                   # Token de sesión (se genera automáticamente)
├── CLAUDE.md                    # Configuración del agente
├── documentos/
│   └── documento_maestro_gmail_bulk_trash.md   # Este archivo
├── docs/
│   └── superpowers/plans/
│       └── 2026-05-24-gmail-bulk-trash-mejoras.md  # Plan de implementación detallado
└── memory/
    └── MEMORY.md
```

### Flujo de ejecución

```
python3 gmail_bulk_trash.py [args]
        │
        ├─ Gestión de remitentes (--add-sender, --list-senders, etc.)
        │   └─ Lee/escribe senders.json → sale sin autenticar
        │
        └─ Limpieza de correos
            ├─ get_service()        → OAuth2
            ├─ load_senders()       → senders.json
            ├─ build_query()        → combina query base + blocklist - whitelist
            ├─ get_all_ids()        → paginación Gmail API
            ├─ [dry-run: mostrar count y salir]
            ├─ [confirmación del usuario]
            └─ batch_trash()        → batchModify en lotes de 1000
```

### `senders.json` — estructura

```json
{
  "blocked": ["spam@example.com", "noreply@linkedin.com"],
  "whitelist": ["mi-banco@banco.com", "trabajo@empresa.com"]
}
```

---

## 4. API de Gmail — Referencia

### Sintaxis de queries (campo `q`)

| Filtro | Ejemplo |
|---|---|
| Por remitente | `from:spam@example.com` |
| Por categoría | `category:promotions` |
| Por categoría social | `category:social` |
| Antes de fecha | `before:2024/01/01` |
| Después de fecha | `after:2023/01/01` |
| Combinado OR | `{from:a@x.com from:b@y.com}` |
| Combinado AND | `from:x.com after:2023/01/01` |
| Excluir | `-from:banco@x.com` |

### Límites de la API
- `messages.list`: max 500 resultados por página
- `messages.batchModify`: max **1000 IDs por llamada**
- Quota: 250 unidades/segundo por usuario

---

## 5. Comandos — Referencia Completa (objetivo)

```bash
# ── Información ──────────────────────────────────────────────────────────────
python3 gmail_bulk_trash.py --help
python3 gmail_bulk_trash.py --list-senders

# ── Gestionar blocklist ───────────────────────────────────────────────────────
python3 gmail_bulk_trash.py --add-sender spam@example.com
python3 gmail_bulk_trash.py --add-sender correo1@x.com correo2@y.com  # múltiples
python3 gmail_bulk_trash.py --remove-sender spam@example.com

# ── Gestionar whitelist ───────────────────────────────────────────────────────
python3 gmail_bulk_trash.py --add-whitelist mi-banco@banco.com
python3 gmail_bulk_trash.py --remove-whitelist mi-banco@banco.com

# ── Simular (sin borrar) ──────────────────────────────────────────────────────
python3 gmail_bulk_trash.py --dry-run
python3 gmail_bulk_trash.py --query "from:linkedin.com" --dry-run
python3 gmail_bulk_trash.py --before 2024-01-01 --dry-run

# ── Borrar con filtros ────────────────────────────────────────────────────────
python3 gmail_bulk_trash.py                              # query por defecto + blocklist
python3 gmail_bulk_trash.py --query "category:social"   # query personalizada
python3 gmail_bulk_trash.py --before 2024-01-01         # emails anteriores a fecha
python3 gmail_bulk_trash.py --after 2023-01-01 --before 2023-12-31  # rango
python3 gmail_bulk_trash.py --query "from:linkedin.com" --before 2024-06-01
```

---

## 6. Setup — Primeros pasos

### Requisitos
- Python 3.10+
- Cuenta Google con Gmail
- Google Cloud project con Gmail API habilitada

### Paso 1: Configurar Google Cloud Console
1. Ir a [console.cloud.google.com](https://console.cloud.google.com)
2. Crear proyecto nuevo (o usar existente)
3. Habilitar **Gmail API**
4. Crear credenciales → **OAuth 2.0 Client ID** → Desktop app
5. Descargar `credentials.json` y colocarlo junto al script

### Paso 2: Primera ejecución
```bash
python3 gmail_bulk_trash.py --dry-run
# → Abrirá navegador para autenticación OAuth2
# → Genera token.json (no vuelve a pedir login)
# → Muestra cuántos correos borraría sin borrar nada
```

### Paso 3: Añadir remitentes no deseados
```bash
python3 gmail_bulk_trash.py --add-sender noreply@linkedin.com
python3 gmail_bulk_trash.py --add-sender notifications@twitter.com
python3 gmail_bulk_trash.py --list-senders   # verificar
```

### Paso 4: Proteger remitentes importantes
```bash
python3 gmail_bulk_trash.py --add-whitelist facturas@banco.com
```

### Paso 5: Ejecutar limpieza
```bash
python3 gmail_bulk_trash.py --dry-run        # revisar primero
python3 gmail_bulk_trash.py                  # ejecutar
```

---

## 7. Decisiones de diseño

| Decisión | Alternativa considerada | Motivo |
|---|---|---|
| `senders.json` como BD local | SQLite | Más simple, portátil, editable a mano |
| argparse stdlib | click/typer | Sin dependencias extra |
| batchModify en lugar de trash individual | `messages.trash()` por ID | 1000x más rápido |
| Whitelist como `-from:` en query | Filtrar IDs en Python | La API filtra en origen, menos datos transferidos |
| Auto-install deps | requirements.txt | El script es standalone, fácil de copiar |

---

## 8. Backlog de features futuras

| # | Feature | Descripción | Prioridad |
|---|---|---|---|
| F-01 | Modo `--unsubscribe` | Detectar link de unsubscribe y abrirlo antes de borrar | ✨ Idea |
| F-02 | Exportar log | Guardar CSV con remitente/fecha/asunto de lo borrado | ✨ Idea |
| F-03 | Estadísticas de almacenamiento | Mostrar espacio estimado liberado | ✨ Idea |
| F-04 | Modo interactivo | Listar remitentes únicos y seleccionar cuáles borrar | ✨ Idea |
| F-05 | `--label` | Mover a etiqueta en lugar de papelera | ✨ Idea |
| F-06 | Scheduled / cron | Instrucciones para ejecutar automáticamente | ✨ Idea |

---

## 9. Historial de iteraciones

### §1. Estado inicial — 2026-05-24
- Script monolítico con query hardcoded
- Funcionalidad base: autenticación OAuth2, búsqueda paginada, batchModify
- Sin CLI, sin blocklist, sin whitelist

### §2. Documento maestro — 2026-05-24
- Bootstrap: creación de CLAUDE.md, documento maestro y memory index
- Plan de implementación creado en `docs/superpowers/plans/`
- Backlog definido con 6 tareas de mejora

### §3. Task 1 — Persistencia de remitentes — 2026-05-25
- **Qué**: Creación de `senders.json` y funciones `load_senders()` / `save_senders()`
- **Por qué**: Foundation para gestión de blocklist/whitelist (Task 2)
- **Tests**: N/A (no hay suite de tests en proyecto)
- **Decisión**: Seguida estructura exacta del plan; archivo JSON simple con estructura `{"blocked": [], "whitelist": []}`
- **Próximo**: Task 2 — Comando `--add-sender` / `--remove-sender` / `--list-senders`

### §4. Task 2 — Gestión CLI de remitentes — 2026-05-25
- **Qué**: Implementación de argparse + función `manage_senders()` con soporte para `--add-sender`, `--remove-sender`, `--add-whitelist`, `--remove-whitelist`, `--list-senders`
- **Por qué**: Permite al usuario gestionar su blocklist/whitelist sin necesidad de editar JSON a mano
- **Tests**: Verificación manual de cada comando ✅
- **Decisión**: Agregué chequeos `hasattr()` en `manage_senders()` para compatibilidad con argparse
- **Próximo**: Task 3 — Construcción dinámica de query desde blocklist

### §5. Task 3 — Query dinámica desde blocklist — 2026-05-25
- **Qué**: Función `build_query()` que combina query base con remitentes bloqueados (OR) y excluye whitelist (-from:)
- **Por qué**: Fundación para filtros dinámicos; permitirá al usuario borrar por remitentes sin escribir queries complejas
- **Tests**: Verificación manual de combinación de queries ✅
- **Decisión**: La query se construye cada ejecución (no se cachea) para mantener flexibilidad
- **Próximo**: Task 4 — Modo `--dry-run`

### §6. Task 4 — Modo --dry-run — 2026-05-25
- **Qué**: Argumento `--dry-run` que muestra cuántos mensajes se moverían sin borrar nada
- **Por qué**: Seguridad; permite revisar el filtro antes de ejecutar la limpieza real
- **Tests**: Verificación de --help y sintaxis ✅
- **Decisión**: Se muestra el mensaje de dry-run antes de pedir confirmación
- **Próximo**: Task 5 — Filtros `--query`, `--before`, `--after`

### §7. Task 5 — Filtros por fecha y query personalizada — 2026-05-25
- **Qué**: Argumentos `--query`, `--before`, `--after` con conversión automática de YYYY-MM-DD a YYYY/MM/DD (formato Gmail API)
- **Por qué**: Permitir al usuario filtrar por rango de fechas y queries personalizadas sin hardcodear
- **Tests**: Verificación de --help y sintaxis ✅
- **Decisión**: Se envuelven las queries en paréntesis para asegurar precedencia correcta; conversión de formato automática
- **Próximo**: Task 6 — Mejor UX (ETA y reporte final)

### §8. Task 6 — UX mejorada (ETA y reporte final) — 2026-05-25
- **Qué**: Función `batch_trash()` mejorada con cálculo de ETA, tasa de procesamiento y tiempo total
- **Por qué**: Feedback visual durante ejecución larga; usuario sabe cuándo terminará
- **Tests**: Verificación de sintaxis ✅; ETA requiere ejecución real contra Gmail API
- **Decisión**: ETA se calcula como (mensajes_restantes / tasa_actual); muestra "casi listo" cuando faltan < 1s
- **Próximo**: Backlog de features futuras (F-01 a F-06) o cierre de ciclo

---

## 10a. Estado final — Plan completado ✅

**Todas las 6 tareas del plan han sido implementadas:**

- [x] Task 1: `senders.json` + funciones load/save
- [x] Task 2: CLI con `--add-sender`, `--remove-sender`, `--add-whitelist`, `--remove-whitelist`, `--list-senders`
- [x] Task 3: Query dinámica desde blocklist + whitelist
- [x] Task 4: Modo `--dry-run`
- [x] Task 5: Filtros `--query`, `--before`, `--after`
- [x] Task 6: ETA y reporte final en barra de progreso

**El script ahora soporta la interfaz completa descrita en §5 (Comandos — Referencia Completa).**

---

## 10. Notas de seguridad

- `credentials.json` y `token.json` **nunca deben subirse a git**
- `senders.json` no contiene datos sensibles — puede versionarse si se desea
- El script solo usa el scope `gmail.modify` (no puede leer cuerpo de emails, solo metadatos e IDs)
- Los correos van a la **papelera** (recuperables durante 30 días), no se eliminan permanentemente
