# 🏛️ Documento Maestro de Ingeniería

## 1. Contexto del Sistema
- **Dominio**: Desarrollo de plataforma de gestión / automatización.
- **Stack Tecnológico**: Python 3.12+, NiceGUI para la capa de presentación, SQLite (modo WAL), y modelos LLM locales.
- **Filosofía de Diseño**: Minimalismo funcional. Interfaz "Premium" con micro-interacciones sutiles y tipografía limpia.
- **Seguridad y Privacidad**: Aislamiento estricto de datos. Las consultas a LLMs locales (ej. OpenClaw, DeepSeek) no deben exponer información sensible en logs.

## 2. Estándares de Arquitectura
- **Separación de Responsabilidades (SoC)**: La lógica de negocio (`services/`), el acceso a datos (`repositories/` o `models/`) y la interfaz de usuario (`ui/` componentes NiceGUI) deben estar estrictamente desacoplados.
- **Manejo de Estado**: Centralizado y predecible. Evitar variables globales mutables.
- **Tipado**: Cobertura del 100% con *Type Hints* de Python (`mypy` compliant).

## 3. Protocolo de Iteración (The AI Loop)
El trabajo se ejecuta de forma secuencial y atómico. Está estrictamente prohibido mantener más de una feature en `in-progress` simultáneamente.

1. **Sincronización Inicial**: Leer `progress.json` para cargar el contexto, identificar el `handoff` previo y la tarea activa.
2. **Validación Pre-vuelo**: Ejecutar el script de inicialización/tests (`bash init.sh` o equivalente) para asegurar un entorno limpio.
3. **Ejecución**: Escribir código adherido a los estándares de la Sección 2.
4. **Cierre de Ciclo**: Todo cambio debe estar respaldado por la actualización del estado en `progress.json`.

## 4. Universal Definition of Done (DoD)
Una tarea solo puede cambiar a `done` en el JSON si cumple estos criterios universales, además de los suyos propios:
- [ ] El linter (`ruff`) pasa con 0 advertencias.
- [ ] Los tests unitarios del módulo modificado se ejecutan con éxito.
- [ ] El código está documentado usando el estándar de Google para docstrings.
- [ ] Se ha generado un commit atómico siguiendo *Conventional Commits* (ej. `feat(ui): implement premium dark mode`).