#!/bin/bash

# Script de análisis de debugging para proyectos
# Realiza las 4 pasadas del análisis de código

echo "=== INICIANDO ANÁLISIS PROFUNDO DE PROYECTOS ==="
echo "Directorio: $(pwd)"
echo "Fecha: $(date)"
echo

# Pass 1: Análisis de pruebas
echo "=== PASO 1: ANÁLISIS DE PRUEBAS ==="
test_count=$(find . -name "test_*.py" -o -name "*_test.py" -o -name "conftest.py" | wc -l)
echo "Archivos de prueba encontrados: $test_count"

# Ejecutar pytest si está disponible
if command -v pytest &> /dev/null; then
    echo "Ejecutando pytest..."
    pytest tests/ -q --tb=short 2>&1 | head -20
else
    echo "pytest no disponible, omitiendo análisis detallado de pruebas"
fi
echo

# Pass 2: Análisis estático
echo "=== PASO 2: ANÁLISIS ESTÁTICO ==="
python_count=$(find . -name "*.py" -not -path "././*" | wc -l)
echo "Archivos Python analizados: $python_count"

# Buscar errores de sintaxis
echo "Buscando errores de sintaxis..."
syntax_errors=0
for file in $(find . -name "*.py" -not -path "././*" 2>/dev/null); do
    python -m py_compile "$file" 2>/dev/null || {
        echo "ERROR DE SINTAXIS en $file"
        ((syntax_errors++))
    }
done
echo "Errores de sintaxis encontrados: $syntax_errors"
echo

# Pass 3: Búsqueda de patrones de bugs
echo "=== PASO 3: BÚSQUEDA DE PATRONES DE BUGS ==="
echo "Buscando patrones de bugs..."

bare_excepts=$(grep -r "except:" . --include="*.py" 2>/dev/null | wc -l)
hardcoded_paths=$(grep -r "/Users/\|/home/" . --include="*.py" 2>/dev/null | wc -l)
open_without_with=$(grep -r "open(" . --include="*.py" 2>/dev/null | grep -v "with open(" | wc -l)

echo "Patrones encontrados:"
echo "  - bare excepts: $bare_excepts"
echo "  - hardcoded paths: $hardcoded_paths" 
echo "  - open() sin with: $open_without_with"
echo

# Pass 4: Análisis de dependencias
echo "=== PASO 4: ANÁLISIS DE DEPENDENCIAS ==="
if [ -f requirements.txt ]; then
    echo "Archivo requirements.txt encontrado"
    if command -v pip &> /dev/null; then
        echo "Verificando dependencias..."
        pip check 2>&1 | head -10
    fi
else
    echo "No se encontró requirements.txt"
fi

if [ -f pyproject.toml ]; then
    echo "Archivo pyproject.toml encontrado"
fi

echo
echo "=== RESUMEN FINAL ==="
echo "Total de archivos Python: $python_count"
echo "Errores de sintaxis: $syntax_errors"
echo "Patrones de bugs potenciales: $((bare_excepts + hardcoded_paths + open_without_with))"
echo "Archivos de prueba: $test_count"

if [ $syntax_errors -gt 0 ]; then
    echo "⚠️  RECOMENDACIÓN: Corregir errores de sintaxis antes de continuar"
fi

echo "Análisis completado el $(date)"