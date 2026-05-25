# ADR-002: argparse (stdlib) vs Click/Typer for CLI

## Status
✅ ACCEPTED

## Context
Se necesitaba un framework CLI para manejar 9+ argumentos (--add-sender, --remove-sender, etc.). Opciones:
1. **argparse** (elegida) — stdlib
2. Click — tercera dependencia
3. Typer — tercera dependencia

## Decision
Usar `argparse` del stdlib de Python.

## Rationale
- **Sin dependencias extra**: Click/Typer requieren instalación adicional; argparse viene con Python 3.x
- **Suficiencia**: argparse cubre todos los casos de uso (nargs, metavar, epilog con ejemplos)
- **Familiaridad**: Estándar de la industria en Python CLI
- **Tamaño de distribución**: Script standalone sin dependencias externas

## Consequences
### Positivos
- Script totalmente standalone (copia a otro máquina y funciona)
- Mantenimiento a largo plazo (argparse no desaparece)
- Menos surficial attack (menos código de terceros)

### Negativos
- Sintaxis más verbosa vs Click/Typer (pero manejable)
- Sin decoradores @click.command() (más código imperativo)
- Menos "mágico" (requiere más escritura manual)

## Code Example
```python
# argparse (actual)
parser = argparse.ArgumentParser(epilog="Ejemplos...")
parser.add_argument("--add-sender", nargs="+", help="...")
args = parser.parse_args()

# Click (alternativa)
@click.command()
@click.option('--add-sender', multiple=True)
def main(add_sender):
    ...
```

La diferencia es tolerable para una CLI de tamaño medio.

## Alternative Considered
**Click**: Más elegante, pero requiere `pip install click` en máquinas nuevas. Overhead injustificado para CLI pequeña.

---

**Decision Date**: 2026-05-25
**Reviewed By**: SUPERREVISION PASADA 3
