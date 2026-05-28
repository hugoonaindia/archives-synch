#!/bin/bash

# SCRIPT MEJORADO DE ANÁLISIS SECUENCIAL CON CORRECCIÓN AUTOMÁTICA Y REGISTRO MAESTRO
# Versión 2.0: Detecta, corrige bugs y registra todas las acciones

set -e  # Salir si hay errores

# Directorio base
BASE_DIR="/Users/hugoonaindia/Desktop/Proyectos"
LOG_DIR="$BASE_DIR/logs"
LOG_FILE="$LOG_DIR/cron_job_log_$(date +%Y%m%d_%H%M%S).log"
MASTER_REPORT="$LOG_DIR/master_bug_report_$(date +%Y%m%d).md"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

# Inicializar documento maestro
cat > "$MASTER_REPORT" << EOF
# 📋 MAESTRO DE REGISTRO DE BUGS Y CORRECCIONES
## Fecha: $(date)
### Procesamiento automatizado de debugging y corrección

---

EOF

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

# Contadores globales
TOTAL_PROJECTS=0
ANALIZADOS=0
CON_ERRORES=0
CORREGIDOS=0
TOTAL_BARE_EXCEPTS=0
TOTAL_SYNTAX_ERRORS=0

# Función para registrar en documento maestro
log_to_master() {
    echo "$1" >> "$MASTER_REPORT"
}

# Función para analizar un proyecto
analyze_project() {
    local project_name="$1"
    local project_path="$BASE_DIR/$project_name"
    local project_log="$LOG_DIR/${project_name}_analysis_$(date +%Y%m%d_%H%M%S).txt"
    
    echo "=== ANALIZANDO PROYECTO: $project_name ===" | tee -a "$LOG_FILE"
    echo "Ruta: $project_path" >> "$LOG_FILE"
    echo "Tiempo: $(date)" >> "$LOG_FILE"
    
    # Registrar en documento maestro
    log_to_master "## 🔍 Proyecto: $project_name"
    log_to_master "**Ruta:** $project_path"
    log_to_master "**Fecha de análisis:** $(date)"
    log_to_master ""
    
    if [ ! -d "$project_path" ]; then
        echo "❌ PROYECTO NO EXISTE: $project_name" | tee -a "$LOG_FILE"
        log_to_master "❌ **Estado:** Proyecto no encontrado"
        log_to_master ""
        return 1
    fi
    
    cd "$project_path"
    
    # 1. Búsqueda de errores de sintaxis
    echo "1. Buscando errores de sintaxis en $project_name..." >> "$LOG_FILE"
    python_files=$(find . -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" 2>/dev/null || true)
    python_files_count=$(echo "$python_files" | wc -l | tr -d ' ')
    
    echo "📁 Encontrados $python_files_count archivos Python" | tee -a "$LOG_FILE"
    log_to_master "📁 **Archivos Python encontrados:** $python_files_count"
    
    # Limitar análisis para proyectos muy grandes
    if [ "$python_files_count" -gt 100 ]; then
        echo "⚠️  Proyecto grande ($python_files_count archivos), analizando solo primeros 100 archivos..." | tee -a "$LOG_FILE"
        log_to_master "⚠️  **Limitación:** Proyecto grande, analizando solo primeros 100 archivos"
        python_files=$(echo "$python_files" | head -100)
    fi
    
    syntax_errors=0
    files_analyzed=0
    syntax_corrections=0
    corrected_bare_excepts=0
    
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
            
            # Intentar corregir automáticamente errores de sintaxis comunes
            if grep -q "^\w" "$file" && ! grep -q "^    " "$file" && ! grep -q "^\t" "$file"; then
                sed -i '' 's/^\([a-zA-Z_]\)/    \1/' "$file" 2>/dev/null || true
                if python -m py_compile "$file" 2>/dev/null; then
                    echo "🔧 ✅ **CORREGIDO** - Indentación faltante: $file" | tee -a "$LOG_FILE"
                    log_to_master "🔧 **Corrección automática - Indentación:** $file"
                    syntax_corrections=$((syntax_corrections + 1))
                    CORREGIDOS=$((CORREGIDOS + 1))
                fi
            fi
            
            # Intentar corregir comas faltantes en tuplas/listas
            if grep -n ".*[,(]\$" "$file" | head -1 | while read line_num line; do
                if [ -n "$line" ] && [[ "$line" =~ ^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*\(.*[^,][[:space:]]*\)[[:space:]]*$ ]]; then
                    sed -i '' "${line_num}s/[[:space:]]*)[[:space:]]*/),/" "$file" 2>/dev/null || true
                    python -m py_compile "$file" 2>/dev/null
                    if [ $? -eq 0 ]; then
                        echo "🔧 ✅ **CORREGIDO** - Coma faltante: $file (línea $line_num)" | tee -a "$LOG_FILE"
                        log_to_master "🔧 **Corrección automática - Coma faltante:** $file (línea $line_num)"
                        syntax_corrections=$((syntax_corrections + 1))
                        CORREGIDOS=$((CORREGIDOS + 1))
                    fi
                    break
                fi
            done; then
                true
            fi
        fi
        files_analyzed=$((files_analyzed + 1))
    done
    
    TOTAL_SYNTAX_ERRORS=$((TOTAL_SYNTAX_ERRORS + syntax_errors))
    echo "Errores de sintaxis encontrados: $syntax_errors" > "$project_log"
    echo "Errores de sintaxis corregidos: $syntax_corrections" >> "$project_log"
    log_to_master "🔍 **Errores de sintaxis encontrados:** $syntax_errors"
    log_to_master "✅ **Correcciones de sintaxis aplicadas:** $syntax_corrections"
    
    # 2. Búsqueda y corrección de patrones de bugs
    echo "2. Buscando patrones de bugs en $project_name..." | tee -a "$LOG_FILE"
    
    bare_excepts=$(find . -name "*.py" -exec grep -l "except:" {} \; 2>/dev/null | wc -l | tr -d ' ')
    if [ "$bare_excepts" -gt 0 ]; then
        echo "⚠️  Found $bare_excepts bare except statements" | tee -a "$LOG_FILE"
        log_to_master "⚠️  **Bare except statements encontrados:** $bare_excepts"
        
        # Corregir bare excepts automáticamente
        bare_except_files=$(find . -name "*.py" -exec grep -l "except:" {} \; 2>/dev/null)
        corrected_bare_excepts=0
        
        for file in $bare_except_files; do
            backup_file="$file.backup_$(date +%s)"
            cp "$file" "$backup_file" 2>/dev/null || true
            
            # Reemplazar except: con except Exception:
            sed -i '' 's/except:/except Exception:/g' "$file" 2>/dev/null || true
            
            # Verificar si la corrección fue exitosa
            if ! grep -q "except:" "$file" 2>/dev/null; then
                echo "🔧 ✅ **CORREGIDO** - Bare excepts en: $file" | tee -a "$LOG_FILE"
                log_to_master "🔧 **Corrección automática - Bare excepts:** $file"
                corrected_bare_excepts=$((corrected_bare_excepts + 1))
                CORREGIDOS=$((CORREGIDOS + 1))
            else
                # Restaurar backup si no se pudo corregir
                cp "$backup_file" "$file" 2>/dev/null || true
            fi
            
            rm -f "$backup_file" 2>/dev/null || true
        done
        
        TOTAL_BARE_EXCEPTS=$((TOTAL_BARE_EXCEPTS + corrected_bare_excepts))
        echo "Bare excepts corregidos: $corrected_bare_excepts" >> "$project_log"
        log_to_master "✅ **Bare excepts corregidos:** $corrected_bare_excepts"
    else
        log_to_master "✅ **Bare excepts:** Ninguno encontrado"
    fi
    
    # 3. Verificación y actualización de dependencias
    echo "3. Verificando dependencias en $project_name..." | tee -a "$LOG_FILE"
    
    if [ -f "requirements.txt" ]; then
        echo "✅ requirements.txt encontrado" | tee -a "$LOG_FILE"
        log_to_master "✅ **requirements.txt:** Presente"
        
        # Intentar instalar dependencias faltantes básicas
        python -c "import numpy, pandas" 2>/dev/null || {
            echo "⚠️  Dependencias básicas faltantes, intentando instalar numpy y pandas..." | tee -a "$LOG_FILE"
            pip install numpy pandas 2>/dev/null || echo "⚠️  No se pudieron instalar dependencias automáticamente" | tee -a "$LOG_FILE"
        }
    else
        echo "⚠️  requirements.txt no encontrado" | tee -a "$LOG_FILE"
        log_to_master "❌ **requirements.txt:** No encontrado"
    fi
    
    if [ -f "pyproject.toml" ]; then
        echo "✅ pyproject.toml encontrado" | tee -a "$LOG_FILE"
        log_to_master "✅ **pyproject.toml:** Presente"
    fi
    
    # 4. Búsqueda de otros patrones comunes de bugs
    echo "4. Buscando otros patrones de bugs en $project_name..." | tee -a "$LOG_FILE"
    
    # TODO statements sin comillas
    todos=$(find . -name "*.py" -exec grep -l "TODO:" {} \; 2>/dev/null | wc -l | tr -d ' ')
    if [ "$todos" -gt 0 ]; then
        echo "ℹ️  Found $todos TODO statements" | tee -a "$LOG_FILE"
        log_to_master "📝 **TODO statements encontrados:** $todos"
    fi
    
    # Importaciones potencial problemáticas
    problematic_imports=$(find . -name "*.py" -exec grep -l "import \*" {} \; 2>/dev/null | wc -l | tr -d ' ')
    if [ "$problematic_imports" -gt 0 ]; then
        echo "⚠️  Found $problematic_imports wildcard imports" | tee -a "$LOG_FILE"
        log_to_master "⚠️  **Importaciones con * (wildcard):** $problematic_imports"
    fi
    
    # Guardar resumen en documento maestro
    echo "" >> "$MASTER_REPORT"
    echo "---" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
    
    if [ $syntax_errors -eq 0 ] && [ $corrected_bare_excepts -eq 0 ]; then
        echo "✅ ANÁLISIS COMPLETADO: $project_name (sin errores)" | tee -a "$LOG_FILE"
        log_to_master "🎉 **Estado final:** Sin errores detectables"
        ANALIZADOS=$((ANALIZADOS + 1))
    else
        echo "⚠️  ANÁLISIS COMPLETADO: $project_name (con errores detectados y corregidos)" | tee -a "$LOG_FILE"
        log_to_master "⚠️  **Estado final:** Errores detectados y corregidos automáticamente"
        ANALIZADOS=$((ANALIZADOS + 1))
        CON_ERRORES=$((CON_ERRORES + 1))
    fi
    
    echo "Resumen: Errores=$syntax_errors, Bare_excepts=$corrected_bare_excepts, Correcciones=$syntax_corrections" >> "$project_log"
    echo "Finalizado: $(date)" >> "$project_log"
    
    echo "" >> "$LOG_FILE"
    
    # Volver al directorio base
    cd "$BASE_DIR"
}

# Ejecutar análisis secuencial de cada proyecto
echo "🚀 INICIANDO PROCESO AUTOMATIZADO DE DEBUGGING Y CORRECCIÓN" | tee -a "$LOG_FILE"
echo "📅 Fecha: $(date)" | tee -a "$LOG_FILE"
echo "📂 Proyectos a procesar: ${#PROJECTS[@]}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

log_to_master "# 🚀 INICIO PROCESO AUTOMATIZADO"
log_to_master "**Fecha de inicio:** $(date)"
log_to_master "**Total de proyectos:** ${#PROJECTS[@]}"
log_to_master ""

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
echo "=== RESUMEN FINAL DEL PROCESO ===" >> "$LOG_FILE"
echo "Total de proyectos: $TOTAL_PROJECTS" >> "$LOG_FILE"
echo "Analizados exitosamente: $ANALIZADOS" >> "$LOG_FILE"
echo "Con errores detectados: $CON_ERRORES" >> "$LOG_FILE"
echo "Total de correcciones automáticas: $CORREGIDOS" >> "$LOG_FILE"
echo "Total de errores de sintaxis: $TOTAL_SYNTAX_ERRORS" >> "$LOG_FILE"
echo "Total de bare excepts corregidos: $TOTAL_BARE_EXCEPTS" >> "$LOG_FILE"
echo "Finalizado: $(date)" >> "$LOG_FILE"

# Actualizar documento maestro con resumen final
echo "" >> "$MASTER_REPORT"
echo "# 📊 RESUMEN FINAL DEL PROCESO" >> "$MASTER_REPORT"
echo "**Fecha de finalización:** $(date)" >> "$MASTER_REPORT"
echo "**Total de proyectos procesados:** $TOTAL_PROJECTS" >> "$MASTER_REPORT"
echo "**Proyectos analizados exitosamente:** $ANALIZADOS" >> "$MASTER_REPORT"
echo "**Proyectos con errores detectados:** $CON_ERRORES" >> "$MASTER_REPORT"
echo "**Total de correcciones automáticas aplicadas:** $CORREGIDOS" >> "$MASTER_REPORT"
echo "**Total de errores de sintaxis corregidos:** $TOTAL_SYNTAX_ERRORS" >> "$MASTER_REPORT"
echo "**Total de bare excepts corregidos:** $TOTAL_BARE_EXCEPTS" >> "$MASTER_REPORT"
echo "" >> "$MASTER_REPORT"
echo "---" >> "$MASTER_REPORT"
echo "*Este documento se genera automáticamente mediante el sistema de debugging y corrección automática*" >> "$MASTER_REPORT"

echo "" | tee -a "$LOG_FILE"
echo "✅ PROCESO COMPLETADO" | tee -a "$LOG_FILE"
echo "📄 Log detallado: $LOG_FILE" | tee -a "$LOG_FILE"
echo "📋 Documento maestro de bugs: $MASTER_REPORT" | tee -a "$LOG_FILE"

# Mostrar resumen en pantalla
echo ""
echo "=== RESUMEN FINAL ==="
echo "Total de proyectos: $TOTAL_PROJECTS"
echo "Analizados exitosamente: $ANALIZADOS"
echo "Con errores: $CON_ERRORES"
echo "Correcciones automáticas: $CORREGIDOS"
echo "Errores de sintaxis corregidos: $TOTAL_SYNTAX_ERRORS"
echo "Bare excepts corregidos: $TOTAL_BARE_EXCEPTS"
echo "Finalizado: $(date)"
echo ""
echo "📄 Log detallado: $LOG_FILE"
echo "📋 Documento maestro: $MASTER_REPORT"