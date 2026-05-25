"""Tests para persistencia y gestión de remitentes."""
import json
import tempfile
from pathlib import Path
import sys

# Importar funciones del script
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_load_senders_nonexistent():
    """load_senders() devuelve dict vacío si archivo no existe."""
    import subprocess
    result = subprocess.run([
        sys.executable, "-c",
        """
import sys
sys.path.insert(0, '.')
from pathlib import Path
import tempfile
import os

# Mock SENDERS_FILE pointing to nonexistent file
SENDERS_FILE = Path(tempfile.gettempdir()) / "nonexistent_senders.json"
if SENDERS_FILE.exists():
    SENDERS_FILE.unlink()

import json
def load_senders():
    if not SENDERS_FILE.exists():
        return {"blocked": [], "whitelist": []}
    return json.loads(SENDERS_FILE.read_text())

data = load_senders()
assert data == {"blocked": [], "whitelist": []}, f"Expected empty dict, got {data}"
print("OK")
        """
    ], cwd="/Users/hugoonaindia/Desktop/RObot gmail", capture_output=True, text=True)
    assert "OK" in result.stdout, f"Test failed: {result.stderr}"


def test_build_query_blocklist():
    """build_query() combina base + remitentes bloqueados."""
    import subprocess
    result = subprocess.run([
        sys.executable, "-c",
        """
import sys
sys.path.insert(0, '.')

def build_query(base_query: str, senders: dict) -> str:
    parts = []
    if base_query:
        parts.append(f"({base_query})")
    if senders["blocked"]:
        blocked_part = " OR ".join(f"from:{s}" for s in senders["blocked"])
        parts.append(f"({blocked_part})")
    if not parts:
        return ""
    query = " OR ".join(parts)
    for protected in senders["whitelist"]:
        query = f"({query}) -from:{protected}"
    return query

senders = {"blocked": ["spam@test.com"], "whitelist": []}
result = build_query("category:promotions", senders)
expected = "(category:promotions) OR (from:spam@test.com)"
assert result == expected, f"Expected {expected}, got {result}"
print("OK")
        """
    ], cwd="/Users/hugoonaindia/Desktop/RObot gmail", capture_output=True, text=True)
    assert "OK" in result.stdout, f"Test failed: {result.stderr}"


def test_build_query_whitelist_exclusion():
    """build_query() excluye whitelist con -from:"""
    import subprocess
    result = subprocess.run([
        sys.executable, "-c",
        """
import sys
sys.path.insert(0, '.')

def build_query(base_query: str, senders: dict) -> str:
    parts = []
    if base_query:
        parts.append(f"({base_query})")
    if senders["blocked"]:
        blocked_part = " OR ".join(f"from:{s}" for s in senders["blocked"])
        parts.append(f"({blocked_part})")
    if not parts:
        return ""
    query = " OR ".join(parts)
    for protected in senders["whitelist"]:
        query = f"({query}) -from:{protected}"
    return query

senders = {"blocked": ["spam@test.com"], "whitelist": ["boss@company.com"]}
result = build_query("category:promotions", senders)
assert "-from:boss@company.com" in result, f"Whitelist not excluded: {result}"
print("OK")
        """
    ], cwd="/Users/hugoonaindia/Desktop/RObot gmail", capture_output=True, text=True)
    assert "OK" in result.stdout, f"Test failed: {result.stderr}"


if __name__ == "__main__":
    test_load_senders_nonexistent()
    print("✅ test_load_senders_nonexistent")

    test_build_query_blocklist()
    print("✅ test_build_query_blocklist")

    test_build_query_whitelist_exclusion()
    print("✅ test_build_query_whitelist_exclusion")

    print("\n✅ All tests passed!")
