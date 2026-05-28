# Documento Maestro - equilibria

## Estado Actual
Aplicación web Flask para gestión de práctica terapéutica. Actualmente no funcional debido a dependencias faltantes y bugs críticos identificados.

## Bugs Encontrados
- [x] **Dependencia Flask no instalada**: Error `ModuleNotFoundError: No module named 'flask'` - Prioridad [Alta] - **RESUELTO** (Instalado Flask 3.1.3)
- [x] **Bare except en migrar_datos.py**: Línea 24 `except:` sin especificar tipo de excepción - Prioridad [Alta] - **RESUELTO** (Corregido con `except (ValueError, TypeError)`)
- [ ] **Import dinámico de uuid**: Importado dentro de funciones en lugar de al nivel de módulo - Prioridad [Media] - **NO ES PROBLEMA** (uuid se importa correctamente en migrar_datos.py)
- [ ] **Falta de manejo de errores**: Operaciones de archivo sin manejo de errores adecuados - Prioridad [Media]
- [ ] **Sin tests unitarios**: No hay pruebas para validar funcionalidad - Prioridad [Baja] - **PARCIALMENTE RESUELTO** (Creado tests/test_app.py con 2/5 tests pasando)

## Deudas Técnicas
- [x] **Sin archivo de dependencias**: Falta requirements.txt o pyproject.toml - Impacto [Crítico] - **RESUELTO** (Creado requirements.txt)
- [ ] **Sin estructura de tests**: No hay directorio de pruebas - Impacto [Importante] - **PARCIALMENTE RESUELTO** (Creado tests/ con tests básicos)
- [ ] **Código sin linting**: No se ha analizado con herramientas de calidad - Impacto [Importante]
- [ ] **Documentación incompleta**: Falta documentación de API y uso - Impacto [Moderado]
- [ ] **No maneja concurrencia**: Posibles problemas con acceso simultáneo a datos - Impacto [Moderado]

## Plan de Acción
- [x] Paso 1: Instalar dependencias (Flask, uuid) - **COMPLETADO**
- [x] Paso 2: Corregir bare except en migrar_datos.py - **COMPLETADO**
- [x] Paso 3: Mover import de uuid al nivel de módulo - **NO NECESARIO** (uuid ya está bien importado)
- [ ] Paso 4: Agregar manejo de errores en operaciones de archivo
- [x] Paso 5: Crear archivo requirements.txt - **COMPLETADO**
- [ ] Paso 6: Implementar tests unitarios básicos - **PARCIALMENTE COMPLETADO** (Creados tests básicos)
- [ ] Paso 7: Agregar linting con ruff
- [ ] Paso 8: Documentar API y endpoints

## Progreso
- [x] **PROGRESO SIGNIFICATIVO LOGRADO** ✅
- [x] Bugs Resueltos: 2/5 (2 resueltos, 3 pendientes)
- [x] Deudas Resueltas: 1/5 (1 resuelta, 4 pendientes)
- [x] Tests: 2/5 pasando (API endpoints funcionan, faltan plantillas HTML)

## Última Actualización
2026-05-27 03:15:00 CEST - **PROGRESO SIGNIFICATIVO: Dependencias instaladas, bare except corregido, requirements.txt creado, tests básicos implementados (2/5 tests pasando)**