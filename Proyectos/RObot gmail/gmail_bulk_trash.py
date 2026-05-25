#!/usr/bin/env python3
"""
gmail_bulk_trash.py
-------------------
Herramienta CLI para limpiar masivamente el correo de Gmail usando la API.

Características:
  - Gestión de blocklist/whitelist persistente (senders.json)
  - Filtros dinámicos (query, fecha)
  - Modo dry-run para simular
  - Barra de progreso con ETA
  - Auto-instalación de dependencias

Uso:
    python gmail_bulk_trash.py --help          # Ver todos los comandos
    python gmail_bulk_trash.py --list-senders  # Mostrar blocklist/whitelist
    python gmail_bulk_trash.py --dry-run       # Simular sin borrar
    python gmail_bulk_trash.py                 # Ejecutar limpieza

Ver documentos/documento_maestro_gmail_bulk_trash.md para más detalles.
"""

# ── Auto-instalación de dependencias ─────────────────────────────────────────
import subprocess
import sys

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q", "--break-system-packages"])

REQUIRED_PKGS = {
    "google-auth": "google.auth",
    "google-auth-oauthlib": "google_auth_oauthlib",
    "google-api-python-client": "googleapiclient",
}

for pkg, mod in REQUIRED_PKGS.items():
    try:
        __import__(mod)
    except ImportError:
        print(f"📦 Instalando {pkg}...")
        install(pkg)

# ── Imports ───────────────────────────────────────────────────────────────────
import argparse
from collections import Counter
from datetime import datetime, timedelta
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0

def api_call_with_retry(fn: Callable[[], Any], description: str = "API call") -> Any:
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except HttpError as e:
            if e.resp.status == 429 and attempt < MAX_RETRIES - 1:
                wait = INITIAL_BACKOFF * (2 ** attempt)
                print(f"\n⚠️  Rate limit en {description}. Reintentando en {wait:.0f}s... ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                raise

# ── Configuración ─────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Filtro — edítalo a tu gusto con sintaxis Gmail
QUERY = "{from:noreply category:promotions category:social}"

BATCH_SIZE = 1000  # máximo permitido por la API

# Busca credentials.json en la misma carpeta que este script
SCRIPT_DIR   = Path(__file__).parent
CREDS_FILE   = SCRIPT_DIR / "credentials.json"
TOKEN_FILE   = SCRIPT_DIR / "token.json"
SENDERS_FILE = SCRIPT_DIR / "senders.json"

def load_senders() -> dict:
    if not SENDERS_FILE.exists():
        return {"blocked": [], "whitelist": []}
    try:
        data = json.loads(SENDERS_FILE.read_text())
        if "blocked" not in data or "whitelist" not in data:
            print(f"⚠️  {SENDERS_FILE} tiene formato incorrecto. Regenerando...")
            return {"blocked": [], "whitelist": []}
        return data
    except json.JSONDecodeError:
        print(f"⚠️  {SENDERS_FILE} está corrupto. Regenerando...")
        return {"blocked": [], "whitelist": []}

def save_senders(data: dict) -> None:
    SENDERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def parse_email(from_header: str) -> str:
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).strip().lower()
    return from_header.strip().lower()


# ── Autenticación ─────────────────────────────────────────────────────────────

def get_service() -> Any:
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(f"\n❌ No se encontró credentials.json en:\n   {CREDS_FILE}")
                print("   Descárgalo desde Google Cloud Console y ponlo junto a este script.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())
        print("✅ Autorización guardada en token.json (no volverá a pedirte login)")

    return build("gmail", "v1", credentials=creds)

# ── Query builder ────────────────────────────────────────────────────────────

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

# ── Búsqueda ──────────────────────────────────────────────────────────────────

def get_all_ids(service: Any, query: str) -> list[str]:
    ids = []
    page_token = None

    print(f"\n🔍 Buscando: {query}\n")

    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token

        resp = api_call_with_retry(
            lambda kw=kwargs: service.users().messages().list(**kw).execute(),
            "messages.list"
        )
        msgs = resp.get("messages", [])
        ids.extend(m["id"] for m in msgs)

        page_token = resp.get("nextPageToken")
        print(f"   {len(ids)} mensajes encontrados...", end="\r")

        if not page_token:
            break

    print(f"\n📬 Total: {len(ids)} mensajes\n")
    return ids

# ── Gestión de remitentes ────────────────────────────────────────────────────

def manage_senders(args: argparse.Namespace) -> bool:
    """Gestiona blocklist y whitelist. Devuelve True si manejó un comando de gestión."""
    data = load_senders()

    # Procesar comandos de adición/eliminación
    commands = [
        ('add_sender', 'blocked', '✅ Añadido a blocklist:', '⚠️  Ya estaba en blocklist:'),
        ('remove_sender', 'blocked', '✅ Eliminado de blocklist:', '⚠️  No estaba en blocklist:'),
        ('add_whitelist', 'whitelist', '✅ Añadido a whitelist:', '⚠️  Ya estaba en whitelist:'),
        ('remove_whitelist', 'whitelist', '✅ Eliminado de whitelist:', '⚠️  No estaba en whitelist:'),
    ]

    for cmd_attr, list_key, success_msg, error_msg in commands:
        cmd_value = getattr(args, cmd_attr, None)
        if cmd_value:
            is_add = 'add' in cmd_attr
            for s in cmd_value:
                s = s.strip().lower()
                exists = s in data[list_key]
                if (is_add and not exists) or (not is_add and exists):
                    if is_add:
                        data[list_key].append(s)
                    else:
                        data[list_key].remove(s)
                    print(f"{success_msg} {s}")
                else:
                    print(f"{error_msg} {s}")
            save_senders(data)
            return True

    # Mostrar listas
    if getattr(args, 'list_senders', False):
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

# ── Análisis de remitentes ────────────────────────────────────────────────

def get_top_senders(service: Any, ids: list[str], top_n: int = 20) -> tuple[list[tuple[str, int]], dict[str, list[str]]]:
    counter: Counter = Counter()
    sender_ids: dict[str, list[str]] = {}
    total = len(ids)

    print(f"\n🔍 Escaneando {total} mensajes para análisis de remitentes...\n")

    for i, msg_id in enumerate(ids):
        try:
            msg = api_call_with_retry(
                lambda mid=msg_id: service.users().messages().get(
                    userId="me", id=mid, format="metadata", metadataHeaders=["From"]
                ).execute(),
                f"messages.get ({i+1}/{total})"
            )
            headers = msg.get("payload", {}).get("headers", [])
            from_val = next((h["value"] for h in headers if h["name"] == "From"), "")
            email = parse_email(from_val)
            if email:
                counter[email] += 1
                sender_ids.setdefault(email, []).append(msg_id)
        except HttpError:
            pass

        pct = round((i + 1) / total * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  [{bar}] {pct}%  ({i+1}/{total})  {len(counter)} remitentes únicos   ", end="\r")

    print()

    top_senders = counter.most_common(top_n)
    top_emails = {email for email, _ in top_senders}
    sender_ids = {k: v for k, v in sender_ids.items() if k in top_emails}

    return top_senders, sender_ids


def interactive_sender_menu(service: Any, top_senders: list[tuple[str, int]], sender_ids: dict[str, list[str]], senders: dict) -> bool:
    modified = False

    while True:
        print("\n╔════════════════════════════════════════════╗")
        print("║         Top Senders — Análisis             ║")
        print("╚════════════════════════════════════════════╝\n")
        print(f"  {'#':>3}  {'Remitente':<30} {'Correos':>8}")
        print(f"  {'─'*3}  {'─'*30} {'─'*8}")
        for i, (email, count) in enumerate(top_senders, 1):
            print(f"  {i:>3}  {email:<30} {count:>8,}")
        print(f"  {'─'*3}  {'─'*30} {'─'*8}")

        cmd = input("\nSelecciona remitente (#), (a)ñadir todos a blocklist, (q)uit: ").strip().lower()

        if cmd == "q":
            break
        elif cmd == "a":
            for email, _ in top_senders:
                if email not in senders["blocked"]:
                    senders["blocked"].append(email)
                    print(f"✅ Añadido a blocklist: {email}")
                else:
                    print(f"⚠️  Ya estaba en blocklist: {email}")
            save_senders(senders)
            modified = True
            break
        elif cmd.isdigit():
            idx = int(cmd) - 1
            if 0 <= idx < len(top_senders):
                email, count = top_senders[idx]
                modified = _handle_sender_action(service, email, count, sender_ids.get(email, []), senders) or modified
            else:
                print("⚠️  Número fuera de rango.")
        else:
            print("⚠️  Comando no válido.")

    return modified


def _handle_sender_action(service: Any, email: str, count: int, ids: list[str], senders: dict) -> bool:
    while True:
        print(f"\n✉️  {email} ({count:,} emails)")
        print("  [1] Trash all — mover a la papelera")
        print("  [2] Dry-run — simular sin borrar")
        print("  [3] Add to blocklist")
        print("  [4] ← Volver")
        print("  [q] Salir")
        action = input("\nAcción: ").strip().lower()

        if action == "1":
            batch_trash(service, ids)
            return True
        elif action == "2":
            print(f"\n🔍 DRY RUN — Se moverían {len(ids)} emails de {email} a la papelera.")
            print("   Usa 'Trash all' para aplicar.\n")
            input("Presiona Enter para continuar...")
        elif action == "3":
            if email not in senders["blocked"]:
                senders["blocked"].append(email)
                save_senders(senders)
                print(f"✅ Añadido a blocklist: {email}")
            else:
                print(f"⚠️  Ya estaba en blocklist: {email}")
            return True
        elif action == "4":
            return False
        elif action == "q":
            return False
        else:
            print("⚠️  Acción no válida.")

def batch_trash(service: Any, ids: list[str]) -> None:
    total   = len(ids)
    trashed = 0
    failed  = 0
    start   = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = ids[i : i + BATCH_SIZE]
        try:
            api_call_with_retry(
                lambda b=batch: service.users().messages().batchModify(
                    userId="me",
                    body={
                        "ids":            b,
                        "addLabelIds":    ["TRASH"],
                        "removeLabelIds": ["INBOX"],
                    },
                ).execute(),
                f"batchModify ({i+1}-{min(i+BATCH_SIZE, total)})"
            )
            trashed += len(batch)
        except HttpError:
            failed += len(batch)
        elapsed   = time.time() - start
        processed = trashed + failed
        rate      = trashed / elapsed if elapsed > 0 else 0
        remaining = int((total - processed) / rate) if rate > 0 else 0
        pct       = round(processed / total * 100)
        bar       = "█" * (pct // 5) + "░" * (20 - pct // 5)
        eta_str   = f"{remaining}s restantes" if remaining > 0 else "casi listo"
        status    = f"  [{bar}] {pct}%  ({trashed}/{total})  ⏱ {eta_str}"
        if failed:
            status += f"  ⚠️ {failed} fallidos"
        print(f"{status}   ", end="\r")

    elapsed_total = round(time.time() - start)
    print(f"\n\n✅ {trashed} correos movidos a la papelera en {elapsed_total}s.")
    if failed:
        print(f"⚠️  {failed} correos no pudieron procesarse.")
    print("   Vacíala en Gmail cuando quieras para liberar espacio definitivamente.\n")

# ── Menú interactivo ──────────────────────────────────────────────────────────

def _bulk_trash_interactive() -> None:
    print("\n═══════════════════════════════════")
    print("   Limpieza masiva por filtros")
    print("═══════════════════════════════════")
    print("(Deja vacío para omitir un filtro)\n")

    sender = input("Remitente (from:): ").strip()
    subject = input("Palabra en asunto (subject:): ").strip()
    content = input("Palabra en cuerpo: ").strip()
    before = input("Antes de fecha (YYYY-MM-DD): ").strip()
    after = input("Después de fecha (YYYY-MM-DD): ").strip()
    label = input("Etiqueta (label:): ").strip()

    query_parts = []
    if sender:
        query_parts.append(f"from:{sender}")
    if subject:
        query_parts.append(f"subject:{subject}")
    if label:
        query_parts.append(f"label:{label}")
    if content:
        query_parts.append(content)

    base = " ".join(query_parts) if query_parts else ""

    if before:
        base = f"({base}) before:{before.replace('-', '/')}" if base else f"before:{before.replace('-', '/')}"
    if after:
        base = f"({base}) after:{after.replace('-', '/')}" if base else f"after:{after.replace('-', '/')}"

    print(f"\nQuery: {base or '(todas las bandejas)'}")

    dry = input("¿Solo simular (dry-run)? (s/n): ").strip().lower()
    dry_run = dry == "s"

    try:
        service = get_service()
        senders = load_senders()
        query = build_query(base, senders)

        if not query and not sender:
            print("⚠️  Debes especificar al menos un filtro.")
            return

        ids = get_all_ids(service, query)

        if not ids:
            print("✅ No hay mensajes que coincidan.")
            return

        if dry_run:
            print(f"\n🔍 DRY RUN — Se moverían {len(ids)} mensajes a la papelera.")
            return

        confirm = input(f"\n¿Mover {len(ids)} mensajes a la papelera? (s/n): ").strip().lower()
        if confirm == "s":
            batch_trash(service, ids)
        else:
            print("Cancelado.")
    except HttpError as e:
        print(f"\n❌ Error de la API: {e}")
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario.")


def _manage_list_menu(list_key: str, title: str, icon: str) -> None:
    while True:
        data = load_senders()
        items = data[list_key]

        print(f"\n╔══════════════════════════════════╗")
        print(f"║      {title:<31}║")
        print(f"╚══════════════════════════════════╝")

        if items:
            for i, s in enumerate(items, 1):
                print(f"  {icon} {i:>2}. {s}")
        else:
            print(f"  (vacío)")

        print(f"\n  [1] Añadir remitente")
        print(f"  [2] Eliminar remitente")
        print(f"  [v] Volver al menú principal")
        choice = input("\nOpción: ").strip().lower()

        if choice == "v":
            break
        elif choice == "1":
            email = input("Email: ").strip().lower()
            if email and email not in data[list_key]:
                data[list_key].append(email)
                save_senders(data)
                print(f"✅ Añadido: {email}")
            elif email in data[list_key]:
                print(f"⚠️  Ya estaba en la lista.")
        elif choice == "2":
            n = input("Número del remitente a eliminar: ").strip()
            if n.isdigit() and 1 <= int(n) <= len(items):
                removed = items.pop(int(n) - 1)
                save_senders(data)
                print(f"✅ Eliminado: {removed}")
        else:
            print("⚠️  Opción no válida.")


def _run_top_senders_menu(args: argparse.Namespace) -> None:
    try:
        service = get_service()
        senders = load_senders()

        base = args.query or ""
        days = args.days if args.days > 0 else 90
        cutoff = datetime.now() - timedelta(days=days)
        date_query = f"before:{cutoff.strftime('%Y/%m/%d')}"

        parts = [p for p in [base, date_query] if p]
        query = " ".join(parts)

        if args.before:
            query = f"({query}) before:{args.before.replace('-', '/')}" if query else f"before:{args.before.replace('-', '/')}"
        if args.after:
            query = f"({query}) after:{args.after.replace('-', '/')}" if query else f"after:{args.after.replace('-', '/')}"

        ids = get_all_ids(service, query)

        if not ids:
            print("✅ No hay mensajes en el rango especificado.")
            return

        top, sender_id_map = get_top_senders(service, ids, args.top_limit)

        if not top:
            print("No se pudieron identificar remitentes.")
            return

        interactive_sender_menu(service, top, sender_id_map, senders)

    except HttpError as e:
        print(f"\n❌ Error de la API: {e}")
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario.")


def show_menu() -> None:
    while True:
        print("\n╔══════════════════════════════════╗")
        print("║    Gmail Bulk Trash — by Hugo    ║")
        print("╚══════════════════════════════════╝")
        print("  [1] 🔍  Analizar top senders")
        print("  [2] 🗑️   Limpieza masiva por filtros")
        print("  [3] 📋  Gestionar blocklist")
        print("  [4] 🛡️   Gestionar whitelist")
        print("  [q] Salir")

        choice = input("\nOpción: ").strip().lower()

        if choice == "q":
            print("\n¡Hasta luego! 👋\n")
            break
        elif choice == "1":
            _run_top_senders_menu(argparse.Namespace(
                query=None, days=0, before=None, after=None, top_limit=20
            ))
        elif choice == "2":
            _bulk_trash_interactive()
        elif choice == "3":
            _manage_list_menu("blocked", "Blocklist", "🚫")
        elif choice == "4":
            _manage_list_menu("whitelist", "Whitelist", "✅")
        else:
            print("⚠️  Opción no válida.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gmail Bulk Trash — by Hugo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 gmail_bulk_trash.py --list-senders
  python3 gmail_bulk_trash.py --add-sender spam@example.com
  python3 gmail_bulk_trash.py --add-sender correo1@x.com correo2@y.com
  python3 gmail_bulk_trash.py --remove-sender spam@example.com
  python3 gmail_bulk_trash.py --add-whitelist boss@work.com
  python3 gmail_bulk_trash.py --remove-whitelist boss@work.com
  python3 gmail_bulk_trash.py --dry-run
  python3 gmail_bulk_trash.py --query "from:linkedin.com" --dry-run
  python3 gmail_bulk_trash.py --before 2024-01-01 --dry-run
  python3 gmail_bulk_trash.py --after 2023-01-01 --before 2023-12-31 --dry-run
  python3 gmail_bulk_trash.py --top-senders
  python3 gmail_bulk_trash.py --top-senders --top-limit 5 --days 30
        """
    )

    # Comandos de gestión
    parser.add_argument("--add-sender",       nargs="+", metavar="EMAIL", help="Añadir remitente(s) al blocklist")
    parser.add_argument("--remove-sender",    nargs="+", metavar="EMAIL", help="Eliminar remitente(s) del blocklist")
    parser.add_argument("--add-whitelist",    nargs="+", metavar="EMAIL", help="Añadir remitente(s) a la whitelist")
    parser.add_argument("--remove-whitelist", nargs="+", metavar="EMAIL", help="Eliminar remitente(s) de la whitelist")
    parser.add_argument("--list-senders",     action="store_true",       help="Mostrar blocklist y whitelist")

    # Filtros de búsqueda
    parser.add_argument("--query",    metavar="QUERY",  help="Query Gmail personalizada (sobreescribe la por defecto)")
    parser.add_argument("--before",   metavar="FECHA",  help="Borrar emails ANTES de esta fecha (formato: YYYY-MM-DD)")
    parser.add_argument("--after",    metavar="FECHA",  help="Borrar emails DESPUÉS de esta fecha (formato: YYYY-MM-DD)")

    # Opciones de ejecución
    parser.add_argument("--dry-run",          action="store_true",       help="Simular sin borrar nada")
    parser.add_argument("--top-senders",      action="store_true",       help="Analizar remitentes más frecuentes (modo interactivo)")
    parser.add_argument("--top-limit",        type=int, default=20,      help="Número de top senders a mostrar (default: 20)")
    parser.add_argument("--days",             type=int, default=0,       help="Ventana de tiempo en días para el análisis (default: 90 con --top-senders)")
    parser.add_argument("--menu",             action="store_true",       help="Mostrar menú interactivo")

    args, remaining = parser.parse_known_args()

    if args.menu or len(sys.argv) == 1:
        show_menu()
        return

    print("\n═══════════════════════════════════")
    print("   Gmail Bulk Trash — by Hugo")
    print("═══════════════════════════════════")

    # Manejar comandos de gestión (no necesitan autenticación)
    if manage_senders(args):
        return

    # ── Modo Top Senders ────────────────────────────────────────────────
    if args.top_senders:
        _run_top_senders_menu(args)
        return

    try:
        service = get_service()
        senders = load_senders()

        # Construir query base
        base = args.query or QUERY

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

if __name__ == "__main__":
    main()
