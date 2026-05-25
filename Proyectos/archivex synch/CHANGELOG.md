# Changelog

Todos los cambios notables en este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

### Added
- ✅ Sincronización automática de Google Calendar → Archivex Clinical
- ✅ Detección de conflictos con captura de pantalla
- ✅ Selección interactiva de días antes de sincronizar
- ✅ Logging estructurado a archivo
- ✅ Tests unitarios con pytest
- ✅ Documentación completa (README, docstrings)
- ✅ Configuración segura: credenciales en `~/.config`

### Changed
- 🔧 Refactorizado: extracción de función `calc_grid_metrics()` para eliminar duplicación
- 🔧 Mejorado: uso de clipboard (`pbcopy`) para caracteres especiales (acentos)
- 🔧 Mejorado: timezone dinámico (`datetime.now().astimezone()`) en lugar de hardcoded `+02:00`
- 🔧 Mejorado: logging centralizado con `logging` module (ya no archivo manual)

### Fixed
- 🐛 Seguridad: tokens Google almacenados en `~/.config` (no en repo)
- 🐛 Seguridad: `.gitignore` añadido para evitar commit accidental de credenciales
- 🐛 Corrección: parseado robusto de bounds de ventana con mejor manejo de errores
- 🐛 Corrección: validación de grid_metrics en edge cases (inicio/fin de día)

### Removed
- ❌ Auto-instalación de dependencias (reemplazada por `requirements.txt`)
- ❌ Hardcoding de timezone `+02:00`

### Security
- 🔒 Credenciales nunca se comitean (`.gitignore`)
- 🔒 Tokens guardados con permisos restringidos (`~/.config`)
- 🔒 Mejor logging sin exposición de datos sensibles

---

## Notas futuras

### Planeado para v1.1
- [ ] Soporte para múltiples calendarios
- [ ] Configuración en archivo `.env`
- [ ] Docker support
- [ ] CI/CD con GitHub Actions

### Consideraciones
- Los magic numbers en `is_slot_occupied()` (variance > 300, mean < 220) pueden necesitar ajuste según tema UI de Archivex
- Timezone se detecta automáticamente; verificar comportamiento en diferentes regiones y durante DST
