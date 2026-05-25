# SUPERREVISIÓN

Guía única para trabajar con **Spec-Driven Development** y revisión autónoma de código. Cubre el flujo completo desde la especificación hasta el merge, con revisión en 3 pasadas usando 6 lentes.

> Este archivo reemplaza a `CLAUDE.md` y `TODO.md` como referencia operativa del proyecto.
>
> **Archivo canónico de resultados:** `documento_maestro_unificado.md`
>
> Toda instrucción de "documentar resultados" apunta a ese archivo, especialmente a:
>
> - Sección 20.3: scores por pasada
> - Sección 20.4: conteo de issues
> - Sección 20.5: deuda técnica priorizada

---

## 1. Principio Rector

Sin spec aprobada no se escribe código.

Flujo obligatorio:

```text
SPEC -> PLAN -> CODE -> TEST -> REVIEW -> DEPLOY
```

Si el usuario pide código sin spec:

> Antes de escribir código necesito crear la spec. ¿Empezamos?

### 1.1 Micro-Spec Para Cambios Pequeños

Para fixes pequeños, ajustes de documentación, cambios de configuración o tareas con alcance muy limitado, se permite una **micro-spec** en vez de una spec completa.

Usar micro-spec solo si se cumplen todos:

- El cambio afecta a un módulo o archivo principal.
- No cambia arquitectura, contratos públicos ni modelo de datos.
- No introduce dependencia nueva.
- Puede verificarse con comandos concretos.
- El riesgo de regresión es bajo.

Formato mínimo:

```text
Micro-spec:
Objetivo: [qué se quiere conseguir]
Alcance: [archivos/módulos afectados]
Fuera de alcance: [qué NO se tocará]
Validación: [comandos o checks]
Riesgo: [bajo/medio + motivo]
```

Si cualquiera de esos puntos no está claro, volver a spec completa.

---

## 2. Ciclo De Trabajo

```text
1. INICIO
   @Arquitecto analiza requisitos, crea SPEC y espera aprobación.

2. IMPLEMENTACIÓN ITERATIVA
   @Programador implementa por módulos con TDD: RED -> GREEN -> REFACTOR.
   @Tester añade o ajusta tests por módulo.

3. REVISIÓN
   @Revisor ejecuta 3 pasadas con 6 lentes.
   APROBADO -> paso 4
   RECHAZADO -> @Programador corrige y vuelve a revisión.

4. PRODUCCIÓN
   @DevOps prepara Docker, CI/CD, variables y healthchecks.
   @Documentador actualiza README, CHANGELOG y ADRs relevantes.
```

### 2.1 Entradas Y Salidas Por Fase

| Fase | Entrada requerida | Salida esperada |
|---|---|---|
| SPEC | Requisitos, contexto y restricciones | Spec o micro-spec aprobada con criterios de aceptación |
| PLAN | Spec aprobada | Plan con pasos verificables, riesgos y archivos previstos |
| CODE | Plan aprobado | Implementación mínima que cumple la spec |
| TEST | Código implementado | Tests nuevos o actualizados, más comandos ejecutados |
| REVIEW | Diff, spec y resultados de tests | Findings con severidad, estado y `file:line` |
| DEPLOY | Revisión aprobada | Build/deploy reproducible, configuración documentada y cierre |

Cada fase debe dejar claro qué queda fuera de alcance. Si aparece trabajo nuevo, se registra como deuda o se abre una nueva spec.

---

## 3. Roles Disponibles

Activar con `@Nombre`. El asistente adopta ese rol en la misma conversación; no hay contexto aislado entre roles. Si se cambia de rol a mitad de tarea, indicar el estado actual antes de continuar.

| Rol | Cuándo usarlo | Entregable principal |
|---|---|---|
| `@Arquitecto` | Inicio de proyecto, feature o cambio relevante | `SPEC_[nombre].md` |
| `@Programador` | Spec aprobada y plan definido | Código con TDD, type hints y SRP |
| `@Tester` | Después de cada módulo o fix | Tests `pytest`, cobertura >= 80% |
| `@Revisor` | Antes de merge o entrega | Findings priorizados con `file:line` |
| `@DevOps` | Código aprobado | Dockerfile, CI/CD, `.env.example`, healthchecks |
| `@Documentador` | Cierre de fase o cambio público | README, CHANGELOG, ADRs |

---

## 4. Revisión En 3 Pasadas

### Comando De Lanzamiento

```text
Ejecuta SUPERREVISION.md:
1. PASADA 1 - Revisión profunda + fixes críticos
2. PASADA 2 - Re-revisión + fixes residuales
3. PASADA 3 - Verificación final + cierre
```

### Las 6 Lentes

| Lente | Qué busca |
|---|---|
| Arquitectura | SRP, acoplamiento, límites de módulos, escalabilidad |
| Calidad de código | Tipos, imports, errores silenciados, duplicación, legibilidad |
| Corrección | Bugs, fórmulas, data leakage, seguridad, performance |
| Tests | Cobertura, edge cases, mocks, flakiness, regresiones |
| DevOps | Docker, CI/CD, logging, configuración, secrets |
| Documentación | README, docstrings, changelog, ADRs, coherencia con el código |

> Seguridad y performance se revisan dentro de **Corrección**. En la tabla de scores pueden aparecer desglosadas para dar más granularidad.

### Scope De Revisión

Antes de revisar, declarar el scope:

| Scope | Cuándo usarlo | Qué revisar |
|---|---|---|
| `diff` | PR pequeño o fix acotado | Solo cambios entre `BASE_SHA` y `HEAD_SHA` |
| `archivos-modificados` | Feature mediana | Archivos tocados y tests relacionados |
| `modulo-afectado` | Cambio con impacto local | Módulo completo, dependencias directas y tests |
| `proyecto-completo` | Release, refactor grande o auditoría | Todo el repo y flujos críticos |

El scope por defecto es `archivos-modificados`. Subir a `modulo-afectado` si el diff toca contratos públicos, datos compartidos, configuración global, autenticación, seguridad, performance o modelos ML.

### Severidad

| Marca | Significado | Acción |
|---|---|---|
| 🔴 Crítico | Bug de correctness, data leakage, secret expuesto, crash en hot path, vulnerabilidad explotable | Bloquea merge |
| ⚠️ Medium | Riesgo real, test faltante, performance degradada, error silenciado, deuda que puede causar bug | Corregir antes de cerrar ciclo o justificar explícitamente |
| 🟢 Low | Estilo, naming, docstring, refactor cosmético, mejora no bloqueante | Registrar como deuda técnica |

### Estados De Issue

| Estado | Uso |
|---|---|
| `open` | Confirmado y pendiente |
| `fixed` | Corregido y verificado |
| `wontfix-justified` | No se corrige por decisión técnica documentada |
| `false-positive` | El finding no aplica tras verificar el código |
| `deferred` | Se difiere como deuda técnica priorizada |

Todo issue 🔴 debe terminar como `fixed` o `false-positive`. Un 🔴 no puede cerrarse como `deferred`.

### Rúbrica De Scores

| Score | Interpretación |
|---:|---|
| 10 | Sin hallazgos relevantes; diseño, tests y documentación sólidos |
| 9 | Solo mejoras menores no bloqueantes |
| 8 | Aprobable; quedan lows o deuda explícita controlada |
| 7 | Funciona, pero quedan mediums o huecos de test/documentación |
| 6 | Riesgo moderado; requiere fixes antes de merge |
| <= 5 | Bloqueado; hay críticos, comportamiento dudoso o validación insuficiente |

El promedio nunca puede aprobar si existe un 🔴 abierto, aunque numéricamente sea >= 8.0.

### Criterio De Aprobación

Para aprobar la Pasada 3 deben cumplirse todos:

- Promedio de scores >= 8.0/10
- 0 issues 🔴 críticos
- Todo ⚠️ medium corregido o justificado
- Cobertura >= 80%
- `ruff check .` limpio
- `pytest` verde
- Import principal verificado sin side effects inesperados

---

## 5. Pasada 1: Revisión Profunda + Fixes Críticos

### 5.1 Revisión

Ejecutar las 6 lentes y registrar findings con:

```text
ID: REV-[pasada]-[número]
Estado: open
Severidad: [🔴/⚠️/🟢]
Lente: [Arquitectura/Calidad/Corrección/Tests/DevOps/Documentación]
Ubicación: file:line
Problema: [qué ocurre]
Evidencia: [qué código, test o comando lo demuestra]
Impacto: [qué puede romper o degradar]
Fix recomendado: [cambio concreto]
```

Checklist por lente:

**Arquitectura**

- Funciones o módulos con más de una responsabilidad
- Código muerto, bloques inaccesibles o imports sin usar
- Singletons globales o estado mutable compartido
- Acoplamiento innecesario entre UI, dominio, infraestructura o datos

**Calidad de código**

- `Any` innecesario o `# type: ignore` sin justificación
- `except: pass` o `except Exception` demasiado amplio
- Imports locales que deberían ser globales
- Módulos demasiado grandes sin frontera clara
- Duplicación que puede provocar divergencias

**Corrección**

- Fórmulas incorrectas, `ddof` incorrecto, redondeos peligrosos
- Implementaciones custom donde conviene librería probada
- Look-ahead bias, data leakage o normalización fit-total en vez de fit-train
- Path traversal, inyección, validación insuficiente o secrets expuestos
- Hot paths con complejidad o I/O innecesario

**Tests**

- Funciones públicas o ramas críticas sin test
- Edge cases: cero, NaN, vacío, `None`, cadenas vacías, fechas límite
- Dependencias externas sin mock
- Tests frágiles por orden, tiempo, red o estado global

**DevOps**

- Dockerfile sin multi-stage cuando aplique
- Falta de `HEALTHCHECK`, `CMD` válido o `.dockerignore`
- Variables de entorno sin documentación ni fallback explícito
- Logging sin estructura, rotación o nivel configurable
- Secrets hardcodeados o versionados

**Documentación**

- README sin setup, uso, tests o variables
- Docstrings ausentes en funciones públicas complejas
- CHANGELOG desactualizado
- Decisiones arquitectónicas relevantes sin ADR

### 5.2 Fixes

- [ ] Corregir todos los issues 🔴 críticos
- [ ] Corregir issues ⚠️ medium quick-fix, si cada uno toma menos de 15 minutos
- [ ] No tocar issues 🟢 low salvo que el fix sea trivial y no aumente riesgo

### 5.3 Validación

- [ ] `ruff check .`
- [ ] `python -m py_compile <archivo_principal>`
- [ ] `pytest tests/ -v`
- [ ] Documentar resultados en `documento_maestro_unificado.md`

---

## 6. Pasada 2: Re-Revisión + Fixes Residuales

### 6.1 Revisión

- [ ] Re-ejecutar las 6 lentes sobre el código corregido
- [ ] Buscar regresiones introducidas por los fixes
- [ ] Confirmar que los críticos de Pasada 1 no reaparecen
- [ ] Separar falsos positivos de deuda real

### 6.2 Fixes

- [ ] Corregir regresiones
- [ ] Corregir ⚠️ medium restantes
- [ ] Corregir 🟢 low quick-fix si no aumenta riesgo

### 6.3 Validación

- [ ] `ruff check .`
- [ ] `pytest tests/ -v`
- [ ] Verificar fixes de Pasada 1 intactos
- [ ] Actualizar `documento_maestro_unificado.md`

---

## 7. Pasada 3: Verificación Final + Cierre

### 7.1 Verificación

- [ ] Ejecutar una revisión final usando las 6 lentes en un solo pase
- [ ] Confirmar 0 issues 🔴 críticos
- [ ] Confirmar que todo ⚠️ medium está corregido o justificado
- [ ] Contabilizar 🟢 low como deuda técnica

### 7.2 Validación Final

- [ ] `ruff check .`
- [ ] `pytest tests/ -v`
- [ ] `python -c "import <modulo>; print('OK')"`

### 7.3 Cierre

- [ ] Volcar scores en sección 20.3
- [ ] Volcar conteo de issues en sección 20.4
- [ ] Volcar deuda técnica priorizada en sección 20.5
- [ ] Confirmar si el proyecto queda aprobado o bloqueado

> Si en Pasada 3 queda algún 🔴 crítico, no mergear. Reiniciar Pasada 1 con scope acotado al módulo afectado. No crear una Pasada 4 improvisada.

### 7.4 Si La Revisión Bloquea

Cuando el ciclo queda bloqueado:

1. Declarar el motivo exacto del bloqueo.
2. Listar solo los issues bloqueantes con ID y ubicación.
3. Reducir el scope al módulo afectado si el problema está localizado.
4. Corregir en una rama o commit separado si el cambio es riesgoso.
5. Repetir desde Pasada 1 para ese scope.
6. Documentar en `documento_maestro_unificado.md` qué se reabrió y por qué.

No mezclar nuevos features con fixes de desbloqueo.

---

## 8. Cómo Solicitar Review

Usar después de cada tarea relevante, al completar una feature o antes de merge.

### 8.1 Obtener SHAs

```bash
BASE_SHA=$(git rev-parse HEAD~1)   # o origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

### 8.2 Dispatch Del Reviewer

Solicitar una instancia fresca de revisión para evitar sesgo de auto-revisión e incluir:

- `{DESCRIPTION}`: qué se construyó
- `{PLAN_OR_REQUIREMENTS}`: qué debería hacer
- `{BASE_SHA}`: commit base
- `{HEAD_SHA}`: commit actual

### 8.3 Actuar Sobre Feedback

- 🔴 Crítico: fix inmediato
- ⚠️ Medium: fix antes de continuar o justificación técnica
- 🟢 Low: deuda técnica priorizada
- Push back si el feedback es incorrecto para este código o este stack

---

## 9. Cómo Recibir Review

Proceso obligatorio:

```text
1. LEER: feedback completo sin reaccionar.
2. ENTENDER: reformular el requerimiento.
3. VERIFICAR: contrastar contra el código real.
4. EVALUAR: decidir si aplica técnicamente a este proyecto.
5. RESPONDER: aceptar, corregir o hacer push back razonado.
6. IMPLEMENTAR: uno a uno, verificando cada cambio.
```

Prohibido responder con frases vacías como "tienes toda la razón" o "gran punto". Actuar con evidencia.

Preguntar si algo no está claro. No implementar parcialmente un feedback ambiguo.

### Cuándo Hacer Push Back

- La sugerencia rompe funcionalidad existente
- El reviewer no tiene contexto completo
- La propuesta viola YAGNI
- Es incorrecta para este stack
- Choca con decisiones arquitectónicas previas documentadas

Forma recomendada:

```text
No aplico este cambio tal como está porque [razón técnica verificable].
Alternativa propuesta: [cambio menor / test / documentación / no-op justificado].
```

---

## 10. Red Flags

Detener el flujo y volver al paso correcto si aparece cualquiera de estas racionalizaciones:

| Racionalización | Realidad operativa |
|---|---|
| "Es muy simple para spec" | Simple no significa sin requisitos. Escribir spec breve. |
| "Ya lo probé manualmente" | Sin test automatizado, no hay garantía reproducible. |
| "Solo es un fix rápido" | Fix sin contexto puede reintroducir bugs. |
| "No necesita revisión" | Lo trivial también rompe producción. |
| "Esto es urgente, revisión después" | Urgente sin revisión suele costar más tiempo después. |
| "El reviewer no entiende" | Aclarar el contexto o hacer push back técnico. |

---

## 11. Templates Para Resultados

Destino: `documento_maestro_unificado.md`.

### 11.1 Scores -> Sección 20.3

| Categoría | Pasada 1 | Pasada 2 | Pasada 3 |
|---|---:|---:|---:|
| Architecture | /10 | /10 | /10 |
| Code Quality | /10 | /10 | /10 |
| Math Correctness | /10 | /10 | /10 |
| Security | /10 | /10 | /10 |
| Performance | /10 | /10 | /10 |
| Tests | /10 | /10 | /10 |
| DevOps | /10 | /10 | /10 |
| Documentation | /10 | /10 | /10 |
| **Promedio** | /10 | /10 | /10 |

### 11.2 Conteo De Issues -> Sección 20.4

| Severidad | Pasada 1 | Pasada 2 | Pasada 3 |
|---|---:|---:|---:|
| 🔴 Crítico |  |  |  |
| ⚠️ Medium |  |  |  |
| 🟢 Low |  |  |  |
| **TOTAL** |  |  |  |

### 11.3 Deuda Técnica Priorizada -> Sección 20.5

```text
1. ⚠️ REV-2-003 - [Issue] - [impacto] -> [fix propuesto] - Estado: deferred
2. 🟢 REV-3-001 - [Issue] - [nota] -> [cuándo revisarlo] - Estado: deferred
```

### 11.4 Formato De Finding

```text
ID: REV-1-001
Estado: open
Severidad: 🔴
Lente: Corrección
Ubicación: src/module.py:42
Problema: normaliza usando todo el dataset antes del split.
Evidencia: scaler.fit(df) ocurre antes de train_test_split().
Impacto: introduce data leakage y sobreestima métricas.
Fix recomendado: ajustar scaler solo con train y aplicar transform a val/test.
```

---

## 12. Prompts Rápidos

| Propósito | Prompt |
|---|---|
| Revisión completa | `Revisa SUPERREVISION.md y ejecuta PASADA 1 sobre el proyecto usando las 6 lentes. Devuelve findings priorizados con file:line. No hagas cambios.` |
| Review con scope | `Ejecuta review scope=[diff/archivos-modificados/modulo-afectado/proyecto-completo] usando SUPERREVISION.md. Declara scope, evidencia y estado por issue.` |
| Solo fixes críticos | `Lee documento_maestro_unificado.md y corrige todos los 🔴 críticos. Verifica con ruff y pytest tras cada fix.` |
| Verificación rápida | `Ejecuta ruff check ., pytest tests/ -v e import del módulo principal. Reporta errores y comandos usados.` |
| Micro-spec | `Crea una micro-spec para este cambio con objetivo, alcance, fuera de alcance, validación y riesgo. Espera aprobación antes de tocar código.` |
| Archivo específico | `Haz code review senior de [ARCHIVO] usando las 6 lentes. Devuelve severity, file:line, impacto y fix.` |
| Recibir feedback | `Recibiste review con issues. Aplica el flujo de recibir review: verificar contra código real, implementar uno a uno y testear cada cambio.` |
| Solicitar review | `Solicita review con instancia fresca: obtiene BASE_SHA y HEAD_SHA, describe cambios y pide findings priorizados.` |
| Ciclo completo | `Ejecuta SUPERREVISION.md: Pasada 1 -> fixes -> Pasada 2 -> fixes -> Pasada 3 -> cierre. Documenta en documento_maestro_unificado.md.` |

---

## 13. Skills Relacionadas

| Situación | Skill |
|---|---|
| Antes de escribir código | `brainstorming`, luego `writing-plans` |
| Implementar con TDD | `test-driven-development` |
| Investigar bug | `systematic-debugging` |
| Solicitar review | `requesting-code-review` |
| Recibir review | `receiving-code-review` |
| Finalizar branch | `finishing-a-development-branch` |

---

## 14. Estándares De Código Python

### 14.1 Stack Por Defecto

| Capa | Stack |
|---|---|
| Backend | FastAPI + Pydantic v2 |
| DB | PostgreSQL con SQLAlchemy / SQLite en desarrollo |
| Tests | pytest + pytest-cov + pytest-asyncio |
| Linting | ruff + mypy |
| Deploy | Docker + docker-compose |

### 14.2 Reglas De Código

- Type hints siempre.
- Máximo recomendado: 50 líneas por función.
- Excepción: pipelines ML/training donde la cohesión justifica más longitud. Marcar con comentario `# domain-complex`.
- Imports en orden: stdlib, terceros, locales.
- No hardcodear valores: usar constantes, settings o config.
- Manejar errores explícitamente; nunca `except: pass`.
- Docstrings en funciones públicas o con lógica no obvia.
- Logger con `%s` / `%d`, no f-strings, para evitar formateo eager.
- Preferir `X | None` sobre `Optional[X]` en Python 3.10+.

Ejemplo:

```python
def process_data(input_data: dict[str, object]) -> dict[str, object]:
    if not input_data:
        raise ValueError("input_data no puede estar vacío")

    logger.info("Procesando %d campos", len(input_data))
    ...
```

### 14.3 `pyproject.toml` Base

```toml
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 14.4 Matriz De Verificación

| Comando | Cuándo | Obligatorio |
|---|---|---|
| `ruff check .` | Siempre que haya código Python | Sí |
| `pytest` o `pytest tests/ -v` | Siempre que existan tests | Sí |
| `python -m py_compile <archivo_principal>` | Scripts o módulos sin test directo | Sí, si aplica |
| `python -c "import <modulo>; print('OK')"` | Librerías, apps o paquetes importables | Sí, si aplica |
| `mypy .` | Si el proyecto usa mypy o tipos estrictos | Sí |
| `pytest --cov` | Si existe configuración de coverage | Sí |
| `docker compose build` | Si el cambio toca Docker/deploy | Sí |
| `pre-commit run --all-files` | Si el repo usa pre-commit | Sí |

Si un comando no existe o no aplica, documentar el motivo y usar el fallback más cercano. No marcar la tarea como aprobada sin explicar la brecha de verificación.

### 14.5 Excepciones Controladas

Estas excepciones reducen ceremonia, pero no eliminan responsabilidad:

| Caso | Regla |
|---|---|
| Script exploratorio | Micro-spec permitida; debe quedar fuera de producción o claramente marcado |
| Notebook | Validar ejecución principal y documentar datos/semillas usados |
| Migración | Revisar rollback, compatibilidad y datos existentes |
| Código generado | No editar a mano salvo capa wrapper; revisar fuente generadora |
| Hotfix urgente | Micro-spec mínima, fix aislado, review posterior obligatoria |
| Prototipo | Marcar como no productivo y abrir deuda antes de integrarlo |

Una excepción debe quedar escrita en la spec, micro-spec o resultados de revisión.

### 14.6 Triggers Para ADR

Crear o actualizar un ADR cuando el cambio:

- Introduce una dependencia relevante.
- Cambia arquitectura, límites de módulos o patrón principal.
- Cambia base de datos, esquema, almacenamiento o cola.
- Afecta autenticación, autorización, seguridad o privacidad.
- Cambia estrategia de deploy, observabilidad o configuración global.
- Introduce una decisión difícil de revertir.
- Acepta una deuda técnica importante con trade-off explícito.

Formato mínimo de ADR:

```text
# ADR-[número]: [decisión]

Contexto: [situación y restricciones]
Decisión: [qué se decide]
Alternativas: [opciones consideradas]
Consecuencias: [costes, riesgos y beneficios]
Estado: propuesto | aceptado | reemplazado
```

### 14.7 Reglas Globales

1. No escribir código sin spec aprobada.
2. No hardcodear secrets ni credenciales.
3. No usar `except: pass`.
4. No usar `except Exception` sin manejo específico, logging útil o re-raise.
5. No mergear con tests fallando.
6. No mergear con cobertura inferior a 80% salvo excepción documentada.
7. Preguntar dudas antes de implementar si el requisito es ambiguo.
8. Verificar que código nuevo no rompe lo existente.
9. Usar commits convencionales: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`, `perf:`.
10. No usar `--no-verify` ni saltarse hooks pre-commit.

---

## 15. Definición De Hecho

Una tarea se considera terminada cuando:

- La spec está aprobada o el cambio tiene alcance explícitamente documentado.
- El código está implementado con tests relevantes.
- `ruff check .` pasa.
- `pytest` pasa.
- Los resultados de revisión están documentados.
- La deuda técnica restante está priorizada.
- README, CHANGELOG o ADRs están actualizados si el cambio afecta uso, instalación o arquitectura.

---

*Superarchivo unificado. Actualizar este documento cuando el equipo adopte nuevas convenciones.*
