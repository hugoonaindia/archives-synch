#!/bin/bash
# Script para ejecutar el trader usando el entorno virtual
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
"$DIR/.venv/bin/python" "$DIR/app_customtkinter_simple.py"