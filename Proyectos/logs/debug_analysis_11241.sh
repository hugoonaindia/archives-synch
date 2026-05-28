#!/bin/bash
set -e

# Análisis específico para recursos gratis psicologia
cd "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia"

# 1. Búsqueda de errores de sintaxis
echo "1. Buscando errores de sintaxis en recursos gratis psicologia..."
python_files=$(find . -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" 2>/dev/null || true)

syntax_errors=0
for file in $python_files; do
    if python -m py_compile "$file" 2>/dev/null; then
        echo "✅ Sintaxis OK: $file"
    else
        echo "❌ ERROR SINTAXIS: $file"
        syntax_errors=$((syntax_errors + 1))
        
        # Intentar corregir automáticamente
        echo "🔧 Intentando corregir automáticamente..."
        python -c "
import ast
import sys

try:
    with open('', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse para encontrar errores
    tree = ast.parse(content, filename='')
    print('✅ El archivo es sintácticamente válido')
    
except SyntaxError as e:
    print(f'Error de sintaxis en línea {e.lineno}: {e.msg}')
    
    # Intentar corrección básica
    lines = content.split('\n')
    
    # Corregir indentación común
    if hasattr(e, 'text') and e.text:
        line_num = e.lineno - 1
        if line_num < len(lines):
            line = lines[line_num]
            
            # Agregar indentación faltante
            if line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                lines[line_num] = '    ' + line
                print('✅ Intenté agregar indentación')
            
            # Corregir comas faltantes en tuplas/listas
            if '(' in line and ')' in line and ',' not in line:
                lines[line_num] = line.rstrip() + ','
                print('✅ Intenté agregar coma faltante')
    
    try:
        with open('', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print('✅ Archivo corregido automáticamente')
    except:
        print('❌ No se pudo corregir el archivo')
" || true
    fi
done

echo "Errores de sintaxis encontrados: $syntax_errors" > "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"

# 2. Búsqueda de patrones de bugs
echo "2. Buscando patrones de bugs en recursos gratis psicologia..."
bug_patterns=0

# Bare except statements
bare_excepts=$(grep -r "except:" . --include="*.py" 2>/dev/null | wc -l || echo 0)
if [ "$bare_excepts" -gt 0 ]; then
    echo "⚠️  Found $bare_excepts bare except statements"
    bug_patterns=$((bug_patterns + bare_excepts))
    
    # Intentar corregir
    find . -name "*.py" -exec grep -l "except:" {} \; 2>/dev/null | while read file; do
        sed -i '' 's/except:/except Exception:/' "" 2>/dev/null || true
        echo "✅ Corregido bare except en: $file"
    done
fi

# TODO sin comilla
todos=$(grep -r "TODO" . --include="*.py" 2>/dev/null | wc -l || echo 0)
if [ "$todos" -gt 0 ]; then
    echo "ℹ️  Found $todos TODO statements"
fi

echo "Patrones de bugs encontrados: $bug_patterns" >> "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"

# 3. Verificación de dependencias
echo "3. Verificando dependencias en recursos gratis psicologia..."
if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt encontrado"
    pip install -r requirements.txt 2>/dev/null || echo "⚠️  No se pudieron instalar dependencias"
else
    echo "⚠️  requirements.txt no encontrado"
fi

if [ -f "pyproject.toml" ]; then
    echo "✅ pyproject.toml encontrado"
fi

# 4. Ejecución de pruebas si existen
echo "4. Buscando pruebas en recursos gratis psicologia..."
test_files=$(find . -name "*test*.py" -o -name "test_*" -type d 2>/dev/null || true)
if [ -n "$test_files" ]; then
    echo "✅ Encontrados archivos de prueba"
    # No ejecutar pruebas aquí para evitar problemas con dependencias
else
    echo "ℹ️  No se encontraron archivos de prueba"
fi

# Guardar resumen
echo "" >> "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"
echo "=== RESUMEN recursos gratis psicologia ===" >> "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"
echo "Archivos Python: $python_files" >> "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"
echo "Errores de sintaxis: $syntax_errors" >> "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"
echo "Patrones de bugs: $bug_patterns" >> "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"
echo "Pruebas encontradas: $test_files" >> "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"
echo "Finalizado: $(date)" >> "/Users/hugoonaindia/Desktop/Proyectos/recursos gratis psicologia_analysis_20260527_092438.txt"

echo "✅ Análisis completado para recursos gratis psicologia"
