#!/bin/bash

# SCRIPT SIMPLIFICADO DE ANÁLISIS SECUENCIAL DE PROYECTOS
# Versión mejorada y más robusta

set -e  # Salir si hay errores

# Directorio base
BASE_DIR="/Users/hugoonaindia/Desktop/Proyectos"
LOG_DIR="$BASE_DIR/logs"
LOG_FILE="$LOG_DIR/cron_job_log_$(date +%Y%m%d_%H%M%S).log"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

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
    
    echo "=== ANALIZANDO PROYECTO: $project_name ===" | tee -a "$LOG_FILE"
    echo "Ruta: $project_path" >> "$LOG_FILE"
    echo "Tiempo: $(date)" >> "$LOG_FILE"
    
    if [ ! -d "$project_path" ]; then
        echo "❌ PROYECTO NO EXISTE: $project_name" | tee -a "$LOG_FILE"
        return 1
    fi
    
    cd "$project_path"
    
    # 1. Búsqueda de errores de sintaxis
    echo "1. Buscando errores de sintaxis en $project_name..." >> "$LOG_FILE"
    python_files=$(find . -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" 2>/dev/null || true)
    python_files_count=$(echo "$python_files" | wc -l | tr -d ' ')
    
    echo "📁 Encontrados $python_files_count archivos Python" | tee -a "$LOG_FILE"
    echo "📁 Encontrados $python_files_count archivos Python" >> "$LOG_FILE"
    
    # Limitar análisis para proyectos muy grandes
    if [ "$python_files_count" -gt 100 ]; then
        echo "⚠️  Proyecto grande ($python_files_count archivos), analizando solo primeros 100 archivos..." | tee -a "$LOG_FILE"
        echo "⚠️  Proyecto grande ($python_files_count archivos), analizando solo primeros 100 archivos..." >> "$LOG_FILE"
        python_files=$(echo "$python_files" | head -100)
    fi
    
    syntax_errors=0
    files_analyzed=0
    
    for file in $python_files; do
        if [ $files_analyzed -ge 50 ]; then  # Limitar a 50 archivos por proyecto
            echo "⏸️  Límite de 50 archivos alcanzado para este proyecto" | tee -a "$LOG_FILE"
            break
        fi
        
        if python -m py_compile "$file" 2>/dev/null; then
            echo "✅ Sintaxis OK: $file" | tee -a "$LOG_FILE"
        else
            echo "❌ ERROR SINTAXIS: $file" | tee -a "$LOG_FILE"
            syntax_errors=$((syntax_errors + 1))
            
            # Intentar corregir automáticamente indentación simple
            if grep -q "^\w" "$file" && ! grep -q "^    " "$file" && ! grep -q "^\t" "$file"; then
                sed -i '' 's/^\([a-zA-Z_]\)/    \1/' "$file" 2>/dev/null || true
                echo "🔧 Intenté corregir indentación en: $file" | tee -a "$LOG_FILE"
                CORREGIDOS=$((CORREGIDOS + 1))
            fi
        fi
        files_analyzed=$((files_analyzed + 1))
    done
    
    echo "Errores de sintaxis encontrados: $syntax_errors" > "$project_log"
    echo "Archivos analizados: $files_analyzed" >> "$project_log"
    
    # 2. Búsqueda de patrones de bugs
    echo "2. Buscando patrones de bugs en $project_name..." | tee -a "$LOG_FILE"
    echo "2. Buscando patrones de bugs en $project_name..." >> "$LOG_FILE"
    
    bare_excepts=$(find . -name "*.py" -exec grep -l "except:" {} \; 2>/dev/null | wc -l | tr -d ' ')
    if [ "$bare_excepts" -gt 0 ]; then
        echo "⚠️  Found $bare_excepts bare except statements" | tee -a "$LOG_FILE"
        echo "⚠️  Found $bare_excepts bare except statements" >> "$LOG_FILE"
        
        # Intentar corregir bare excepts
        find . -name "*.py" -exec sed -i '' 's/except:/except Exception:/' {} \; 2>/dev/null || true
        echo "🔧 Intenté corregir bare excepts" | tee -a "$LOG_FILE"
        CORREGIDOS=$((CORREGIDOS + 1))
    fi
    
    # 3. Verificación de dependencias
    echo "3. Verificando dependencias en $project_name..." | tee -a "$LOG_FILE"
    echo "3. Verificando dependencias en $project_name..." >> "$LOG_FILE"
    
    if [ -f "requirements.txt" ]; then
        echo "✅ requirements.txt encontrado" | tee -a "$LOG_FILE"
        echo "✅ requirements.txt encontrado" >> "$project_log"
    else
        echo "⚠️  requirements.txt no encontrado" | tee -a "$LOG_FILE"
        echo "⚠️  requirements.txt no encontrado" >> "$project_log"
    fi
    
    if [ -f "pyproject.toml" ]; then
        echo "✅ pyproject.toml encontrado" | tee -a "$LOG_FILE"
        echo "✅ pyproject.toml encontrado" >> "$project_log"
    fi
    
    # Guardar resumen
    echo "" >> "$project_log"
    echo "=== RESUMEN $project_name ===" >> "$project_log"
    echo "Archivos Python: $python_files_count" >> "$project_log"
    echo "Errores de sintaxis: $syntax_errors" >> "$project_log"
    echo "Bare excepts: $bare_excepts" >> "$project_log"
    echo "Correcciones automáticas: $([ $syntax_errors -gt 0 ] && echo "Sí" || echo "No")" >> "$project_log"
    echo "Finalizado: $(date)" >> "$project_log"
    
    if [ $syntax_errors -eq 0 ] && [ $bare_excepts -eq 0 ]; then
        echo "✅ ANÁLISIS COMPLETADO: $project_name (sin errores)" | tee -a "$LOG_FILE"
        ANALIZADOS=$((ANALIZADOS + 1))
    else
        echo "⚠️  ANÁLISIS COMPLETADO: $project_name (con errores)" | tee -a "$LOG_FILE"
        ANALIZADOS=$((ANALIZADOS + 1))
        CON_ERRORES=$((CON_ERRORES + 1))
    fi
    
    echo "" >> "$LOG_FILE"
    
    # Volver al directorio base
    cd "$BASE_DIR"
}

# Ejecutar análisis secuencial de cada proyecto
for project in "${PROJECTS[@]}"; do
    TOTAL_PROJECTS=$((TOTAL_PROJECTS + 1))
    
    echo "🔄 Iniciando proyecto $project ($((TOTAL_PROJECTS-1+1))/${#PROJECTS[@]})..." | tee -a "$LOG_FILE"
    analyze_project "$project"
    
    # Pausa corta entre proyectos
    echo "⏱️  Esperando 2 segundos antes del siguiente proyecto..." | tee -a "$LOG_FILE"
    sleep 2
done

# Resumen final
echo "" >> "$LOG_FILE"
echo "=== RESUMEN FINAL ===" >> "$LOG_FILE"
echo "Total de proyectos: $TOTAL_PROJECTS" >> "$LOG_FILE"
echo "Analizados exitosamente: $ANALIZADOS" >> "$LOG_FILE"
echo "Con errores: $CON_ERRORES" >> "$LOG_FILE"
echo "Correcciones automáticas: $CORREGIDOS" >> "$LOG_FILE"
echo "Finalizado: $(date)" >> "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "✅ ANÁLISIS SECUENCIAL COMPLETADO" | tee -a "$LOG_FILE"
echo "Log detallado: $LOG_FILE" | tee -a "$LOG_FILE"

# Mostrar resumen en pantalla
echo ""
echo "=== RESUMEN FINAL ==="
echo "Total de proyectos: $TOTAL_PROJECTS"
echo "Analizados exitosamente: $ANALIZADOS"
echo "Con errores: $CON_ERRORES"
echo "Correcciones automáticas: $CORREGIDOS"
echo "Finalizado: $(date)"
echo ""
echo "Log detallado: $LOG_FILE"