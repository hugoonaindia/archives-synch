# Archivex Sync

Sincroniza automáticamente citas de **Google Calendar** a **Archivex Clinical** (macOS) usando automatización de interfaz de usuario.

## Características

✅ Lee citas de Google Calendar para la semana actual
✅ Selecciona qué días sincronizar antes de ejecutar
✅ Detección de conflictos: avisa si un slot ya está ocupado
✅ Logging completo: historial en `~/.config/archivex-sync/archivex_sync.log`
✅ Seguro: credenciales en `~/.config` (no tracked en git)

## Requisitos previos

- **macOS** (requiere AppleScript y `osascript`)
- **Python 3.9+**
- **Archivex Clinical** abierto en vista SEMANAL
- **Google Cloud OAuth**: archivo `credentials.json` (ver [Google Cloud Console](https://console.cloud.google.com))
- **Terminal debe tener permisos de Accesibilidad**:
  - Preferencias del Sistema → Privacidad y Seguridad → Accesibilidad → ✓ Terminal

## Instalación

```bash
# 1. Clonar o descargar el proyecto
cd archivex-sync

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Poner credentials.json en la carpeta raíz
# (descargarlo desde Google Cloud Console)

# 4. (Primera ejecución) Autorizar Google Calendar
python archivex_sync.py
# → Abrirá navegador para autenticar con Google
# → Se guardará token en ~/.config/archivex-sync/
```

## Uso

```bash
python archivex_sync.py
```

### Flujo de ejecución:

1. **Conecta con Google Calendar**
2. **Muestra citas de esta semana** agrupadas por día
3. **Te pide seleccionar** qué días sincronizar (ej: `1,3` para lunes y miércoles)
4. **Verifica permisos y que Archivex esté abierto**
5. **Inicia automatización** (mueve ratón/teclado)
6. **Guarda log** en `~/.config/archivex-sync/archivex_sync.log`

### Abortando la ejecución

Mueve el ratón a la **esquina superior izquierda** en cualquier momento para abortar.

## Configuración de calibración

Si los clics no dan en el sitio correcto, ajusta los valores en `archivex_sync.py`:

```python
CAL = {
    "grid_top_px":    135,      # píxeles desde top hasta grid
    "grid_bottom_px": 145,      # píxeles desde bottom
    "time_col_px":    65,       # ancho columna de horas
    "search_box_x":   0.245,    # posición buscador (proporción)
    "search_box_y":   0.525,
    "crear_btn_x":    0.75,     # botón "+ Crear cita"
    "crear_btn_y":    0.87,
    # ... más valores
}
```

## Logging

```bash
# Ver logs en tiempo real
tail -f ~/.config/archivex-sync/archivex_sync.log

# Formato: [TIMESTAMP] STATUS | PACIENTE | FECHA HORA | NOTA
# [2024-01-15 10:30:45] CREADA  | John Doe                  | 15/01/2024 10:00-11:00
# [2024-01-15 10:31:12] SALTADA | Jane Smith                | 15/01/2024 11:00-12:00 | conflicto detectado
```

## Seguridad

- **Tokens Google** se guardan en `~/.config/archivex-sync/` (permisos 0600)
- **`credentials.json` debe estar en la raíz del proyecto**
- **`.gitignore` bloquea commit accidental de credenciales**

⚠️ Si leakeaste credenciales:
1. Elimina tokens: `rm ~/.config/archivex-sync/token_*.json`
2. Regenera credenciales en Google Cloud Console

## Testing

```bash
# Ejecutar tests
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=. --cov-report=html

# Ver reporte HTML
open htmlcov/index.html
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: No module named 'pyautogui'` | `pip install -r requirements.txt` |
| "No pude detectar la ventana de Archivex" | Haz clic en la ventana de Archivex antes de pulsar ENTER |
| Los clics no dan en el sitio correcto | Ajusta valores en sección `CAL` (calibración) |
| "❌ No se encontró credentials.json" | Descárgalo desde [Google Cloud Console](https://console.cloud.google.com) |
| Terminal sin permisos de Accesibilidad | Preferencias del Sistema → Privacidad → Accesibilidad → ✓ Terminal |

## Licencia

MIT

## Contacto

Para issues o sugerencias: [crear issue](https://github.com/tu-usuario/archivex-sync/issues)
