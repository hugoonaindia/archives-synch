# MINIREVISIÓN — Spec mínima + Review rápida

> Versión ligera de `SUPERREVISION.md` para cambios pequeños, fixes, features acotadas o iteraciones rápidas.  
> Objetivo: evitar código improvisado sin convertir cada cambio en un proceso pesado.

---

## Principio general

No escribir código a ciegas.  
Antes de implementar, debe existir al menos una **spec mínima**.

Flujo rápido:

```text
MINI-SPEC → CODE → TEST → REVIEW → FIX → CIERRE
```

---

## Cuándo usar MINIREVISIÓN

Usar este archivo cuando:

- El cambio afecta a 1-3 archivos.
- Es un bugfix, refactor pequeño o feature sencilla.
- No requiere rediseño arquitectónico profundo.
- No cambia contratos públicos importantes.
- No toca seguridad crítica, pagos, datos sensibles o producción compleja.

Si el cambio es grande, ambiguo o arriesgado, usar `SUPERREVISION.md`.

---

## 1. MINI-SPEC obligatoria

Antes de tocar código, escribir esto:

```md
## MINI-SPEC

### Objetivo
[Qué se quiere conseguir en 1-3 frases]

### Alcance
- Incluye: [...]
- No incluye: [...]

### Criterios de aceptación
- [ ] El comportamiento esperado funciona.
- [ ] No se rompe comportamiento existente.
- [ ] Hay test o verificación clara.
```

Si el usuario pide código sin contexto suficiente:

```text
Necesito una mini-spec antes de tocar código. Resumo lo que entiendo y sigo con una propuesta mínima.
```

No bloquearse preguntando demasiado: si el cambio es razonablemente claro, proponer la mini-spec y avanzar.

---

## 2. Implementación rápida

Reglas mínimas:

- Cambiar solo lo necesario.
- No reescribir módulos enteros si no hace falta.
- Mantener nombres claros y type hints cuando sea Python.
- No hardcodear credenciales, rutas frágiles ni valores mágicos importantes.
- No usar `except: pass`.
- No silenciar errores sin justificar.
- Separar lógica de UI cuando sea sencillo hacerlo.

Para Python:

```bash
ruff check .
python -m py_compile archivo_modificado.py
pytest -q
```

Si no existen tests, hacer al menos una verificación manual explícita y dejarlo anotado.

---

## 3. Review rápida con 4 lentes

Revisar el cambio con estas 4 lentes:

### 1. Corrección

- ¿Hace exactamente lo que pide la mini-spec?
- ¿Hay edge cases evidentes?
- ¿Puede introducir data leakage, cálculos incorrectos o estados imposibles?

### 2. Calidad de código

- ¿Es legible?
- ¿Tiene responsabilidades mezcladas?
- ¿Hay código duplicado o muerto?
- ¿Hay errores silenciados?

### 3. Tests / verificación

- ¿Hay test automático?
- ¿Cubre el caso principal?
- ¿Cubre al menos un caso límite importante?
- Si no hay tests, ¿la verificación manual está descrita?

### 4. Riesgo operativo

- ¿Rompe configuración, rutas, imports o despliegue?
- ¿Introduce secretos o dependencias nuevas sin documentar?
- ¿Puede fallar en producción por entorno, permisos o datos vacíos?

---

## 4. Clasificación de issues

Usar solo 3 niveles:

```text
🔴 Crítico — rompe funcionalidad, seguridad, datos o ejecución.
⚠️ Importante — no bloquea todo, pero debe corregirse antes de cerrar.
🟢 Menor — mejora deseable, puede ir a deuda técnica.
```

Regla:

- Todo 🔴 se corrige.
- Todo ⚠️ se corrige o se justifica.
- Los 🟢 se anotan si no se arreglan.

---

## 5. Formato de salida del review

```md
## MINIREVIEW

### Resumen
[Qué se revisó y estado general]

### Issues encontrados

| Severidad | Archivo/Línea | Problema | Fix propuesto |
|----------|---------------|----------|---------------|
| 🔴/⚠️/🟢 | archivo.py:10 | ... | ... |

### Verificación
- [ ] ruff check .
- [ ] py_compile/import limpio
- [ ] pytest -q
- [ ] verificación manual si aplica

### Decisión
APROBADO / APROBADO CON DEUDA / RECHAZADO
```

---

## 6. Cierre rápido

Al terminar, dejar constancia breve:

```md
## CIERRE

### Cambios realizados
- ...

### Validaciones ejecutadas
- ...

### Deuda técnica pendiente
- ...

### Estado final
APROBADO / APROBADO CON DEUDA / RECHAZADO
```

---

## Prompts rápidos

### Revisar archivo concreto

```text
Ejecuta minirevision.md sobre [ARCHIVO]. Haz review rápida con 4 lentes. Devuelve issues priorizados con severidad, archivo/línea y fix propuesto. No hagas cambios.
```

### Arreglar issues críticos

```text
Lee el MINIREVIEW anterior y corrige solo los 🔴 críticos y ⚠️ importantes. No hagas refactors no solicitados. Después ejecuta verificación mínima.
```

### Cambio pequeño completo

```text
Usa minirevision.md. Crea mini-spec, implementa el cambio mínimo, verifica con ruff/pytest si aplica y cierra con resumen breve.
```

### Verificación final

```text
Ejecuta verificación final según minirevision.md: ruff, py_compile/import, pytest si existe, y resume estado final.
```

---

## Regla de oro

La minirevisión existe para avanzar rápido sin perder control.

Si empiezas a necesitar demasiadas excepciones, muchas preguntas o varios módulos afectados, deja de usar este archivo y cambia a `SUPERREVISION.md`.
