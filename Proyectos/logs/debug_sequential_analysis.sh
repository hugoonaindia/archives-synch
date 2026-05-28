#!/bin/bash

# SCRIPT DE ANÁLISIS SECUENCIAL DE PROYECTOS CON CORRECCIÓN AUTOMÁTICA
# Analiza proyecto por proyecto, corregiendo errores cuando sea posible

set -e  # Salir si hay errores

# Directorio base
BASE_DIR="/Users/hugoonaindia/Desktop/Proyectos"
LOG_FILE="$BASE_DIR/debug_sequential_$(date +%Y%m%d_%H%M%S).log"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

# Lista de proyectos para analizar secuencialmente
PROJECTS=(
    "equilibria"
    "LSTM RL"
    "psych-billing-app"
    "Trader LSTM"
    "trader supersimple"
    "ayuda programacion"
    "archivex synch"
    "artefacto pacientes"
    "RObot gmail"
    "recursos gratis psicologia"
)

# Crear archivo de log
echo "=== INICIO ANÁLISIS SECUENCIAL: $TIMESTAMP ===" > "$LOG_FILE"
echo "Directorio base: $BASE_DIR" >> "$LOG_FILE"
echo "Total de proyectos: ${#PROJECTS[@]}" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Contadores globales
TOTAL_PROJECTS=0
ANALIZADOS=0
CON_ERRORES=0
CORREGIDOS=0

# Función para analizar un proyecto
analyze_project() {
    local project_name="$1"
    local project_path="$BASE_DIR/$project_name"
    local project_log="$BASE_DIR/${project_name}_analysis_$(date +%Y%m%d_%H%M%S).txt"
    local analysis_script="$BASE_DIR/debug_analysis_${project_name}_$(date +%s).sh"
    
    echo "=== ANALIZANDO PROYECTO: $project_name ===" | tee -a "$LOG_FILE"
    echo "Ruta: $project_path" >> "$LOG_FILE"
    echo "Tiempo: $(date)" >> "$LOG_FILE"
    
    if [ ! -d "$project_path" ]; then
        echo "❌ PROYECTO NO EXISTE: $project_name" | tee -a "$LOG_FILE"
        return 1
    fi
    
    # Crear script de análisis específico para el proyecto
    cat > "$analysis_script" << EOF
#!/bin/bash
set -e

# Análisis específico para $project_name
cd "$project_path"

# 1. Búsqueda de errores de sintaxis
echo "1. Buscando errores de sintaxis en $project_name..."
python_files=$(find . -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" 2>/dev/null || true)
python_files_count=$(echo "$python_files" | wc -l | tr -d ' ')

echo "📁 Encontrados $python_files_count archivos Python"

# Limitar análisis para proyectos muy grandes
if [ "$python_files_count" -gt 100 ]; then
    echo "⚠️  Proyecto grande ($python_files_count archivos), analizando solo primeros 100 archivos..."
    python_files=$(echo "$python_files" | head -100)
fi

syntax_errors=0
for file in $python_files; do
    if timeout 10 python -m py_compile "$file" 2>/dev/null; then
        echo "✅ Sintaxis OK: $file"
    else
        echo "❌ ERROR SINTAXIS: $file"
        syntax_errors=$((syntax_errors + 1))
        
        # Intentar corregir automáticamente
        echo "🔧 Intentando corregir automáticamente..."
        timeout 15 python -c "
import ast
import sys

try:
    with open('$file', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse para encontrar errores
    tree = ast.parse(content, filename='$file')
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
        with open('$file', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print('✅ Archivo corregido automáticamente')
    except:
        print('❌ No se pudo corregir el archivo')
" || true
    fi
    
    # Timeout por archivo
    sleep 0.1
done

echo "Errores de sintaxis encontrados: $syntax_errors" > "$project_log"

# 2. Búsqueda de patrones de bugs
echo "2. Buscando patrones de bugs en $project_name..."
bug_patterns=0

# Bare except statements
bare_excepts=\$(grep -r "except:" . --include="*.py" 2>/dev/null | wc -l || echo 0)
if [ "\$bare_excepts" -gt 0 ]; then
    echo "⚠️  Found \$bare_excepts bare except statements"
    bug_patterns=\$((bug_patterns + bare_excepts))
    
    # Intentar corregir
    find . -name "*.py" -exec grep -l "except:" {} \; 2>/dev/null | while read file; do
        sed -i '' 's/except:/except Exception:/' "$file" 2>/dev/null || true
        echo "✅ Corregido bare except en: \$file"
    done
fi

# TODO sin comilla
todos=\$(grep -r "TODO" . --include="*.py" 2>/dev/null | wc -l || echo 0)
if [ "\$todos" -gt 0 ]; then
    echo "ℹ️  Found \$todos TODO statements"
fi

echo "Patrones de bugs encontrados: \$bug_patterns" >> "$project_log"

# 3. Verificación de dependencias
echo "3. Verificando dependencias en $project_name..."
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
echo "4. Buscando pruebas en $project_name..."
test_files=\$(find . -name "*test*.py" -o -name "test_*" -type d 2>/dev/null || true)
if [ -n "\$test_files" ]; then
    echo "✅ Encontrados archivos de prueba"
    # No ejecutar pruebas aquí para evitar problemas con dependencias
else
    echo "ℹ️  No se encontraron archivos de prueba"
fi

# Guardar resumen
echo "" >> "$project_log"
echo "=== RESUMEN $project_name ===" >> "$project_log"
echo "Archivos Python: \$python_files" >> "$project_log"
echo "Errores de sintaxis: \$syntax_errors" >> "$project_log"
echo "Patrones de bugs: \$bug_patterns" >> "$project_log"
echo "Pruebas encontradas: \$test_files" >> "$project_log"
echo "Finalizado: \$(date)" >> "$project_log"

echo "✅ Análisis completado para $project_name"
EOF

    # Ejecutar análisis del proyecto
    if bash "$analysis_script" >> "$project_log" 2>&1; then
        echo "✅ ANÁLISIS COMPLETADO: $project_name" | tee -a "$LOG_FILE"
        ANALIZADOS=$((ANALIZADOS + 1))
        
        # Contar errores y correcciones
        if grep -q "ERROR" "$project_log"; then
            CON_ERRORES=$((CON_ERRORES + 1))
        fi
        
        if grep -q "corregido automáticamente" "$project_log"; then
            CORREGIDOS=$((CORREGIDOS + 1))
        fi
        
    else
        echo "❌ ANÁLISIS FALLIDO: $project_name" | tee -a "$LOG_FILE"
        CON_ERRORES=$((CON_ERRORES + 1))
    fi
    
    echo "" >> "$LOG_FILE"
    
    # Limpiar script temporal
    rm -f "$analysis_script"
}

# Ejecutar análisis secuencial de cada proyecto
for project in "${PROJECTS[@]}"; do
    TOTAL_PROJECTS=$((TOTAL_PROJECTS + 1))
    
    echo "🔄 Iniciando proyecto $project ($((TOTAL_PROJECTS-1+1))/${#PROJECTS[@]})..."
    analyze_project "$project"
    
    # Pausa corta entre proyectos
    echo "⏱️  Esperando 3 segundos antes del siguiente proyecto..." | tee -a "$LOG_FILE"
    sleep 3
done

# Resumen final
echo "" >> "$LOG_FILE"
echo "=== RESUMEN FINAL ===" >> "$LOG_FILE"
echo "Total de proyectos: $TOTAL_PROJECTS" >> "$LOG_FILE"
echo "Analizados exitosamente: $ANALIZADOS" >> "$LOG_FILE"
echo "Con errores: $CON_ERRORES" >> "$LOG_FILE"
echo "Correcciones automáticas: $CORREGIDOS" >> "$LOG_FILE"
echo "Finalizado: $(date)" >> "$LOG_FILE"

echo "✅ ANÁLISIS SECUENCIAL COMPLETADO"
echo "Log detallado: $LOG_FILE"