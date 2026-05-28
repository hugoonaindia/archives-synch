#!/usr/bin/env python3
"""
gmail_gui.py — GUI nativa Tkinter para Gmail Bulk Trash
Compilar: pyinstaller --onedir --windowed --name "Gmail Bulk Trash" gmail_gui.py

Requiere: credentials.json en el mismo directorio (o en ~/Library/Application Support/GmailBulkTrash/)
"""

import sys, os, json, time, threading, re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── Paths ────────────────────────────────────────────────────────────────

if getattr(sys, 'frozen', False):
    DATA_DIR = Path.home() / "Library" / "Application Support" / "GmailBulkTrash"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    DATA_DIR = Path(__file__).resolve().parent

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
BATCH_SIZE = 1000

CREDS_FILE = DATA_DIR / "credentials.json"
TOKEN_FILE = DATA_DIR / "token.json"
SENDERS_FILE = DATA_DIR / "senders.json"


# ── Core Gmail functions (GUI-adapted with progress callbacks) ──────────

def api_call_with_retry(fn, desc="API call"):
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except HttpError as e:
            if e.resp.status == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(INITIAL_BACKOFF * (2 ** attempt))
            else:
                raise

def get_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json no encontrado en:\n{CREDS_FILE}\n\n"
                    "Descárgalo desde Google Cloud Console (API Gmail → Credenciales → OAuth 2.0)"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def load_senders():
    if not SENDERS_FILE.exists():
        return {"blocked": [], "whitelist": []}
    try:
        data = json.loads(SENDERS_FILE.read_text())
        if "blocked" not in data or "whitelist" not in data:
            return {"blocked": [], "whitelist": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"blocked": [], "whitelist": []}

def save_senders(data):
    SENDERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def parse_email(from_header):
    m = re.search(r'<([^>]+)>', from_header)
    return m.group(1).strip().lower() if m else from_header.strip().lower()

def build_query(base_query, senders):
    parts = []
    if base_query:
        parts.append(f"({base_query})")
    if senders["blocked"]:
        parts.append("(" + " OR ".join(f"from:{s}" for s in senders["blocked"]) + ")")
    if not parts:
        return ""
    query = " OR ".join(parts)
    for p in senders["whitelist"]:
        query = f"({query}) -from:{p}"
    return query

def get_all_ids(service, query, on_progress=None):
    ids, page_token = [], None
    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = api_call_with_retry(lambda kw=kwargs: service.users().messages().list(**kw).execute(), "messages.list")
        msgs = resp.get("messages", [])
        ids.extend(m["id"] for m in msgs)
        page_token = resp.get("nextPageToken")
        if on_progress:
            on_progress(len(ids))
        if not page_token:
            break
    return ids

def get_top_senders(service, ids, top_n=20, on_progress=None):
    counter, sender_ids = Counter(), {}
    total = len(ids)
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
        if on_progress:
            on_progress(i + 1, total, len(counter))
    top = counter.most_common(top_n)
    top_emails = {e for e, _ in top}
    sender_ids = {k: v for k, v in sender_ids.items() if k in top_emails}
    return top, sender_ids

def batch_trash(service, ids, on_progress=None):
    total = len(ids)
    trashed, failed = 0, 0
    start = time.time()
    for i in range(0, total, BATCH_SIZE):
        batch = ids[i:i + BATCH_SIZE]
        try:
            api_call_with_retry(
                lambda b=batch: service.users().messages().batchModify(
                    userId="me", body={"ids": b, "addLabelIds": ["TRASH"], "removeLabelIds": ["INBOX"]}
                ).execute(),
                f"batchModify ({i+1}-{min(i+BATCH_SIZE, total)})"
            )
            trashed += len(batch)
        except HttpError:
            failed += len(batch)
        if on_progress:
            on_progress(trashed, total, failed, time.time() - start)
    return trashed, failed


# ── GUI ──────────────────────────────────────────────────────────────────

class GmailApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gmail Bulk Trash")
        self.root.geometry("820x640")
        self.root.minsize(700, 500)

        self.service = None
        self.senders = load_senders()
        self.top_senders_data = []
        self.sender_ids_map = {}
        self.last_search_ids = []
        self.last_query = ""

        self._build_ui()
        self._update_status("Inicia sesión con el botón Conectar.")

    # ── UI Builder ──────────────────────────────────────────────────────

    def _build_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=8, pady=6)

        self.btn_connect = ttk.Button(toolbar, text="\U0001f510  Conectar Gmail", command=self._connect)
        self.btn_connect.pack(side=tk.LEFT, padx=2)

        self.lbl_auth_status = ttk.Label(toolbar, text="(desconectado)", foreground="gray")
        self.lbl_auth_status.pack(side=tk.LEFT, padx=10)

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8)

        self.tab_senders = ttk.Frame(self.notebook)
        self.tab_trash = ttk.Frame(self.notebook)
        self.tab_lists = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_senders, text="Top Senders")
        self.notebook.add(self.tab_trash, text="Bulk Trash")
        self.notebook.add(self.tab_lists, text="Listas")

        self._build_senders_tab()
        self._build_trash_tab()
        self._build_lists_tab()

        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill=tk.X, padx=8)

        # Log output
        self.log = scrolledtext.ScrolledText(self.root, font=("Menlo", 10), height=6, wrap=tk.WORD, padx=6, pady=6)
        self.log.pack(fill=tk.BOTH, padx=8, pady=(0, 4))
        self.log.insert(tk.END, "Bienvenido. Conecta tu cuenta de Gmail para empezar.\n")
        self.log.config(state=tk.DISABLED)

        # Status bar
        self.status_var = tk.StringVar(value="Listo.")
        bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _log(self, msg):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def _update_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _ensure_auth(self):
        if not self.service:
            self._connect()
        return self.service is not None

    # ── Toolbar: Connect ────────────────────────────────────────────────

    def _connect(self):
        self.btn_connect.config(state=tk.DISABLED, text="Conectando...")
        self._update_status("Autenticando con Google...")
        self.lbl_auth_status.config(text="(autenticando...)")
        threading.Thread(target=self._do_connect, daemon=True).start()

    def _do_connect(self):
        try:
            self.service = get_service()
            profile = self.service.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress", "desconocido")
            self.root.after(0, lambda: self._on_connected(email))
        except Exception as e:
            self.root.after(0, lambda: self._on_connect_error(str(e)))

    def _on_connected(self, email):
        self.btn_connect.config(state=tk.NORMAL, text=f"\U0001f510  Conectado ({email})")
        self.lbl_auth_status.config(text="\u2705 Conectado", foreground="green")
        self._update_status(f"Conectado como {email}")
        self._log(f"Conectado a Gmail: {email}")

    def _on_connect_error(self, err):
        self.btn_connect.config(state=tk.NORMAL, text="\U0001f510  Conectar Gmail")
        self.lbl_auth_status.config(text="\u274c Error", foreground="red")
        self._update_status("Error de conexión")
        messagebox.showerror("Error de conexión", err)

    # ── Tab 1: Top Senders ──────────────────────────────────────────────

    def _build_senders_tab(self):
        top = ttk.Frame(self.tab_senders)
        top.pack(fill=tk.X, pady=6)

        ttk.Label(top, text="Días:").pack(side=tk.LEFT, padx=2)
        self.senders_days = ttk.Spinbox(top, from_=1, to=365, width=5)
        self.senders_days.set(90)
        self.senders_days.pack(side=tk.LEFT, padx=2)

        ttk.Label(top, text="Top N:").pack(side=tk.LEFT, padx=2)
        self.senders_limit = ttk.Spinbox(top, from_=5, to=100, width=5)
        self.senders_limit.set(20)
        self.senders_limit.pack(side=tk.LEFT, padx=2)

        ttk.Label(top, text="Filtrar:").pack(side=tk.LEFT, padx=(10, 2))
        self.senders_filter = ttk.Entry(top, width=25)
        self.senders_filter.pack(side=tk.LEFT, padx=2)
        self.senders_filter.bind("<KeyRelease>", self._filter_senders_list)

        self.btn_scan = ttk.Button(top, text="\U0001f50d  Escanear", command=self._scan_senders)
        self.btn_scan.pack(side=tk.LEFT, padx=(10, 2))

        # Treeview
        cols = ("sender", "count", "status")
        self.senders_tree = ttk.Treeview(self.tab_senders, columns=cols, show="headings", selectmode="browse")
        self.senders_tree.heading("sender", text="Remitente")
        self.senders_tree.heading("count", text="Correos")
        self.senders_tree.heading("status", text="Estado")
        self.senders_tree.column("sender", width=350)
        self.senders_tree.column("count", width=80, anchor=tk.CENTER)
        self.senders_tree.column("status", width=120, anchor=tk.CENTER)

        scroll = ttk.Scrollbar(self.tab_senders, orient=tk.VERTICAL, command=self.senders_tree.yview)
        self.senders_tree.configure(yscrollcommand=scroll.set)

        self.senders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Action bar
        actions = ttk.Frame(self.tab_senders)
        actions.pack(fill=tk.X, pady=6)

        self.btn_trash = ttk.Button(actions, text="\U0001f5d1  Trash seleccionado", command=self._trash_selected_sender, state=tk.DISABLED)
        self.btn_trash.pack(side=tk.LEFT, padx=2)

        self.btn_block = ttk.Button(actions, text="\U0001f6ab  Bloquear seleccionado", command=self._block_selected_sender, state=tk.DISABLED)
        self.btn_block.pack(side=tk.LEFT, padx=2)

        self.btn_add_all = ttk.Button(actions, text="\U0001f4e5  Bloquear TODOS visibles", command=self._block_all_visible, state=tk.DISABLED)
        self.btn_add_all.pack(side=tk.LEFT, padx=2)

        self.senders_tree.bind("<<TreeviewSelect>>", self._on_sender_select)

    def _on_sender_select(self, event=None):
        sel = self.senders_tree.selection()
        state = tk.NORMAL if sel else tk.DISABLED
        self.btn_trash.config(state=state)
        self.btn_block.config(state=state)

    def _filter_senders_list(self, event=None):
        q = self.senders_filter.get().strip().lower()
        for item in self.senders_tree.get_children():
            vals = self.senders_tree.item(item, "values")
            s = vals[0].lower()
            self.senders_tree.reattach(item, "", "end" if q in s else "")
            self.senders_tree.item(item, open=False)

    def _scan_senders(self):
        if not self._ensure_auth():
            return
        self.senders = load_senders()
        days = int(self.senders_days.get())
        limit = int(self.senders_limit.get())
        cutoff = datetime.now() - timedelta(days=days)

        self.btn_scan.config(state=tk.DISABLED, text="Escaneando...")
        for c in self.senders_tree.get_children():
            self.senders_tree.delete(c)
        self._update_status("Escaneando mensajes...")
        self.progress["value"] = 0

        threading.Thread(target=self._do_scan, args=(cutoff, limit), daemon=True).start()

    def _do_scan(self, cutoff, limit):
        try:
            self._log(f"Escaneando mensajes anteriores a {cutoff.strftime('%Y/%m/%d')}...")
            query = f"before:{cutoff.strftime('%Y/%m/%d')}"

            ids = get_all_ids(self.service, query, on_progress=lambda c: self.root.after(0, lambda cnt=c: self._update_status(f"Buscando: {cnt} mensajes encontrados...")))
            if not ids:
                self.root.after(0, lambda: self._on_scan_done([], {}, 0))
                return

            self._log(f"{len(ids)} mensajes encontrados. Analizando remitentes...")
            top, sender_ids = get_top_senders(self.service, ids, limit, on_progress=lambda i, t, u: self.root.after(0, lambda i=i, t=t, u=u: self._on_scan_progress(i, t, u)))

            self.root.after(0, lambda: self._on_scan_done(top, sender_ids, len(ids)))
        except Exception as e:
            self.root.after(0, lambda: self._on_scan_error(str(e)))

    def _on_scan_progress(self, i, total, unique):
        pct = round(i / total * 100)
        self.progress["value"] = pct
        self._update_status(f"Analizando {i}/{total} ({unique} remitentes únicos)")

    def _on_scan_done(self, top, sender_ids, total_msgs):
        self.btn_scan.config(state=tk.NORMAL, text="\U0001f50d  Escanear")
        self.progress["value"] = 100
        self.top_senders_data = top
        self.sender_ids_map = sender_ids
        self.senders = load_senders()

        for email, count in top:
            status = ""
            if email in self.senders.get("blocked", []):
                status = "\U0001f6ab Bloqueado"
            elif email in self.senders.get("whitelist", []):
                status = "\u2705 Whitelist"
            self.senders_tree.insert("", tk.END, values=(email, f"{count:,}", status))

        self.btn_add_all.config(state=tk.NORMAL if top else tk.DISABLED)
        self._log(f"Análisis completo: {len(top)} remitentes de {total_msgs} mensajes.")
        self._update_status(f"{len(top)} remitentes encontrados.")

    def _on_scan_error(self, err):
        self.btn_scan.config(state=tk.NORMAL, text="\U0001f50d  Escanear")
        self.progress["value"] = 0
        self._update_status("Error en escaneo")
        messagebox.showerror("Error", err)

    def _get_selected_email(self):
        sel = self.senders_tree.selection()
        if not sel:
            return None
        return self.senders_tree.item(sel[0], "values")[0]

    def _trash_selected_sender(self):
        email = self._get_selected_email()
        if not email:
            return
        ids = self.sender_ids_map.get(email, [])
        if not ids:
            messagebox.showwarning("Sin datos", f"No hay IDs de correos para {email}. Vuelve a escanear.")
            return
        ok = messagebox.askyesno("Confirmar", f"\u00bfMover {len(ids)} correos de {email} a la papelera?")
        if not ok:
            return
        self._update_status(f"Eliminando correos de {email}...")
        threading.Thread(target=self._do_trash, args=(email, ids), daemon=True).start()

    def _do_trash(self, email, ids):
        try:
            def prog(t, total, failed, elapsed):
                pct = round(t / total * 100)
                self.root.after(0, lambda p=pct: self.progress.__setitem__("value", p))
                self.root.after(0, lambda: self._update_status(f"Eliminando {t}/{total} ({failed} fallos)..."))
            trashed, failed = batch_trash(self.service, ids, on_progress=prog)
            self.root.after(0, lambda: self._on_trash_done(email, trashed, failed))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _on_trash_done(self, email, trashed, failed):
        self.progress["value"] = 100
        msg = f"{trashed} correos de {email} movidos a la papelera."
        if failed:
            msg += f" ({failed} fallos)"
        self._log(f"\u2705 {msg}")
        self._update_status(msg)
        self._refresh_sender_status()

    def _block_selected_sender(self):
        email = self._get_selected_email()
        if not email:
            return
        self.senders = load_senders()
        if email in self.senders["blocked"]:
            messagebox.showinfo("Ya bloqueado", f"{email} ya está en la blocklist.")
            return
        self.senders["blocked"].append(email)
        save_senders(self.senders)
        self._log(f"\u2705 {email} añadido a blocklist.")
        self._refresh_sender_status()

    def _block_all_visible(self):
        self.senders = load_senders()
        added = 0
        for item in self.senders_tree.get_children():
            vals = self.senders_tree.item(item, "values")
            email = vals[0]
            if email not in self.senders["blocked"] and vals[2] != "\u2705 Whitelist":
                self.senders["blocked"].append(email)
                added += 1
        save_senders(self.senders)
        self._log(f"\u2705 {added} remitentes añadidos a blocklist.")
        self._refresh_sender_status()

    def _refresh_sender_status(self):
        self.senders = load_senders()
        for item in self.senders_tree.get_children():
            vals = list(self.senders_tree.item(item, "values"))
            email = vals[0]
            if email in self.senders.get("blocked", []):
                vals[2] = "\U0001f6ab Bloqueado"
            elif email in self.senders.get("whitelist", []):
                vals[2] = "\u2705 Whitelist"
            else:
                vals[2] = ""
            self.senders_tree.item(item, values=vals)

    # ── Tab 2: Bulk Trash ───────────────────────────────────────────────

    def _build_trash_tab(self):
        f = ttk.LabelFrame(self.tab_trash, text="Filtros", padding=8)
        f.pack(fill=tk.X, pady=6)

        fields = [("Remitente (from:)", "from"), ("Asunto (subject:)", "subject"),
                  ("Palabra en cuerpo", "body"), ("Antes de (YYYY-MM-DD)", "before"),
                  ("Después de (YYYY-MM-DD)", "after"), ("Etiqueta (label:)", "label")]
        self.trash_entries = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(f, text=label).grid(row=i // 2, column=(i % 2) * 2, sticky=tk.W, padx=(0, 4), pady=2)
            e = ttk.Entry(f, width=30)
            e.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky=tk.W, padx=(0, 20), pady=2)
            self.trash_entries[key] = e

        # Buttons
        bf = ttk.Frame(self.tab_trash)
        bf.pack(fill=tk.X, pady=6)

        self.btn_search = ttk.Button(bf, text="\U0001f50d  Buscar", command=self._trash_search, state=tk.DISABLED)
        self.btn_search.pack(side=tk.LEFT, padx=2)

        self.btn_dry = ttk.Button(bf, text="\U0001f6a7  Dry Run", command=self._trash_dryrun, state=tk.DISABLED)
        self.btn_dry.pack(side=tk.LEFT, padx=2)

        self.btn_trash_all = ttk.Button(bf, text="\U0001f5d1  Trash All", command=self._trash_execute, state=tk.DISABLED)
        self.btn_trash_all.pack(side=tk.LEFT, padx=2)

        # Results area
        self.trash_result = scrolledtext.ScrolledText(self.tab_trash, font=("Menlo", 10), height=8, state=tk.DISABLED)
        self.trash_result.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

    def _build_trash_query(self):
        parts = []
        v = self.trash_entries
        if v["from"].get().strip():
            parts.append(f"from:{v['from'].get().strip()}")
        if v["subject"].get().strip():
            parts.append(f"subject:{v['subject'].get().strip()}")
        if v["label"].get().strip():
            parts.append(f"label:{v['label'].get().strip()}")
        if v["body"].get().strip():
            parts.append(v["body"].get().strip())
        base = " ".join(parts)
        if v["before"].get().strip():
            base = f"({base}) before:{v['before'].get().strip().replace('-', '/')}" if base else f"before:{v['before'].get().strip().replace('-', '/')}"
        if v["after"].get().strip():
            base = f"({base}) after:{v['after'].get().strip().replace('-', '/')}" if base else f"after:{v['after'].get().strip().replace('-', '/')}"
        self.senders = load_senders()
        return build_query(base, self.senders)

    def _trash_search(self):
        if not self._ensure_auth():
            return
        query = self._build_trash_query()
        if not query:
            messagebox.showwarning("Sin filtros", "Especifica al menos un filtro.")
            return
        self.last_query = query
        self.btn_search.config(state=tk.DISABLED, text="Buscando...")
        self.log.config(state=tk.NORMAL)
        self.trash_result.config(state=tk.NORMAL)
        self.trash_result.delete(1.0, tk.END)
        self.trash_result.insert(tk.END, "Buscando...")
        self.trash_result.config(state=tk.DISABLED)
        self.log.config(state=tk.DISABLED)
        threading.Thread(target=self._do_trash_search, args=(query,), daemon=True).start()

    def _do_trash_search(self, query):
        try:
            self._log(f"Query: {query}")
            ids = get_all_ids(self.service, query, on_progress=lambda c: self.root.after(0, lambda cnt=c: self._update_status(f"Buscando: {cnt} mensajes...")))
            self.last_search_ids = ids
            self.root.after(0, lambda: self._on_trash_search_done(ids))
        except Exception as e:
            self.root.after(0, lambda: self._on_trash_search_error(str(e)))

    def _on_trash_search_done(self, ids):
        self.btn_search.config(state=tk.NORMAL, text="\U0001f50d  Buscar")
        self.btn_dry.config(state=tk.NORMAL)
        self.btn_trash_all.config(state=tk.NORMAL if ids else tk.DISABLED)
        self.progress["value"] = 100 if not ids else 0
        self.trash_result.config(state=tk.NORMAL)
        self.trash_result.delete(1.0, tk.END)
        self.trash_result.insert(tk.END, f"{len(ids)} mensajes encontrados con esa query.\n")
        if ids:
            self.trash_result.insert(tk.END, "Usa 'Dry Run' para simular o 'Trash All' para eliminar.")
        self.trash_result.config(state=tk.DISABLED)
        self._update_status(f"{len(ids)} mensajes encontrados.")

    def _on_trash_search_error(self, err):
        self.btn_search.config(state=tk.NORMAL, text="\U0001f50d  Buscar")
        messagebox.showerror("Error", err)

    def _trash_dryrun(self):
        if not self.last_search_ids:
            return
        messagebox.showinfo("Dry Run", f"Se moverían {len(self.last_search_ids)} mensajes a la papelera.")

    def _trash_execute(self):
        if not self.last_search_ids:
            return
        ok = messagebox.askyesno("Confirmar", f"\u00bfMover {len(self.last_search_ids)} mensajes a la papelera?")
        if not ok:
            return
        self.btn_trash_all.config(state=tk.DISABLED, text="Eliminando...")
        threading.Thread(target=self._do_trash_execute, daemon=True).start()

    def _do_trash_execute(self):
        ids = self.last_search_ids
        try:
            def prog(t, total, failed, elapsed):
                pct = round(t / total * 100)
                self.root.after(0, lambda p=pct: self.progress.__setattr__("value", p))
                self.root.after(0, lambda: self._update_status(f"Eliminando {t}/{total}..."))
            trashed, failed = batch_trash(self.service, ids, on_progress=prog)
            self.root.after(0, lambda: self._on_trash_execute_done(trashed, failed))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _on_trash_execute_done(self, trashed, failed):
        self.btn_trash_all.config(state=tk.NORMAL, text="\U0001f5d1  Trash All")
        self.progress["value"] = 100
        msg = f"{trashed} correos movidos a la papelera."
        if failed:
            msg += f" ({failed} fallos)"
        self.trash_result.config(state=tk.NORMAL)
        self.trash_result.insert(tk.END, f"\n{msg}\n")
        self.trash_result.config(state=tk.DISABLED)
        self._log(f"\u2705 {msg}")
        self._update_status(msg)
        self.last_search_ids = []
        self.btn_trash_all.config(state=tk.DISABLED)
        self.btn_dry.config(state=tk.DISABLED)

    # ── Tab 3: Listas ───────────────────────────────────────────────────

    def _build_lists_tab(self):
        pf = ttk.PanedWindow(self.tab_lists, orient=tk.HORIZONTAL)
        pf.pack(fill=tk.BOTH, expand=True, pady=6)

        # Blocklist
        bl = ttk.LabelFrame(pf, text="\U0001f6ab Blocklist", padding=6)
        pf.add(bl, weight=1)
        self.bl_listbox = tk.Listbox(bl, font=("Menlo", 10))
        scroll_bl = ttk.Scrollbar(bl, orient=tk.VERTICAL, command=self.bl_listbox.yview)
        self.bl_listbox.configure(yscrollcommand=scroll_bl.set)
        self.bl_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_bl.pack(side=tk.RIGHT, fill=tk.Y)
        bl_btn = ttk.Frame(bl)
        bl_btn.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(bl_btn, text="Añadir", command=self._bl_add).pack(side=tk.LEFT, padx=2)
        ttk.Button(bl_btn, text="Eliminar sel.", command=self._bl_remove).pack(side=tk.LEFT, padx=2)

        # Whitelist
        wl = ttk.LabelFrame(pf, text="\u2705 Whitelist", padding=6)
        pf.add(wl, weight=1)
        self.wl_listbox = tk.Listbox(wl, font=("Menlo", 10))
        scroll_wl = ttk.Scrollbar(wl, orient=tk.VERTICAL, command=self.wl_listbox.yview)
        self.wl_listbox.configure(yscrollcommand=scroll_wl.set)
        self.wl_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_wl.pack(side=tk.RIGHT, fill=tk.Y)
        wl_btn = ttk.Frame(wl)
        wl_btn.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(wl_btn, text="Añadir", command=self._wl_add).pack(side=tk.LEFT, padx=2)
        ttk.Button(wl_btn, text="Eliminar sel.", command=self._wl_remove).pack(side=tk.LEFT, padx=2)

        self._refresh_lists()

    def _refresh_lists(self):
        self.senders = load_senders()
        self.bl_listbox.delete(0, tk.END)
        for s in self.senders.get("blocked", []):
            self.bl_listbox.insert(tk.END, s)
        self.wl_listbox.delete(0, tk.END)
        for s in self.senders.get("whitelist", []):
            self.wl_listbox.insert(tk.END, s)

    def _bl_add(self):
        email = simpledialog.askstring("Añadir a blocklist", "Email:")
        if email:
            self.senders = load_senders()
            email = email.strip().lower()
            if email in self.senders["blocked"]:
                messagebox.showinfo("Ya existe", f"{email} ya está en la blocklist.")
                return
            self.senders["blocked"].append(email)
            save_senders(self.senders)
            self._log(f"\U0001f6ab {email} añadido a blocklist.")
            self._refresh_lists()
            self._refresh_sender_status()

    def _bl_remove(self):
        sel = self.bl_listbox.curselection()
        if not sel:
            return
        email = self.bl_listbox.get(sel[0])
        self.senders = load_senders()
        if email in self.senders["blocked"]:
            self.senders["blocked"].remove(email)
            save_senders(self.senders)
            self._log(f"Removido de blocklist: {email}")
            self._refresh_lists()
            self._refresh_sender_status()

    def _wl_add(self):
        email = simpledialog.askstring("Añadir a whitelist", "Email:")
        if email:
            self.senders = load_senders()
            email = email.strip().lower()
            if email in self.senders["whitelist"]:
                messagebox.showinfo("Ya existe", f"{email} ya está en la whitelist.")
                return
            self.senders["whitelist"].append(email)
            save_senders(self.senders)
            self._log(f"\u2705 {email} añadido a whitelist.")
            self._refresh_lists()
            self._refresh_sender_status()

    def _wl_remove(self):
        sel = self.wl_listbox.curselection()
        if not sel:
            return
        email = self.wl_listbox.get(sel[0])
        self.senders = load_senders()
        if email in self.senders["whitelist"]:
            self.senders["whitelist"].remove(email)
            save_senders(self.senders)
            self._log(f"Removido de whitelist: {email}")
            self._refresh_lists()
            self._refresh_sender_status()

    # ── Run ─────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        from tkinter import simpledialog
        GmailApp().run()
    except KeyboardInterrupt:
        pass
