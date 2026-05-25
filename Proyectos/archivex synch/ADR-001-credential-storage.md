# ADR-001: Almacenamiento seguro de credenciales Google

**Status**: Accepted
**Date**: 2024-01-15
**Author**: Archivex Sync Team

## Context

El script necesita autenticar con Google Calendar API usando OAuth2. Las credenciales (tokens) se generan en la primera ejecución y necesitan ser persistidas para futuras ejecuciones.

**Problema**: ¿Dónde guardar los tokens de forma segura?

## Options Considered

### 1. En el directorio del script (RECHAZADO)
```python
TOKEN_FILE = Path(__file__).parent / "token_archivex.json"
```
**Pros**: Simple, sin dependencias
**Cons**: ⚠️ **RIESGO**: Si repo se leakea, tokens están expuestos; fácil comitear accidentalmente

### 2. En `~/.config/archivex-sync/` (ACEPTADO)
```python
CONFIG_DIR = Path.home() / ".config" / "archivex-sync"
TOKEN_FILE = CONFIG_DIR / "token_archivex.json"
```
**Pros**:
- Estándar en Unix/macOS (`~/.config` es convención XDG)
- Separación: datos privados ≠ código fuente
- `.gitignore` hace imposible comitear accidentalmente
- Permisos del sistema (`chmod 600`) protegen el archivo

**Cons**: Requiere crear directorio

### 3. Sistema de Keychain macOS (DESCARTADO)
```python
import keyring
token = keyring.get_password("archivex", "google_token")
```
**Pros**: Máxima seguridad (encriptado por SO)
**Cons**: Dependencia externa, complejo, requiere UI prompt cada run

## Decision

**Guardar tokens en `~/.config/archivex-sync/`**

Razones:
1. **Seguridad razonable**: Protegido por permisos del filesystem
2. **Portabilidad**: Funciona en macOS, Linux, WSL
3. **Simplicidad**: Sin dependencias extra (vs Keychain)
4. **Convención estándar**: XDG Base Directory especifica `~/.config`

## Implementation

```python
CONFIG_DIR = Path.home() / ".config" / "archivex-sync"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
TOKEN_FILE = CONFIG_DIR / "token_archivex.json"
```

## Consequences

### Positivas
- ✅ Tokens nunca en repo
- ✅ Cada máquina tiene sus propios tokens
- ✅ Fácil de limpiar: `rm -rf ~/.config/archivex-sync`

### Negativas
- ❌ Usuario debe dar permisos a Terminal (Accesibilidad)
- ❌ Si `credentials.json` se leakea, tokens se pueden regenerar pero es molesto

## Related

- `.gitignore`: Bloquea `token_*.json` y `credentials.json`
- README: Instruye cómo regenerar credenciales si se comprometen

## References

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [Google OAuth 2.0 - Storing Tokens](https://developers.google.com/identity/protocols/oauth2)
