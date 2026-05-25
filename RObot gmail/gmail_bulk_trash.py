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
import subprocess, sys

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q", "--break-system-packages"])

for pkg in [
    "google-auth",
    "google-auth-oauthlib",
    "google-api-python-client",
]:
    try:
        __import__(pkg.replace("-", "_").split("-")[0])
    except ImportError:
        print(f"📦 Instalando {pkg}...")
        install(pkg)

# ── Imports ───────────────────────────────────────────────────────────────────
import argparse
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
    import json
    return json.loads(SENDERS_FILE.read_text())

def save_senders(data: dict) -> None:
    import json
    SENDERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

# ── Autenticación ─────────────────────────────────────────────────────────────

def get_service() -> any:
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

def get_all_ids(service: any, query: str) -> list[str]:
    ids = []
    page_token = None

    print(f"\n🔍 Buscando: {query}\n")

    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token

        resp = service.users().messages().list(**kwargs).execute()
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

# ── Borrado en batch ──────────────────────────────────────────────────────────

def batch_trash(service: any, ids: list[str]) -> None:
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
    print("   Vacíala en Gmail cuando quieras para liberar espacio definitivamente.\n")

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
        base = args.query if hasattr(args, 'query') and args.query else QUERY

        # Añadir filtros de fecha
        if hasattr(args, 'before') and args.before:
            base = f"({base}) before:{args.before.replace('-', '/')}"
        if hasattr(args, 'after') and args.after:
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
