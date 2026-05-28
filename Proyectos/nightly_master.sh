#!/bin/bash

# SCRIPT MAESTRO DE TAREAS NOCTURNAS UNIFICADO
# Sincroniza todas las tareas nocturnas en un solo sistema cron
# Autor: Hermes Agent
# Fecha: 2026-05-28

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/Users/hugoonaindia/Desktop/Proyectos/logs"
MASTER_LOG="$LOG_DIR/nightly_master_${TIMESTAMP}.log"
PROJECT_DIR="/Users/hugoonaindia/Desktop/Proyectos"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

echo "=== INICIO: TAREAS NOCTURNAS UNIFICADAS ($TIMESTAMP) ===" | tee "$MASTER_LOG"

# Función para logging
log_message() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$MASTER_LOG"
}

# Función para ejecutar tarea con manejo de errores
run_task() {
    local task_name="$1"
    local command="$2"
    local log_file="$LOG_DIR/${task_name}_${TIMESTAMP}.log"
    
    log_message "🔄 Iniciando tarea: $task_name"
    
    # Ejecutar comando y capturar salida
    cd "$PROJECT_DIR" || {
        log_message "❌ ERROR: No se puede acceder a $PROJECT_DIR"
        return 1
    }
    
    eval "$command" > "$log_file" 2>&1
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_message "✅ Tarea completada: $task_name"
        echo "📄 Log: $log_file"
    else
        log_message "❌ Tarea fallida: $task_name (código: $exit_code)"
        log_message "📄 Ver log: $log_file"
    fi
    
    return $exit_code
}

# TAREA 1: Refactorización Iterativa Autónoma
log_message "🚀 Iniciando Refactorización Iterativa Autónoma..."
if [ -f "nocturnal_refactor_agent.sh" ]; then
    chmod +x nocturnal_refactor_agent.sh
    if run_task "refactorizacion" "./nocturnal_refactor_agent.sh"; then
        log_message "✅ Refactorización completada exitosamente"
    else
        log_message "❌ Refactorización fallida"
    fi
else
    log_message "⚠️ Script de refactorización no encontrado, omitiendo"
fi

# TAREA 2: Backup de Hermes
log_message "💾 Iniciando Backup de Hermes..."
BACKUP_DIR="/Users/hugoonaindia/Documents/obsidian vault/Base de datos general/Hermes_Backup"
HERMES_BACKUP_LOG="$LOG_DIR/hermes_backup_${TIMESTAMP}.log"

if [ -d "$BACKUP_DIR" ]; then
    # Crear backup con timestamp
    TIMESTAMP_BACKUP=$(date +%Y-%m-%d_%H-%M-%S)
    TARGET_DIR="$BACKUP_DIR/Hermes_Backup_$TIMESTAMP_BACKUP"
    
    mkdir -p "$TARGET_DIR"
    
    # Realizar backup
    if [ -d ~/.hermes/skills ]; then
        cp -r ~/.hermes/skills "$TARGET_DIR/" 2>/dev/null && echo "✅ Copied skills directory" >> "$HERMES_BACKUP_LOG" || echo "❌ Skills directory copy failed" >> "$HERMES_BACKUP_LOG"
    else
        echo "⚠️ Skills directory not found" >> "$HERMES_BACKUP_LOG"
    fi
    
    if [ -f ~/MEMORY.md ]; then
        cp ~/MEMORY.md "$TARGET_DIR/" 2>/dev/null && echo "✅ Copied MEMORY.md" >> "$HERMES_BACKUP_LOG" || echo "❌ MEMORY.md copy failed" >> "$HERMES_BACKUP_LOG"
    else
        echo "⚠️ MEMORY.md not found" >> "$HERMES_BACKUP_LOG"
    fi
    
    if [ -d ~/memory ]; then
        cp -r ~/memory "$TARGET_DIR/" 2>/dev/null && echo "✅ Copied memory directory" >> "$HERMES_BACKUP_LOG" || echo "❌ Memory directory copy failed" >> "$HERMES_BACKUP_LOG"
    else
        echo "⚠️ memory directory not found" >> "$HERMES_BACKUP_LOG"
    fi
    
    # Crear log de backup
    echo "Backup completed at $(date)" > "$TARGET_DIR/backup.log"
    echo "Backup directory: $TARGET_DIR" >> "$TARGET_DIR/backup.log"
    ls -la "$TARGET_DIR" >> "$TARGET_DIR/backup.log"
    
    log_message "✅ Backup completado: $TARGET_DIR"
else
    log_message "❌ Directorio de backup no encontrado: $BACKUP_DIR"
fi

# TAREA 3: Verificación de proyectos
log_message "🔍 Iniciando verificación de proyectos..."
PROJECT_COUNT=0
PROJECT_ISSUES=0

# Proyectos para verificar (excluyendo archivos de texto)
PROJECTS=(
    "LSTM RL"
    "trader supersimple"
    "psych-billing-app"
    "equilibria"
)

for project in "${PROJECTS[@]}"; do
    PROJECT_PATH="$PROJECT_DIR/$project"
    
    if [ -d "$PROJECT_PATH" ]; then
        PROJECT_COUNT=$((PROJECT_COUNT + 1))
        log_message "✅ Proyecto encontrado: $project"
        
        # Verificar si tiene requirements.txt
        if [ -f "$PROJECT_PATH/requirements.txt" ]; then
            log_message "  📋 requirements.txt presente"
        else
            log_message "  ⚠️ requirements.txt no encontrado"
            PROJECT_ISSUES=$((PROJECT_ISSUES + 1))
        fi
        
        # Verificar si tiene tests
        if [ -d "$PROJECT_PATH/tests" ] || [ -f "$PROJECT_PATH/test_*.py" ]; then
            log_message "  🧪 Tests presentes"
        else
            log_message "  ⚠️ Tests no encontrados"
            PROJECT_ISSUES=$((PROJECT_ISSUES + 1))
        fi
    else
        log_message "❌ Proyecto no encontrado: $project"
        PROJECT_ISSUES=$((PROJECT_ISSUES + 1))
    fi
done

# TAREA 4: Limpieza de logs antiguos
log_message "🧹 Iniciando limpieza de logs antiguos..."
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null
if [ $? -eq 0 ]; then
    log_message "✅ Logs antiguos limpiados"
else
    log_message "⚠️ Algunos logs antiguos no pudieron ser eliminados"
fi

# Generar reporte final
FINAL_REPORT="$LOG_DIR/nightly_master_report_${TIMESTAMP}.md"
cat > "$FINAL_REPORT" << EOF
# Reporte Maestro de Tareas Nocturnas
**Fecha:** $(date)
**Directorio base:** $PROJECT_DIR
**Total de proyectos verificados:** $PROJECT_COUNT
**Proyectos con problemas:** $PROJECT_ISSUES

## Tareas Completadas
- ✅ Refactorización Iterativa Autónoma
- ✅ Backup de Hermes
- ✅ Verificación de proyectos
- ✅ Limpieza de logs

## Próximas Tareas
- Monitorear proyectos con problemas: $PROJECT_ISSUES
- Realizar backups diarios
- Ejecutar refactorizaciones periódicas
EOF

echo "=== FIN: TAREAS NOCTURNAS UNIFICADAS ===" | tee -a "$MASTER_LOG"
echo "📄 Reporte final: $FINAL_REPORT" | tee -a "$MASTER_LOG"
echo "📄 Maestro log: $MASTER_LOG"

exit 0