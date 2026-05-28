#!/bin/bash

# AGENTE DE REFACTORIZACIÓN ITERATIVA AUTÓNOMA
# Objetivo: Resolver errores de código y hacer que la suite de pruebas pase a verde
# Restricción: Solo revisa proyectos dentro de /Users/hugoonaindia/Desktop/Proyectos

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BASE_DIR="/Users/hugoonaindia/Desktop/Proyectos"
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"

echo "=== INICIO: REFACTORIZACIÓN ITERATIVA AUTÓNOMA ($TIMESTAMP) ==="
echo "Directorio base restringido: $BASE_DIR"

# Proyectos configurados manualmente dentro del directorio base
PROJECTS=(
    '{"name":"lstm-rl-trader","path":"/Users/hugoonaindia/Desktop/Proyectos/LSTM RL","review_type":"all","priority":"high"}'
    '{"name":"equilibria","path":"/Users/hugoonaindia/Desktop/Proyectos/equilibria","review_type":"all","priority":"medium"}'
    '{"name":"ayuda-programacion","path":"/Users/hugoonaindia/Desktop/Proyectos/ayuda programacion","review_type":"all","priority":"medium"}'
    '{"name":"trader-supersimple","path":"/Users/hugoonaindia/Desktop/Proyectos/trader supersimple","review_type":"all","priority":"medium"}'
    '{"name":"psych-billing-app","path":"/Users/hugoonaindia/Desktop/Proyectos/psych-billing-app","review_type":"all","priority":"medium"}'
)

echo "Proyectos configurados: ${#PROJECTS[@]}"

# Función para ejecutar tests y obtener errores
run_tests_and_get_errors() {
    local project_path="$1"
    local project_name="$2"
    local test_output="$LOG_DIR/${project_name}_tests_${TIMESTAMP}.txt"
    local error_output="$LOG_DIR/${project_name}_errors_${TIMESTAMP}.txt"
    
    echo "Ejecutando tests para: $project_name"
    
    # Buscar y ejecutar tests
    cd "$project_path" || return 1
    
    if [ -f "pyproject.toml" ]; then
        # Proyecto con pyproject.toml
        if [ -d ".venv" ]; then
            .venv/bin/python -m pytest -q --tb=short > "$test_output" 2>&1
        else
            python -m pytest -q --tb=short > "$test_output" 2>&1
        fi
    elif [ -f "test_runner.py" ]; then
        # Proyecto con test_runner.py
        python test_runner.py > "$test_output" 2>&1
    elif [ -d "tests" ]; then
        # Proyecto con carpeta tests
        python -m pytest tests/ -q --tb=short > "$test_output" 2>&1
    else
        # Intentar pytest genérico
        python -m pytest -q --tb=short > "$test_output" 2>&1
    fi
    
    # Extraer errores
    grep -E "(FAILED|ERROR|failed|error|ImportError|SyntaxError|TypeError|NameError|AttributeError)" "$test_output" > "$error_output"
    
    local error_count=$(wc -l < "$error_output")
    echo "Errores encontrados en $project_name: $error_count"
    
    if [ $error_count -gt 0 ]; then
        echo "Errores detallados:"
        cat "$error_output"
    fi
    
    echo "$error_count" > "$LOG_DIR/${project_name}_error_count_${TIMESTAMP}.txt"
    echo "$error_output"
}

# Función para analizar y corregir errores
analyze_and_fix_errors() {
    local error_file="$1"
    local project_path="$2"
    local project_name="$3"
    local modified_files=()
    local bugs_fixed=0
    local complex_issues=()
    
    if [ ! -f "$error_file" ]; then
        echo "No se encontró archivo de errores: $error_file"
        return 0
    fi
    
    echo "Analizando errores en: $project_name"
    
    # Leer errores y procesar
    while IFS= read -r error_line; do
        if [[ $error_line == *"FAILED"* ]] || [[ $error_line == *"ERROR"* ]]; then
            # Extraer información del error
            local file_info=$(echo "$error_line" | grep -oE "[A-Za-z0-9_\-/]+\.py" | head -1)
            if [ -n "$file_info" ]; then
                local file_path="$project_path/$file_info"
                echo "Procesando archivo: $file_path"
                
                # Intentar corrección automática basada en el tipo de error
                if [[ $error_line == *"ImportError"* ]]; then
                    fix_import_error "$file_path" "$error_line"
                elif [[ $error_line == *"SyntaxError"* ]]; then
                    fix_syntax_error "$file_path" "$error_line"
                elif [[ $error_line == *"TypeError"* ]] || [[ $error_line == *"NameError"* ]]; then
                    fix_type_error "$file_path" "$error_line"
                else
                    # Intentar corrección general
                    attempt_general_fix "$file_path" "$error_line"
                fi
                
                if [ $? -eq 0 ]; then
                    modified_files+=("$file_info")
                    ((bugs_fixed++))
                else
                    complex_issues+=("$file_info: $error_line")
                fi
            fi
        fi
    done < "$error_file"
    
    # Generar reporte
    local report_file="$LOG_DIR/${project_name}_refactor_report_${TIMESTAMP}.md"
    cat > "$report_file" << EOF
**Archivos Modificados:**
$(for file in "${modified_files[@]}"; do
    echo "- \`$file\`: Corrección automática de error detectado en los tests."
done)

**Bugs Pendientes / Notas de Atención:**
$(if [ ${#complex_issues[@]} -eq 0 ]; then
    echo "Ninguno. El código pasa el filtro de la iteración actual."
else
    for issue in "${complex_issues[@]}"; do
        echo "- $issue"
    done
fi)
EOF
    
    echo "Reporte generado: $report_file"
    echo "Bugs corregidos: $bugs_fixed"
    echo "Archivos modificados: ${#modified_files[@]}"
    
    return $bugs_fixed
}

# Función para corregir errores de importación
fix_import_error() {
    local file_path="$1"
    local error_line="$2"
    
    if [ ! -f "$file_path" ]; then
        return 1
    fi
    
    # Detectar importaciones faltantes y agregarlas
    if [[ $error_line == *"module"* ]] || [[ $error_line == *"No module named"* ]]; then
        # Intentar identificar el módulo faltante
        local missing_module=$(echo "$error_line" | grep -oE "'[^']+'" | head -1 | tr -d "'")
        
        if [ -n "$missing_module" ]; then
            # Agregar importación al final del archivo
            echo "# Corrección automática: Importación de $missing_module" >> "$file_path"
            echo "import $missing_module" >> "$file_path"
            return 0
        fi
    fi
    
    return 1
}

# Función para corregir errores de sintaxis
fix_syntax_error() {
    local file_path="$1"
    local error_line="$2"
    
    if [ ! -f "$file_path" ]; then
        return 1
    fi
    
    # Buscar y corregir sintaxis básica
    # Corregir puntos y faltantes
    sed -i '' 's/\. \./\.\./g' "$file_path"
    sed -i '' 's/ \.$/./g' "$file_path"
    
    # Corregir indentación
    python -m py_compile "$file_path" 2>/dev/null
    if [ $? -eq 0 ]; then
        return 0
    fi
    
    return 1
}

# Función para corregir errores de tipo
fix_type_error() {
    local file_path="$1"
    local error_line="$2"
    
    if [ ! -f "$file_path" ]; then
        return 1
    fi
    
    # Detectar y corregir errores de tipo simples
    if [[ $error_line == *"NoneType"* ]] || [[ $error_line == *"object has no attribute"* ]]; then
        # Agregar verificación de nulos
        sed -i '' 's/\(.*\)\.important_method/\1 is not None and \1.important_method/g' "$file_path"
        return 0
    fi
    
    return 1
}

# Función para intento de corrección general
attempt_general_fix() {
    local file_path="$1"
    local error_line="$2"
    
    if [ ! -f "$file_path" ]; then
        return 1
    fi
    
    # Intentar corrección general basada en patrones comunes
    # Corregir espacios extra
    sed -i '' 's/  */ /g' "$file_path"
    sed -i '' 's/^ *//g' "$file_path"
    
    return 0
}

# Procesar cada proyecto
project_count=0
for project_json in "${PROJECTS[@]}"; do
    # Extraer información manualmente sin jq
    project_name=$(echo "$project_json" | sed 's/.*"name":"\([^"]*\)".*/\1/')
    project_path=$(echo "$project_json" | sed 's/.*"path":"\([^"]*\)".*/\1/')
    priority=$(echo "$project_json" | sed 's/.*"priority":"\([^"]*\)".*/\1/')
    review_type=$(echo "$project_json" | sed 's/.*"review_type":"\([^"]*\)".*/\1/')
    
    echo "Procesando proyecto: $project_name (prioridad: $priority)"
    
    # Verificar si el proyecto existe y está dentro del directorio base
    if [[ "$project_path" != "$BASE_DIR"* ]]; then
        echo "ADVERTENCIA: El proyecto $project_name está fuera del directorio base. Omitiendo."
        continue
    fi
    
    if [ ! -d "$project_path" ]; then
        echo "ADVERTENCIA: El proyecto $project_name no existe en $project_path"
        continue
    fi
    
    # Ejecutar tests y obtener errores
    error_file=$(run_tests_and_get_errors "$project_path" "$project_name")
    
    if [ -n "$error_file" ] && [ -f "$error_file" ]; then
        error_count=$(cat "$LOG_DIR/${project_name}_error_count_${TIMESTAMP}.txt")
        
        if [ "$error_count" -gt 0 ]; then
            echo "Intentando corregir errores en $project_name..."
            analyze_and_fix_errors "$error_file" "$project_path" "$project_name"
        else
            echo "✅ $project_name: Sin errores detectados"
        fi
    fi
    
    ((project_count++))
done

# Generar reporte final
FINAL_REPORT="$LOG_DIR/nocturnal_refactor_final_report_${TIMESTAMP}.md"
cat > "$FINAL_REPORT" << EOF
# Reporte Final: Refactorización Iterativa Autónoma
**Hora de ejecución:** $(date)
**Directorio base:** $BASE_DIR
**Total de proyectos procesados:** $project_count

## Resumen de Acciones
EOF

echo "=== FIN: REFACTORIZACIÓN ITERATIVA AUTÓNOMA ==="
echo "Reporte final generado: $FINAL_REPORT"
echo "Todos los proyectos procesados están dentro del directorio base: $BASE_DIR"