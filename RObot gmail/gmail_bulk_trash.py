#!/usr/bin/env python3
"""
gmail_bulk_trash.py
-------------------
Instala dependencias y mueve a la papelera TODOS los correos
que coincidan con el filtro, usando batchModify (1000 por llamada).

Uso:
    python gmail_bulk_trash.py
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

def get_service():
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

def get_all_ids(service, query: str) -> list[str]:
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

def manage_senders(args) -> bool:
    """Gestiona blocklist y whitelist. Devuelve True si manejó un comando de gestión."""
    data = load_senders()

    if hasattr(args, 'add_sender') and args.add_sender:
        for s in args.add_sender:
            s = s.strip().lower()
            if s not in data["blocked"]:
                data["blocked"].append(s)
                print(f"✅ Añadido a blocklist: {s}")
            else:
                print(f"⚠️  Ya estaba en blocklist: {s}")
        save_senders(data)
        return True

    if hasattr(args, 'remove_sender') and args.remove_sender:
        for s in args.remove_sender:
            s = s.strip().lower()
            if s in data["blocked"]:
                data["blocked"].remove(s)
                print(f"✅ Eliminado de blocklist: {s}")
            else:
                print(f"⚠️  No estaba en blocklist: {s}")
        save_senders(data)
        return True

    if hasattr(args, 'add_whitelist') and args.add_whitelist:
        for s in args.add_whitelist:
            s = s.strip().lower()
            if s not in data["whitelist"]:
                data["whitelist"].append(s)
                print(f"✅ Añadido a whitelist: {s}")
            else:
                print(f"⚠️  Ya estaba en whitelist: {s}")
        save_senders(data)
        return True

    if hasattr(args, 'remove_whitelist') and args.remove_whitelist:
        for s in args.remove_whitelist:
            s = s.strip().lower()
            if s in data["whitelist"]:
                data["whitelist"].remove(s)
                print(f"✅ Eliminado de whitelist: {s}")
            else:
                print(f"⚠️  No estaba en whitelist: {s}")
        save_senders(data)
        return True

    if hasattr(args, 'list_senders') and args.list_senders:
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

def batch_trash(service, ids: list[str]) -> None:
    total   = len(ids)
    trashed = 0

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
        pct = round(trashed / total * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  [{bar}] {pct}%  ({trashed}/{total})", end="\r")

    print(f"\n\n✅ {trashed} correos movidos a la papelera.")
    print("   Vacíala en Gmail cuando quieras para liberar espacio definitivamente.")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
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
        """
    )

    # Comandos de gestión
    parser.add_argument("--add-sender",       nargs="+", metavar="EMAIL", help="Añadir remitente(s) al blocklist")
    parser.add_argument("--remove-sender",    nargs="+", metavar="EMAIL", help="Eliminar remitente(s) del blocklist")
    parser.add_argument("--add-whitelist",    nargs="+", metavar="EMAIL", help="Añadir remitente(s) a la whitelist")
    parser.add_argument("--remove-whitelist", nargs="+", metavar="EMAIL", help="Eliminar remitente(s) de la whitelist")
    parser.add_argument("--list-senders",     action="store_true",       help="Mostrar blocklist y whitelist")

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
        query = build_query(QUERY, senders)

        if not query:
            print("⚠️  No hay query ni remitentes bloqueados.")
            print("   Usa --query 'tu filtro' o --add-sender email@ejemplo.com")
            sys.exit(1)

        ids = get_all_ids(service, query)

        if not ids:
            print("✅ No hay mensajes que coincidan con el filtro.")
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
