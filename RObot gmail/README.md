# Gmail Bulk Trash

Herramienta CLI para limpiar masivamente el correo de Gmail con gestión persistente de blocklist, whitelist y filtros avanzados.

## 🚀 Características

- **Blocklist/Whitelist persistente**: Gestiona remitentes bloqueados y protegidos en `senders.json`
- **Filtros dinámicos**: Query personalizada, filtros por fecha (`--before`, `--after`)
- **Modo dry-run**: Simula sin borrar nada
- **Barra de progreso**: Con ETA calculada dinámicamente
- **Auto-instalación**: Instala automáticamente dependencias necesarias

## 📋 Requisitos

- Python 3.10+
- Cuenta Google con Gmail habilitado
- Google Cloud project con Gmail API configurada

## ⚙️ Setup

### Paso 1: Configurar Google Cloud Console

1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un proyecto nuevo o usa uno existente
3. Habilita **Gmail API**
4. Crea credenciales → OAuth 2.0 Client ID → Desktop app
5. Descarga `credentials.json` y colócalo en la misma carpeta que el script

### Paso 2: Primeros comandos

```bash
# Ver ayuda
python3 gmail_bulk_trash.py --help

# Simular limpieza (sin borrar)
python3 gmail_bulk_trash.py --dry-run

# Agregar remitentes no deseados
python3 gmail_bulk_trash.py --add-sender spam@example.com newsletter@ads.com

# Ver blocklist y whitelist
python3 gmail_bulk_trash.py --list-senders

# Proteger remitentes importantes
python3 gmail_bulk_trash.py --add-whitelist banco@mybank.com

# Limpiar correos
python3 gmail_bulk_trash.py --dry-run          # Revisar primero
python3 gmail_bulk_trash.py                    # Ejecutar
```

## 🎯 Comandos

### Gestión de remitentes

```bash
python3 gmail_bulk_trash.py --add-sender EMAIL [EMAIL ...]
python3 gmail_bulk_trash.py --remove-sender EMAIL [EMAIL ...]
python3 gmail_bulk_trash.py --add-whitelist EMAIL [EMAIL ...]
python3 gmail_bulk_trash.py --remove-whitelist EMAIL [EMAIL ...]
python3 gmail_bulk_trash.py --list-senders
```

### Filtros de búsqueda

```bash
python3 gmail_bulk_trash.py --query "QUERY_GMAIL"     # Query personalizada
python3 gmail_bulk_trash.py --before 2024-01-01       # Emails anteriores a fecha
python3 gmail_bulk_trash.py --after 2023-01-01        # Emails posteriores a fecha
python3 gmail_bulk_trash.py --dry-run                 # Simular sin borrar
```

### Ejemplos

```bash
# Borrar promociones anteriores a 2024
python3 gmail_bulk_trash.py --query "category:promotions" --before 2024-01-01 --dry-run

# Borrar todos los remitentes en blocklist
python3 gmail_bulk_trash.py --dry-run

# Rango de fechas
python3 gmail_bulk_trash.py --after 2023-01-01 --before 2023-12-31
```

## 📁 Archivos

- `gmail_bulk_trash.py` — Script principal
- `senders.json` — Blocklist y whitelist (se crea automáticamente)
- `credentials.json` — OAuth2 credentials (descargar de Google Cloud)
- `token.json` — Token de sesión (se genera automáticamente, NO subir a git)

## 🔐 Seguridad

- ✅ Los correos van a la **papelera** (recuperables durante 30 días), no se eliminan permanentemente
- ✅ El script solo usa scope `gmail.modify` (no puede leer cuerpos de emails)
- ⚠️ **NUNCA** subas `credentials.json` o `token.json` a git

## 🧪 Tests

```bash
python3 tests/test_senders.py   # Ejecutar tests manualmente
pytest tests/ -v                # Usar pytest (requiere instalación)
```

## 📖 Documentación completa

Ver [`documentos/documento_maestro_gmail_bulk_trash.md`](documentos/documento_maestro_gmail_bulk_trash.md) para arquitectura, decisiones de diseño y más detalles.

## 📝 Licencia

Proyecto local — sin licencia específica.
