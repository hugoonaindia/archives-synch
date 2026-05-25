#!/bin/bash
set -e
echo "=== init.sh — [PROYECTO] ==="

# ── 1. Runtime ─────────────────────────────────────────────
# Descomenta UNO:
# python --version || { echo "ERROR: Python no encontrado"; exit 1; }
# node --version   || { echo "ERROR: Node no encontrado"; exit 1; }
# go version       || { echo "ERROR: Go no encontrado"; exit 1; }
# cargo --version  || { echo "ERROR: Cargo no encontrado"; exit 1; }
RUNTIME_CONFIGURED=false   # ← cambia a true cuando descomentes algo

# ── 2. Dependencias ────────────────────────────────────────
# pip install -r requirements.txt -q
# npm install --silent
# go mod download

# ── 3. Linter ──────────────────────────────────────────────
# ruff check . -q
# npx eslint . --max-warnings 0 -q
# golangci-lint run -q

# ── 4. Tests ───────────────────────────────────────────────
# pytest tests/ -q --tb=short
# npm test -- --silent
# go test ./... -q
# cargo test -q

# ── Guardia: falla si no se configuró nada ─────────────────
if [ "$RUNTIME_CONFIGURED" = false ]; then
  echo ""
  echo "ERROR: init.sh no está configurado."
  echo "Descomenta los bloques correspondientes a tu stack y cambia RUNTIME_CONFIGURED a true."
  exit 1
fi

echo ""
echo "✓ Entorno listo"
echo ""

# ── Siguiente feature ──────────────────────────────────────
python3 - <<'PY'
import json, sys
try:
    data = json.load(open("feature_list.json"))
    for status in ("in-progress", "pending"):
        for f in data.get("features", []):
            if f.get("estado") == status:
                print(f"Siguiente: [{f['id']}] {f['titulo']}  ({f['estado']})")
                print(f"  DoD: {f['definition_of_done']}")
                sys.exit(0)
    print("Todas las features están en 'done'. Proyecto completo.")
except FileNotFoundError:
    print("feature_list.json no encontrado.")
PY
