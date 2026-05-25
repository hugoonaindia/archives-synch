# Gmail Bulk Trash — Plan de Mejoras

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir `gmail_bulk_trash.py` en una herramienta CLI completa con gestión persistente de remitentes bloqueados, whitelist, modo dry-run, filtros por fecha y mejor UX.

**Architecture:** Se refactoriza el script monolítico en dos archivos: el script principal con argparse para todos los comandos, y `senders.json` como base de datos local persistente de remitentes bloqueados y whitelist. La query final se construye dinámicamente combinando los remitentes del blocklist + el filtro del usuario.

**Tech Stack:** Python 3.10+, argparse, json, google-api-python-client (ya en uso), datetime

---

## Estructura de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `gmail_bulk_trash.py` | Modificar | Script principal con CLI completa |
| `senders.json` | Crear | Persistencia de blocklist y whitelist |

---

## Task 1: Crear `senders.json` y funciones de carga/guardado

**Files:**
- Create: `senders.json`
- Modify: `gmail_bulk_trash.py`

- [ ] **Step 1: Crear `senders.json` inicial**

```json
{
  "blocked": [],
  "whitelist": []
}
```

- [ ] **Step 2: Añadir funciones de carga y guardado al script**

Añadir después de las constantes (`SCRIPT_DIR`, `CREDS_FILE`, `TOKEN_FILE`):

```python
SENDERS_FILE = SCRIPT_DIR / "senders.json"

def load_senders() -> dict:
    if not SENDERS_FILE.exists():
        return {"blocked": [], "whitelist": []}
    import json
    return json.loads(SENDERS_FILE.read_text())

def save_senders(data: dict) -> None:
    import json
    SENDERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
```

- [ ] **Step 3: Verificar manualmente**

```bash
python3 -c "
import sys; sys.argv=['t']
exec(open('gmail_bulk_trash.py').read().split('def main')[0])
d = load_senders()
print('blocklist:', d['blocked'])
print('whitelist:', d['whitelist'])
"
```

Resultado esperado:
```
blocklist: []
whitelist: []
```

- [ ] **Step 4: Commit**

```bash
git add gmail_bulk_trash.py senders.json
git commit -m "feat: add senders.json persistence layer"
```

---

## Task 2: Comando `--add-sender` / `--remove-sender` / `--list-senders`

**Files:**
- Modify: `gmail_bulk_trash.py`

- [ ] **Step 1: Añadir función `manage_senders`**

Añadir antes de `def main()`:

```python
def manage_senders(args) -> bool:
    """Gestiona blocklist y whitelist. Devuelve True si manejó un comando de gestión."""
    data = load_senders()

    if args.add_sender:
        for s in args.add_sender:
            s = s.strip().lower()
            if s not in data["blocked"]:
                data["blocked"].append(s)
                print(f"✅ Añadido a blocklist: {s}")
            else:
                print(f"⚠️  Ya estaba en blocklist: {s}")
        save_senders(data)
        return True

    if args.remove_sender:
        for s in args.remove_sender:
            s = s.strip().lower()
            if s in data["blocked"]:
                data["blocked"].remove(s)
                print(f"✅ Eliminado de blocklist: {s}")
            else:
                print(f"⚠️  No estaba en blocklist: {s}")
        save_senders(data)
        return True

    if args.add_whitelist:
        for s in args.add_whitelist:
            s = s.strip().lower()
            if s not in data["whitelist"]:
                data["whitelist"].append(s)
                print(f"✅ Añadido a whitelist: {s}")
            else:
                print(f"⚠️  Ya estaba en whitelist: {s}")
        save_senders(data)
        return True

    if args.remove_whitelist:
        for s in args.remove_whitelist:
            s = s.strip().lower()
            if s in data["whitelist"]:
                data["whitelist"].remove(s)
                print(f"✅ Eliminado de whitelist: {s}")
            else:
                print(f"⚠️  No estaba en whitelist: {s}")
        save_senders(data)
        return True

    if args.list_senders:
        print("\n📋 BLOCKLIST (remitentes bloqueados):")
        if data["blocked"]:
            for s in data["blocked"]:
                print(f"   🚫 {s}")
        else:
            print("   (vacío)")

        print("\n🛡️  WHITELIST (remitentes protegidos):")
        if data["whitelist"]:
            for s in data["whitelist"]:
                print(f"   ✅ {s}")
        else:
            print("   (vacío)")
        print()
        return True

    return False
```

- [ ] **Step 2: Verificar manualmente — añadir y listar**

```bash
python3 gmail_bulk_trash.py --add-sender spam@example.com newsletter@ads.com
python3 gmail_bulk_trash.py --list-senders
```

Resultado esperado:
```
✅ Añadido a blocklist: spam@example.com
✅ Añadido a blocklist: newsletter@ads.com

📋 BLOCKLIST (remitentes bloqueados):
   🚫 spam@example.com
   🚫 newsletter@ads.com

🛡️  WHITELIST (remitentes protegidos):
   (vacío)
```

- [ ] **Step 3: Verificar que `senders.json` se actualizó**

```bash
cat senders.json
```

Resultado esperado:
```json
{
  "blocked": [
    "spam@example.com",
    "newsletter@ads.com"
  ],
  "whitelist": []
}
```

- [ ] **Step 4: Verificar eliminación**

```bash
python3 gmail_bulk_trash.py --remove-sender spam@example.com
python3 gmail_bulk_trash.py --list-senders
```

- [ ] **Step 5: Commit**

```bash
git add gmail_bulk_trash.py senders.json
git commit -m "feat: add --add-sender, --remove-sender, --list-senders, --add-whitelist, --remove-whitelist commands"
```

---

## Task 3: Construir query dinámica desde blocklist

**Files:**
- Modify: `gmail_bulk_trash.py`

- [ ] **Step 1: Añadir función `build_query`**

Añadir antes de `def main()`:

```python
def build_query(base_query: str, senders: dict) -> str:
    """Combina la query base con los remitentes bloqueados, excluyendo whitelist."""
    parts = []

    if base_query:
        parts.append(f"({base_query})")

    if senders["blocked"]:
        blocked_part = " OR ".join(f"from:{s}" for s in senders["blocked"])
        parts.append(f"({blocked_part})")

    if not parts:
        return ""

    query = " OR ".join(parts)

    # Excluir whitelist
    for protected in senders["whitelist"]:
        query = f"({query}) -from:{protected}"

    return query
```

- [ ] **Step 2: Verificar la función manualmente**

```bash
python3 -c "
import sys; sys.argv=['t']
exec(open('gmail_bulk_trash.py').read().split('def main')[0])
senders = {'blocked': ['spam@test.com', 'ads@promo.com'], 'whitelist': ['boss@company.com']}
q = build_query('{category:promotions}', senders)
print(q)
"
```

Resultado esperado:
```
({category:promotions}) OR (from:spam@test.com OR from:ads@promo.com) -from:boss@company.com
```

- [ ] **Step 3: Conectar en `main()` — reemplazar línea `ids = get_all_ids(service, QUERY)`**

```python
senders  = load_senders()
query    = build_query(args.query or QUERY, senders)

if not query:
    print("⚠️  No hay query ni remitentes bloqueados. Usa --query o --add-sender.")
    sys.exit(1)

ids = get_all_ids(service, query)
```

- [ ] **Step 4: Verificar con `--list-senders` que la query se construye bien antes de ejecutar**

```bash
python3 gmail_bulk_trash.py --dry-run  # (--dry-run se añade en Task 4)
```

- [ ] **Step 5: Commit**

```bash
git add gmail_bulk_trash.py
git commit -m "feat: build query dynamically from blocklist and whitelist"
```

---

## Task 4: Modo `--dry-run`

**Files:**
- Modify: `gmail_bulk_trash.py`

- [ ] **Step 1: Añadir lógica dry-run en `main()`**

Reemplazar el bloque de confirmación y llamada a `batch_trash`:

```python
if not ids:
    print("✅ No hay mensajes que coincidan con el filtro.")
    return

if args.dry_run:
    print(f"🔍 DRY RUN — Se moverían {len(ids)} mensajes a la papelera.")
    print("   Ejecuta sin --dry-run para aplicar los cambios.")
    return

confirm = input(f"¿Mover {len(ids)} mensajes a la papelera? (s/n): ").strip().lower()
if confirm != "s":
    print("Cancelado.")
    return

print()
batch_trash(service, ids)
```

- [ ] **Step 2: Verificar dry-run**

```bash
python3 gmail_bulk_trash.py --dry-run
```

Resultado esperado (sin borrar nada):
```
═══════════════════════════════════
   Gmail Bulk Trash — by Hugo
═══════════════════════════════════

🔍 Buscando: ...

📬 Total: N mensajes

🔍 DRY RUN — Se moverían N mensajes a la papelera.
   Ejecuta sin --dry-run para aplicar los cambios.
```

- [ ] **Step 3: Commit**

```bash
git add gmail_bulk_trash.py
git commit -m "feat: add --dry-run mode"
```

---

## Task 5: Filtros `--query`, `--before`, `--after`

**Files:**
- Modify: `gmail_bulk_trash.py`

- [ ] **Step 1: Añadir argumentos CLI con `argparse` al inicio de `main()`**

Reemplazar el `def main()` existente con:

```python
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Gmail Bulk Trash — by Hugo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 gmail_bulk_trash.py                        # Usa query por defecto + blocklist
  python3 gmail_bulk_trash.py --dry-run              # Simula sin borrar
  python3 gmail_bulk_trash.py --query "from:spam.com"
  python3 gmail_bulk_trash.py --before 2024-01-01
  python3 gmail_bulk_trash.py --after 2023-01-01 --before 2023-12-31
  python3 gmail_bulk_trash.py --add-sender spam@example.com
  python3 gmail_bulk_trash.py --remove-sender spam@example.com
  python3 gmail_bulk_trash.py --add-whitelist boss@work.com
  python3 gmail_bulk_trash.py --list-senders
        """
    )

    # Comandos de gestión
    parser.add_argument("--add-sender",      nargs="+", metavar="EMAIL", help="Añadir remitente(s) al blocklist")
    parser.add_argument("--remove-sender",   nargs="+", metavar="EMAIL", help="Eliminar remitente(s) del blocklist")
    parser.add_argument("--add-whitelist",   nargs="+", metavar="EMAIL", help="Añadir remitente(s) a la whitelist (nunca se borrarán)")
    parser.add_argument("--remove-whitelist",nargs="+", metavar="EMAIL", help="Eliminar remitente(s) de la whitelist")
    parser.add_argument("--list-senders",    action="store_true",        help="Mostrar blocklist y whitelist")

    # Filtros de búsqueda
    parser.add_argument("--query",   metavar="QUERY",  help="Query Gmail personalizada (sobreescribe la por defecto)")
    parser.add_argument("--before",  metavar="FECHA",  help="Borrar emails ANTES de esta fecha (formato: YYYY-MM-DD)")
    parser.add_argument("--after",   metavar="FECHA",  help="Borrar emails DESPUÉS de esta fecha (formato: YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin borrar nada")

    args = parser.parse_args()

    print("\n═══════════════════════════════════")
    print("   Gmail Bulk Trash — by Hugo")
    print("═══════════════════════════════════")

    # Manejar comandos de gestión (no necesitan autenticación)
    if manage_senders(args):
        return

    try:
        service = get_service()
        senders = load_senders()

        # Construir query base
        base = args.query or QUERY

        # Añadir filtros de fecha
        if args.before:
            base = f"({base}) before:{args.before.replace('-', '/')}"
        if args.after:
            base = f"({base}) after:{args.after.replace('-', '/')}"

        query = build_query(base, senders)

        if not query:
            print("⚠️  No hay query ni remitentes bloqueados.")
            print("   Usa --query 'tu filtro' o --add-sender email@ejemplo.com")
            sys.exit(1)

        ids = get_all_ids(service, query)

        if not ids:
            print("✅ No hay mensajes que coincidan con el filtro.")
            return

        if args.dry_run:
            print(f"🔍 DRY RUN — Se moverían {len(ids)} mensajes a la papelera.")
            print("   Ejecuta sin --dry-run para aplicar los cambios.")
            return

        confirm = input(f"¿Mover {len(ids)} mensajes a la papelera? (s/n): ").strip().lower()
        if confirm != "s":
            print("Cancelado.")
            return

        print()
        batch_trash(service, ids)

    except HttpError as e:
        print(f"\n❌ Error de la API: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario.")
```

- [ ] **Step 2: Verificar `--help`**

```bash
python3 gmail_bulk_trash.py --help
```

Resultado esperado: menú de ayuda con todos los argumentos.

- [ ] **Step 3: Verificar filtro por fecha con dry-run**

```bash
python3 gmail_bulk_trash.py --before 2024-01-01 --dry-run
```

- [ ] **Step 4: Verificar query personalizada**

```bash
python3 gmail_bulk_trash.py --query "from:linkedin.com" --dry-run
```

- [ ] **Step 5: Commit**

```bash
git add gmail_bulk_trash.py
git commit -m "feat: add --query, --before, --after CLI arguments"
```

---

## Task 6: Mejor UX — ETA y reporte final

**Files:**
- Modify: `gmail_bulk_trash.py`

- [ ] **Step 1: Reemplazar `batch_trash` con versión mejorada con ETA**

```python
def batch_trash(service, ids: list[str]) -> None:
    import time
    total   = len(ids)
    trashed = 0
    start   = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = ids[i : i + BATCH_SIZE]
        service.users().messages().batchModify(
            userId="me",
            body={
                "ids":            batch,
                "addLabelIds":    ["TRASH"],
                "removeLabelIds": ["INBOX"],
            },
        ).execute()
        trashed += len(batch)
        elapsed  = time.time() - start
        rate     = trashed / elapsed if elapsed > 0 else 0
        remaining = int((total - trashed) / rate) if rate > 0 else 0
        pct      = round(trashed / total * 100)
        bar      = "█" * (pct // 5) + "░" * (20 - pct // 5)
        eta_str  = f"{remaining}s restantes" if remaining > 0 else "casi listo"
        print(f"  [{bar}] {pct}%  ({trashed}/{total})  ⏱ {eta_str}   ", end="\r")

    elapsed_total = round(time.time() - start)
    print(f"\n\n✅ {trashed} correos movidos a la papelera en {elapsed_total}s.")
    print(f"   Vacíala en Gmail cuando quieras para liberar espacio definitivamente.\n")
```

- [ ] **Step 2: Verificar visualmente la barra de progreso**

```bash
python3 gmail_bulk_trash.py --query "category:promotions" --dry-run
# (sin dry-run para ver la barra real solo si tienes mensajes de prueba)
```

- [ ] **Step 3: Commit**

```bash
git add gmail_bulk_trash.py
git commit -m "feat: add ETA and elapsed time to progress bar"
```

---

## Estado final del script

Al terminar todas las tareas, el script debe soportar:

```bash
# Ver ayuda
python3 gmail_bulk_trash.py --help

# Gestionar blocklist
python3 gmail_bulk_trash.py --add-sender spam@example.com newsletters@promo.com
python3 gmail_bulk_trash.py --remove-sender newsletters@promo.com
python3 gmail_bulk_trash.py --list-senders

# Proteger remitentes
python3 gmail_bulk_trash.py --add-whitelist mi-banco@banco.com trabajo@empresa.com
python3 gmail_bulk_trash.py --remove-whitelist trabajo@empresa.com

# Simular antes de borrar
python3 gmail_bulk_trash.py --dry-run
python3 gmail_bulk_trash.py --query "from:linkedin.com" --dry-run

# Filtrar por fecha
python3 gmail_bulk_trash.py --before 2024-01-01
python3 gmail_bulk_trash.py --after 2023-01-01 --before 2023-12-31

# Combinado
python3 gmail_bulk_trash.py --query "category:promotions" --before 2024-06-01 --dry-run
```

---

## Self-Review

### Cobertura del spec
- [x] Gestión de remitentes no deseados (blocklist) → Tasks 1-3
- [x] Whitelist → Task 2 (`--add-whitelist`, `--remove-whitelist`)
- [x] Dry-run → Task 4
- [x] Argumentos CLI → Task 5
- [x] Filtro por fecha → Task 5
- [x] Mejor UX / ETA → Task 6

### Consistencia de tipos
- `load_senders()` devuelve `dict` con keys `"blocked"` y `"whitelist"` → usado igual en `build_query()` y `manage_senders()`
- `build_query(base: str, senders: dict) -> str` → llamado en `main()` con misma firma
- `manage_senders(args)` recibe el `Namespace` de argparse → accede a `args.add_sender`, etc., todos definidos en `parser.add_argument`

### Sin placeholders
Revisado — todos los steps tienen código completo.
