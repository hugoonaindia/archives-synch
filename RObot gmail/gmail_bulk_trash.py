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
    print("\n═══════════════════════════════════")
    print("   Gmail Bulk Trash — by Hugo")
    print("═══════════════════════════════════")

    try:
        service = get_service()
        ids     = get_all_ids(service, QUERY)

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
