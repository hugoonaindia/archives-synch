#!/bin/bash
# Script mejorado pero simple para ejecutar el trader

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activar entorno virtual
if [ -d "$DIR/.venv" ]; then
    echo "Activando entorno virtual..."
    source "$DIR/.venv/bin/activate"
fi

# Ejecutar versión mejorada y simplificada
echo "Iniciando Trader LSTM versión mejorada y simplificada..."
cd "$DIR"
python -m src.simple_main

echo "Trader finalizado."