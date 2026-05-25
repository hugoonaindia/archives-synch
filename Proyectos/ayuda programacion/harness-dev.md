---
name: harness-dev
description: Úsala al iniciar cualquier proyecto que durará más de una sesión
  de IA, o cuando el agente pierde contexto entre sesiones, repite preguntas,
  o trabaja sin una definición clara de "terminado".
---

# Creating a Dev Harness

Un harness son 4 archivos que hacen al agente predecible entre sesiones.
Sin ellos, cada sesión empieza desde cero. Con ellos, el agente siempre
sabe las reglas, qué queda por hacer, si el entorno funciona, y dónde
paró la sesión anterior.

## Cuándo usar

- Proyecto que abarcará múltiples sesiones de IA
- El agente repite preguntas que ya respondiste antes
- No hay una definición clara de cuándo algo está "terminado"
- El usuario pide "estructura", "harness" o "sistema de control"

**No usar para:** scripts de un solo uso, tareas de una sesión, proyectos < 2h.

---

## Los 4 archivos

| Archivo | Rol | Cuándo lo lee el agente |
|---------|-----|------------------------|
| `CLAUDE.md` | Reglas: flujo, verificación, commits | Al inicio de cada sesión |
| `feature_list.json` | Inventario: qué existe, qué falta, qué está hecho | Antes de elegir la siguiente tarea |
| `init.sh` | Compuerta: verifica que el entorno realmente funciona | Antes de marcar cualquier tarea como done |
| `progress.md` | Diario: qué pasó, handoff a la próxima sesión | Al cerrar cada sesión |

---

## Cómo crear el harness

Crea los 4 archivos en la raíz del proyecto. Rellena los campos entre corchetes.

### 1. `CLAUDE.md`

```markdown
# [PROYECTO] — Reglas del Agente

## Proyecto
- **Qué es**: [una línea]
- **Stack**: [lenguajes / frameworks / DB]
- **Punto de entrada**: [comando para arrancar]

## Flujo
- Una feature a la vez (WIP = 1)
- No marcar "done" sin pasar `bash init.sh`
- `feature_list.json` es la fuente de verdad de qué falta
- `progress.md` es el diario — leerlo al empezar, escribirlo al cerrar

## Commits
feat | fix | refactor | test | docs | chore
Ejemplo: `feat(auth): add JWT refresh endpoint`
```

---

### 2. `feature_list.json`

Estados válidos: `pending` → `in-progress` → `done` | `blocked`
Una sola feature puede estar `in-progress` a la vez.

```json
{
  "features": [
    {
      "id": "F-001",
      "titulo": "Esqueleto del proyecto",
      "estado": "pending",
      "prioridad": "alta",
      "descripcion": "Estructura de carpetas, deps instaladas, punto de entrada ejecutable.",
      "definition_of_done": "bash init.sh pasa sin errores.",
      "dependencias": [],
      "notas": ""
    },
    {
      "id": "F-002",
      "titulo": "[Feature 2]",
      "estado": "pending",
      "prioridad": "alta",
      "descripcion": "[Qué hace esta feature]",
      "definition_of_done": "[Criterio concreto y verificable — un comando que pasa o falla]",
      "dependencias": ["F-001"],
      "notas": ""
    }
  ]
}
```

---

### 3. `init.sh`

Descomenta los bloques de tu stack. El script falla si no hay nada configurado.
Debe completar en menos de 30 segundos — tests lentos van en CI, no aquí.

```bash
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
```

---

### 4. `progress.md`

```markdown
# [PROYECTO] — Diario de Sesiones

## Sesión 1 — [FECHA]

Feature: F-001 — Esqueleto del proyecto

### Logros
-

### Decisiones
-

### Problemas
-

### Verificación
- [ ] bash init.sh pasa
- [ ] feature_list.json actualizado
- [ ] Commit creado

## Handoff
Próxima sesión: [qué hacer exactamente, sin ambigüedad]
Feature activa: F-001
```

Para cada sesión nueva, añade un bloque `## Sesión N` al principio del archivo.

---

## Checklist de inicio de sesión

1. Leer `progress.md` → buscar el último `## Handoff`
2. Ejecutar `bash init.sh` → confirmar que pasa
3. Abrir `feature_list.json` → encontrar la feature `in-progress` o la primera `pending`
4. Trabajar solo en esa feature

## Checklist de cierre de sesión

1. Ejecutar `bash init.sh` → debe pasar
2. Actualizar `feature_list.json` → estado correcto
3. Añadir entrada en `progress.md` con `## Handoff`
4. Hacer commit con el formato definido en `CLAUDE.md`

Una sesión sin handoff no está cerrada. El handoff es tan obligatorio como el commit.

---

## Errores comunes

| Error | Solución |
|-------|----------|
| `definition_of_done` es vaga ("funciona") | Reescribirla como un comando que pasa o falla |
| `init.sh` tarda más de 30s | Mover los tests lentos a un `ci.sh` separado |
| Varias features `in-progress` | Elegir una, las demás vuelven a `pending` |
| Sesión cerrada sin handoff | La próxima sesión empieza sin contexto — es un bug de proceso |
| `CLAUDE.md` con demasiado detalle | Mover las specs a archivos separados referenciados desde `CLAUDE.md` |
