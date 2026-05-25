# Top Senders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adds `--top-senders` interactive mode to analyze and bulk-act on frequent senders

**Architecture:** New functions `parse_email`, `get_top_senders`, `interactive_sender_menu` added to existing `gmail_bulk_trash.py`. `get_top_senders` uses `messages.get(format='metadata', metadataHeaders=['From'])` per message to extract sender, counts frequencies with Counter, returns sorted top N plus per-sender ID map. Interactive menu loops on top senders, allows trash/dry-run/blocklist per sender. New CLI flags `--top-senders`, `--top-limit`, `--days`.

**Tech Stack:** Python 3.10+, collections.Counter, re, argparse, google-api-python-client, unittest.mock

**Files:**
- Modify: `gmail_bulk_trash.py`
- Modify: `tests/test_senders.py`

---

### Task 1: `parse_email()` helper + tests

**Files:**
- Modify: `gmail_bulk_trash.py` (after `save_senders`, before `get_service`)
- Modify: `tests/test_senders.py`

- [ ] **Step 1: Write failing tests**

Add after the last test in `tests/test_senders.py`:

```python
def test_parse_email_simple():
    assert gbt.parse_email("user@example.com") == "user@example.com"


def test_parse_email_with_name():
    assert gbt.parse_email("User <user@example.com>") == "user@example.com"


def test_parse_email_multi_angle():
    assert gbt.parse_email("<a@x.com> <b@x.com>") == "a@x.com"


def test_parse_email_empty():
    assert gbt.parse_email("") == ""


def test_parse_email_whitespace():
    assert gbt.parse_email("  User <user@example.com>  ") == "user@example.com"
```

Run: `python -m pytest tests/test_senders.py::test_parse_email_simple tests/test_senders.py::test_parse_email_with_name tests/test_senders.py::test_parse_email_multi_angle tests/test_senders.py::test_parse_email_empty tests/test_senders.py::test_parse_email_whitespace -v`

Expected: 5 FAILED (AttributeError: module has no attribute 'parse_email')

- [ ] **Step 2: Write minimal implementation**

Add after `save_senders()` in `gmail_bulk_trash.py`:

```python
import re

def parse_email(from_header: str) -> str:
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).strip().lower()
    return from_header.strip().lower()
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_senders.py::test_parse_email_simple tests/test_senders.py::test_parse_email_with_name tests/test_senders.py::test_parse_email_multi_angle tests/test_senders.py::test_parse_email_empty tests/test_senders.py::test_parse_email_whitespace -v`

Expected: 5 PASSED

- [ ] **Step 4: Commit**

```bash
git add gmail_bulk_trash.py tests/test_senders.py
git commit -m "feat: add parse_email helper for sender extraction"
```

---

### Task 2: `get_top_senders()` function + tests

**Files:**
- Modify: `gmail_bulk_trash.py` (before `batch_trash`)
- Modify: `tests/test_senders.py`

- [ ] **Step 1: Write failing test for get_top_senders with mock**

Add to `tests/test_senders.py`:

```python
def test_get_top_senders_returns_sorted():
    mock_service = MagicMock()
    # Mock messages.get chain
    def mock_get(**kwargs):
        result = MagicMock()
        sender_map = {
            "id1": "spam@ads.com",
            "id2": "spam@ads.com",
            "id3": "news@promo.com",
            "id4": "spam@ads.com",
            "id5": "news@promo.com",
        }
        def execute():
            return {
                "payload": {
                    "headers": [{"name": "From", "value": sender_map.get(kwargs["id"], "unknown@x.com")}]
                }
            }
        result.execute = execute
        return result

    mock_service.users().messages().get = mock_get

    ids = ["id1", "id2", "id3", "id4", "id5"]
    top, sender_ids = gbt.get_top_senders(mock_service, ids, top_n=10)

    assert len(top) == 2
    assert top[0] == ("spam@ads.com", 3)
    assert top[1] == ("news@promo.com", 2)
    assert sender_ids["spam@ads.com"] == ["id1", "id2", "id4"]
    assert sender_ids["news@promo.com"] == ["id3", "id5"]


def test_get_top_senders_empty():
    mock_service = MagicMock()
    top, sender_ids = gbt.get_top_senders(mock_service, [], top_n=10)
    assert top == []
    assert sender_ids == {}


def test_get_top_senders_top_n():
    mock_service = MagicMock()
    def mock_get(**kwargs):
        result = MagicMock()
        def execute():
            return {"payload": {"headers": [{"name": "From", "value": f"sender{kwargs['id']}@x.com"}]}}
        result.execute = execute
        return result
    mock_service.users().messages().get = mock_get

    ids = [f"id{i}" for i in range(50)]
    top, sender_ids = gbt.get_top_senders(mock_service, ids, top_n=3)
    assert len(top) <= 3
```

Run: `python -m pytest tests/test_senders.py::test_get_top_senders_returns_sorted tests/test_senders.py::test_get_top_senders_empty tests/test_senders.py::test_get_top_senders_top_n -v`

Expected: 3 FAILED

- [ ] **Step 2: Write minimal implementation**

Add before `batch_trash` in `gmail_bulk_trash.py`:

```python
from collections import Counter

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
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_senders.py::test_get_top_senders_returns_sorted tests/test_senders.py::test_get_top_senders_empty tests/test_senders.py::test_get_top_senders_top_n -v`

Expected: 3 PASSED

- [ ] **Step 4: Commit**

```bash
git add gmail_bulk_trash.py tests/test_senders.py
git commit -m "feat: add get_top_senders for frequency analysis"
```

---

### Task 3: `interactive_sender_menu()` function + tests

**Files:**
- Modify: `gmail_bulk_trash.py` (after `get_top_senders`, before `batch_trash`)
- Modify: `tests/test_senders.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_senders.py`:

```python
def test_interactive_menu_quit():
    from unittest.mock import patch
    top = [("spam@x.com", 10), ("news@y.com", 5)]
    sender_ids = {"spam@x.com": ["a", "b"], "news@y.com": ["c"]}
    mock_service = MagicMock()
    mock_senders = {"blocked": [], "whitelist": []}

    with patch("builtins.input", side_effect=["q"]):
        result = gbt.interactive_sender_menu(mock_service, top, sender_ids, mock_senders)

    assert result is False  # no changes


def test_interactive_menu_add_blocked():
    from unittest.mock import patch
    import tempfile, json
    from pathlib import Path

    top = [("spam@x.com", 10)]
    sender_ids = {"spam@x.com": ["a", "b"]}
    mock_service = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            with patch("builtins.input", side_effect=["1", "3", "q"]):
                result = gbt.interactive_sender_menu(mock_service, top, sender_ids, {"blocked": [], "whitelist": []})
            data = json.loads(fake_path.read_text())
            assert "spam@x.com" in data["blocked"]
            assert result is True


def test_interactive_menu_trash():
    from unittest.mock import patch, MagicMock
    top = [("spam@x.com", 2)]
    sender_ids = {"spam@x.com": ["id1", "id2"]}
    mock_service = MagicMock()

    with patch("builtins.input", side_effect=["1", "1", "q"]):
        gbt.interactive_sender_menu(mock_service, top, sender_ids, {"blocked": [], "whitelist": []})

    # Verify batchModify was called with correct IDs
    mock_service.users().messages().batchModify.assert_called_once()
    call_body = mock_service.users().messages().batchModify.call_args[1]["body"]
    assert call_body["ids"] == ["id1", "id2"]
    assert "TRASH" in call_body["addLabelIds"]
```

Run: `python -m pytest tests/test_senders.py::test_interactive_menu_quit tests/test_senders.py::test_interactive_menu_add_blocked tests/test_senders.py::test_interactive_menu_trash -v`

Expected: 3 FAILED

- [ ] **Step 2: Write minimal implementation**

Add before `batch_trash` in `gmail_bulk_trash.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_senders.py::test_interactive_menu_quit tests/test_senders.py::test_interactive_menu_add_blocked tests/test_senders.py::test_interactive_menu_trash -v`

Expected: 3 PASSED

- [ ] **Step 4: Commit**

```bash
git add gmail_bulk_trash.py tests/test_senders.py
git commit -m "feat: add interactive_sender_menu for top senders actions"
```

---

### Task 4: CLI flags + wiring in `main()`

**Files:**
- Modify: `gmail_bulk_trash.py`

- [ ] **Step 1: Add new CLI arguments**

In `main()`, add after the existing `--dry-run` argument:

```python
    parser.add_argument("--top-senders",  action="store_true",       help="Analizar remitentes más frecuentes (modo interactivo)")
    parser.add_argument("--top-limit",    type=int, default=20,      help="Número de top senders a mostrar (default: 20)")
    parser.add_argument("--days",         type=int, default=0,       help="Ventana de tiempo en días para el análisis (default: 90 con --top-senders)")
```

- [ ] **Step 2: Add import for datetime**

Add to the imports section:
```python
from datetime import datetime, timedelta
```

- [ ] **Step 3: Add `--top-senders` branch in `main()`**

Before the `try:` block in `main()`, add:

```python
    if args.top_senders:
        try:
            service = get_service()
            senders = load_senders()

            base = args.query or ""
            days = args.days if args.days > 0 else 90
            cutoff = datetime.now() - timedelta(days=days)
            date_query = f"before:{cutoff.strftime('%Y/%m/%d')}"

            query_parts = [p for p in [base, date_query] if p]
            query = " ".join(query_parts) if query_parts else ""

            # Add --before/--after if specified
            if args.before:
                query = f"({query}) before:{args.before.replace('-', '/')}" if query else f"before:{args.before.replace('-', '/')}"
            if args.after:
                query = f"({query}) after:{args.after.replace('-', '/')}" if query else f"after:{args.after.replace('-', '/')}"

            ids = get_all_ids(service, query)

            if not ids:
                print("✅ No hay mensajes en el rango especificado.")
                return

            top, sender_ids = get_top_senders(service, ids, args.top_limit)

            if not top:
                print("No se pudieron identificar remitentes.")
                return

            modified = interactive_sender_menu(service, top, sender_ids, senders)

            if modified:
                print("\n✅ Cambios guardados. Vuelve a ejecutar sin --top-senders para limpiar el resto.")
            else:
                print("\nSin cambios.")

        except HttpError as e:
            print(f"\n❌ Error de la API: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\nInterrumpido por el usuario.")
        return
```

- [ ] **Step 4: Verify flags via --help**

Run: `python gmail_bulk_trash.py --help`

Expected: Shows `--top-senders`, `--top-limit`, `--days` in the help output.

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/ -v`

Expected: ALL PASSED

- [ ] **Step 6: Commit**

```bash
git add gmail_bulk_trash.py
git commit -m "feat: add --top-senders, --top-limit, --days CLI flags"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`

Expected: ALL PASSED

- [ ] **Step 2: Verify CLI help**

Run: `python gmail_bulk_trash.py --help`

Expected: All arguments displayed including new `--top-senders`, `--top-limit`, `--days`

- [ ] **Step 3: Verify `re` import at module level**

Search for `import re` in `gmail_bulk_trash.py`. If inside `parse_email` function body, move to top-level imports section.

Run: `python -c "import gmail_bulk_trash; print('OK')"`

Expected: OK (no import errors)

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "chore: finalize top-senders feature"
```
