# Recon Mejoras — Interactividad + Configurabilidad

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create implementation plan (recommended) or superpowers:executing-plans to implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer `recon.py` más robusto eliminando timing frágil, agregando control interactivo (ESPACIO + opciones R/S). Agregar a `sync.py` la capacidad de preguntar qué días sincronizar dinámicamente.

**Architecture:** Refactor mínimo. Nueva función `capture_screenshot_interactive()` en `recon.py` con manejo de ESPACIO/R/S. Nueva función `ask_sync_days()` en `sync.py` que filtra citas por días seleccionados. Ambos scripts siguen siendo monolitos.

**Tech Stack:** Python 3.12+, pyautogui (input), openai SDK, pytest

---

## §1. Problem Statement

**Actual (fragilidad):**
- `recon.py` espera 5s → toma screenshot automático
- Usuario no tiene control
- Si mueve mouse o algo falla, screenshot queda mal
- Imposible reintentar sin re-ejecutar todo

**Deseado:**
- Usuario controla con ESPACIO cuándo capturar
- Opciones: [ESPACIO] Capturar | [R] Reintentar | [S] Saltar
- Más robusto, mayor precisión

**Plus: Configurabilidad**
- Actualmente `sync.py` excluye lunes/miércoles (hardcoded)
- Debería preguntar cada semana qué días sincronizar
- `sync.py` → `ask_sync_days()` → usuario selecciona

---

## §2. Design: `recon.py` Changes

### 2.1 Nueva función: `capture_screenshot_interactive()`

```python
def capture_screenshot_interactive(step_name: str) -> Optional[str]:
    """
    Captura screenshot con control interactivo del usuario.
    
    Args:
        step_name: "calendario" o "formulario"
    
    Returns:
        base64 PNG string si capturó
        None si usuario presiona S (saltar)
    
    Flow:
        1. Muestra instrucciones (ej: "Abre Archivex en vista semanal")
        2. Espera input: [ESPACIO] Capturar | [R] Reintentar | [S] Saltar
        3. Si ESPACIO: captura screenshot, retorna base64
        4. Si R: repite paso 2
        5. Si S: retorna None
    """
```

**Pseudo-código:**
```python
while True:
    print(f"📍 {STEP_INSTRUCTIONS[step_name]}")
    print("   [ESPACIO] Capturar | [R] Reintentar | [S] Saltar")
    
    key = pyautogui.press()  # bloqueante
    
    if key == "space":
        return _screenshot_b64()
    elif key == "r":
        continue  # repite
    elif key == "s":
        return None
    else:
        print("   Presiona ESPACIO, R o S")
```

### 2.2 Cambios en `run_recon()`

```python
def run_recon() -> dict:
    # ... validación API key igual ...
    
    # Paso 1: calendario
    shot1 = capture_screenshot_interactive("calendario")
    if shot1 is None:
        sys.exit("❌ Usuario saltó captura de calendario")
    
    # Paso 2: formulario
    shot2 = capture_screenshot_interactive("formulario")
    if shot2 is None:
        log.warning("Formulario no capturado — continuaremos sin él")
        shot2 = None  # puede ser None, el modelo inferirá
    
    # Envía al modelo
    messages = [
        {"role": "user", "content": [
            {"type": "text", "text": "Screenshot 1 (calendario):"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{shot1}"}},
        ]}
    ]
    if shot2:
        messages[0]["content"].extend([
            {"type": "text", "text": "Screenshot 2 (formulario):"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{shot2}"}},
        ])
    
    # ... resto igual (API call, validación, etc.) ...
```

### 2.3 Instrucciones (constantes nuevas)

```python
STEP_INSTRUCTIONS = {
    "calendario": (
        "Abre Archivex Clinical en vista semanal.\n"
        "Asegúrate de que el calendario sea visible sin obstáculos."
    ),
    "formulario": (
        "Abre el formulario de nueva cita haciendo doble clic en un slot vacío.\n"
        "El formulario debe estar completamente visible."
    ),
}
```

---

## §3. Design: `sync.py` Changes

### 3.1 Nueva función: `ask_sync_days()`

```python
def ask_sync_days() -> set[int]:
    """
    Pregunta al usuario qué días quiere sincronizar.
    
    Returns:
        set de weekdays (0=lun, 1=mar, ..., 6=dom)
    
    Opciones predefinidas:
        [T] Martes-Viernes (recomendado)
        [L] Lunes-Viernes (standard)
        [A] Todos los días (lun-dom)
        [P] Personalizado (ingresa 0-6)
    
    Ejemplo output:
        >>> ask_sync_days()
        ¿Qué días quieres sincronizar?
        [T] Martes-Viernes    [L] Lunes-Viernes
        [A] Todos los días    [P] Personalizado
        Selecciona [T/L/A/P]: T
        >>> {1, 3, 4}  # martes, jueves, viernes
    """
    presets = {
        "T": {1, 3, 4},           # martes, jueves, viernes
        "L": {0, 1, 3, 4, 5},     # lunes-viernes
        "A": {0, 1, 2, 3, 4, 5, 6},  # todos
    }
    
    while True:
        print("\n¿Qué días quieres sincronizar?")
        print("[T] Martes-Viernes (recomendado)")
        print("[L] Lunes-Viernes")
        print("[A] Todos los días")
        print("[P] Personalizado")
        
        choice = input("Selecciona [T/L/A/P]: ").strip().upper()
        
        if choice in presets:
            return presets[choice]
        elif choice == "P":
            # Parse input: "0 1 3 4" → {0, 1, 3, 4}
            dias_str = input("Ingresa días (ej: 0 1 3 4): ").strip()
            try:
                dias = {int(d) for d in dias_str.split()}
                if all(0 <= d <= 6 for d in dias):
                    return dias
            except ValueError:
                pass
            print("Entrada inválida. Intenta de nuevo.")
        else:
            print("Selecciona T, L, A o P")
```

### 3.2 Integración en `main()`

```python
def main() -> None:
    print("🗓  Archivex Sync")
    print("─" * 40)

    # Validar API key (igual)
    if not os.getenv("OPENROUTER_API_KEY"):
        sys.exit("❌  OPENROUTER_API_KEY no está configurada...")

    kb = load_knowledge()
    
    # NUEVO: preguntar días
    sync_days = ask_sync_days()
    print(f"✅ Días a sincronizar: {sorted(sync_days)}")

    # ... obtener citas igual ...
    appointments = get_week_appointments(service, monday)
    
    # NUEVO: filtrar por sync_days
    appointments = [
        a for a in appointments
        if a.day_offset in sync_days
    ]
    
    print(f"📋  {len(appointments)} cita(s) a procesar")
    
    # ... resto igual ...
```

---

## §4. Error Handling

| Escenario | Acción |
|-----------|--------|
| Usuario salta calendario | `sys.exit("❌ Usuario saltó captura...")` |
| Usuario salta formulario | Continúa, infiere del prompt |
| Entrada inválida en `ask_sync_days()` | Repite pregunta |
| No hay citas para días seleccionados | Imprime "Nada que sincronizar" |
| Timeout en captura interactiva | pyautogui timeout (default OK) |

---

## §5. Testing

**Tests en `test_recon.py`:**
- `test_capture_interactive_space()` → usuario presiona ESPACIO
- `test_capture_interactive_retry()` → usuario presiona R, luego ESPACIO
- `test_capture_interactive_skip()` → usuario presiona S
- `test_run_recon_skips_calendar()` → error si salta calendario
- `test_run_recon_formulario_optional()` → continúa si salta formulario

**Tests en `test_sync.py`:**
- `test_ask_sync_days_martes_viernes()` → elige T
- `test_ask_sync_days_personalizado()` → elige P, ingresa "0 1 3"
- `test_main_filters_appointments_by_sync_days()` → filtra correctamente
- `test_main_ask_sync_days_integration()` → flujo completo

**Mocking:**
- Mock `pyautogui.press()` → retorna "space", "r", "s" según test
- Mock `input()` → retorna "T", "L", "P" según test
- Existing mocks para OpenAI, etc. siguen igual

---

## §6. Backwards Compatibility

- Existing `ui_knowledge.json` sigue válido (sin cambios de estructura)
- `sync.py` sigue funcionando con SKIP_DAYS si alguien no quiere usar `ask_sync_days()`
  - (Podríamos mantener SKIP_DAYS como fallback, pero mejor: obligamos la pregunta)
- `recon.py` sigue produciendo mismo JSON

---

## §7. Out of Scope (deliberadamente NO tocamos)

- Refactorizar a módulos separados (monolitos por decisión)
- Cambiar estructura de `ui_knowledge.json`
- Agregar config persistente en archivos (KISS)
- Mejorar modelo vision (separate work)
- Agregar GUI (out of scope)

---

## §8. Success Criteria

✅ `recon.py` acepta ESPACIO + R/S interactivamente
✅ `sync.py` pregunta días cada ejecución
✅ 43 tests pasan (nuevos + existentes)
✅ Lint clean
✅ Documentación clara en scripts

---

## §9. Implementación Iteración 1: capture_screenshot_interactive() — 2026-05-25

- **Qué**: Implementó `capture_screenshot_interactive()` en recon.py. Reemplazó timing automático (esperar 5s) con controles interactivos [ESPACIO] capturar / [R] reintentar / [S] saltar. Refactorizó `run_recon()` para usar nueva función. Hizo captura de formulario opcional.
- **Por qué**: §2.1 del design spec - eliminar fragilidad de timing, dar control al usuario
- **Tests**: 4 nuevos tests + 39 existentes = 43 passing | lint: clean
- **Decisión**: Importé `Optional` desde typing explícitamente para satisfacer ruff lint (strict mode)
- **Próximo**: Implementar `ask_sync_days()` en sync.py (§3 del design spec)

