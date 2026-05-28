"""
Script de migración para convertir notas existentes al nuevo formato estructurado.
"""

import re
import json
import sys
from datetime import datetime
from pathlib import Path

# Añadir el directorio data al path para importar la estructura
sys.path.append(str(Path(__file__).parent / "data"))

from estructura_datos import SistemaEquilibria, Paciente, Sesion


def parse_fecha(fecha_str):
    """Parsear fecha en formato AAAA-MM-DD a formato ISO"""
    try:
        # Asumir que si solo tiene año-mes, se completa con día 1
        if len(fecha_str) == 7:  # YYYY-MM
            fecha_str += "-01"
        return datetime.strptime(fecha_str, "%Y-%m-%d").isoformat()
    except (ValueError, TypeError):
        return datetime.now().isoformat()


def migrar_notas_pacientes():
    """Migrar notas desde el archivo Markdown al nuevo sistema"""
    
    # Cargar el archivo de notas existentes
    notas_file = Path("Notas Pacientes.md")
    if not notas_file.exists():
        print("Archivo de notas no encontrado")
        return
    
    # Crear instancia del sistema
    sistema = SistemaEquilibria()
    
    # Parsear el archivo Markdown
    with open(notas_file, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Extraer secciones de pacientes
    secciones = contenido.split('## ')[1:]  # Ignorar el encabezado
    
    for seccion in secciones:
        lines = seccion.strip().split('\n')
        
        # Extraer nombre del paciente (primera línea)
        if not lines or not lines[0]:
            continue
            
        nombre_paciente = lines[0].strip()
        
        # Crear paciente si no existe
        paciente_id = sistema.crear_paciente(nombre_paciente)
        print(f"Creado paciente: {nombre_paciente} (ID: {paciente_id})")
        
        # Procesar notas del paciente
        current_fecha = None
        notas_acumuladas = []
        
        for line in lines[1:]:
            line = line.strip()
            
            # Detectar fecha
            fecha_match = re.match(r'\*\*Fecha:\*\*\s*(.+)', line)
            if fecha_match:
                current_fecha = parse_fecha(fecha_match.group(1).strip())
                notas_acumuladas = []
                continue
            
            # Detectar nota (líneas con guión)
            if line.startswith('- '):
                nota_texto = line[2:].strip()
                if current_fecha and nota_texto:
                    # Agregar nota con fecha actual
                    sistema.agregar_nota_paciente(
                        paciente_id, 
                        nota_texto,
                        tags=["migrado"]
                    )
        
        # Crear sesión para la última entrada si tiene costo
        if notas_acumuladas:
            ultima_nota = notas_acumuladas[-1] if notas_acumuladas else ""
            if "euros" in ultima_nota.lower() or "€" in ultima_nota:
                # Extraer costo
                costo_match = re.search(r'(\d+(?:\.\d+)?)\s*euros', ultima_nota.lower())
                if costo_match:
                    costo = float(costo_match.group(1))
                    duracion = 80  # Duración por defecto
                    
                    sistema.crear_sesion(
                        paciente_id=paciente_id,
                        duracion=duracion,
                        costo=costo,
                        notas=ultima_nota,
                        tags=["migrado", "sesión"]
                    )
                    print(f"  Creada sesión: {costo}€, {duracion}min")


def migrar_tareas_colegio():
    """Migrar tareas del colegio al nuevo sistema"""
    
    # Cargar archivo de recogida
    recogida_file = Path("colegio/recogida-colegio.md")
    if not recogida_file.exists():
        print("Archivo de recogida no encontrado")
        return
    
    with open(recogida_file, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Crear instancia del sistema
    sistema = SistemaEquilibria()
    
    # Extraer información de la tarea
    tarea_id = sistema.crear_tarea(
        tipo="colegio",
        titulo="Recogida de niños",
        descripcion=contenido.strip(),
        prioridad="alta",
        asignada_a="padres"
    )
    
    print(f"Creada tarea: {tarea_id}")


def crear_datos_ejemplo():
    """Crear datos de ejemplo para el sistema"""
    
    sistema = SistemaEquilibria()
    
    # Crear pacientes de ejemplo
    pacientes_ejemplo = [
        {"nombre": "Naira", "email": "naira@example.com"},
        {"nombre": "Carlos", "email": "carlos@example.com"},
        {"nombre": "Ana", "email": "ana@example.com"}
    ]
    
    for paciente_data in pacientes_ejemplo:
        paciente_id = sistema.crear_paciente(**paciente_data)
        print(f"Creado paciente de ejemplo: {paciente_data['nombre']}")
        
        # Agregar notas de ejemplo
        sistema.agregar_nota_paciente(
            paciente_id,
            "Consulta inicial realizada con éxito",
            tags=["inicial", "importante"]
        )
        
        # Crear sesión de ejemplo
        sistema.crear_sesion(
            paciente_id=paciente_id,
            duracion=60,
            costo=80.0,
            notas="Sesión regular de seguimiento",
            tags=["seguimiento"]
        )


def generar_reporte_migracion():
    """Generar reporte de la migración"""
    
    sistema = SistemaEquilibria()
    
    reporte = {
        "fecha_migracion": datetime.now().isoformat(),
        "total_pacientes": len(sistema.pacientes),
        "total_sesiones": len(sistema.sesiones),
        "total_tareas": len(sistema.tareas),
        "pacientes": [
            {
                "id": p.id,
                "nombre": p.nombre,
                "notas_count": len(p.notas),
                "fecha_registro": p.fecha_registro
            }
            for p in sistema.pacientes.values()
        ],
        "sesiones": [
            {
                "id": s.id,
                "paciente_id": s.paciente_id,
                "fecha": s.fecha,
                "costo": s.costo,
                "duracion": s.duracion
            }
            for s in sistema.sesiones.values()
        ],
        "tareas": [
            {
                "id": t.id,
                "tipo": t.tipo,
                "titulo": t.titulo,
                "completada": t.completada
            }
            for t in sistema.tareas.values()
        ]
    }
    
    # Guardar reporte
    with open("data/migracion_reporte.json", 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    
    print("Reporte de migración generado: data/migracion_reporte.json")
    
    return reporte


def main():
    """Función principal de migración"""
    print("🚀 Iniciando migración del sistema equilibria...")
    
    # Migrar notas de pacientes
    print("\n📋 Migrando notas de pacientes...")
    migrar_notas_pacientes()
    
    # Migrar tareas del colegio
    print("\n🏫 Migrando tareas del colegio...")
    migrar_tareas_colegio()
    
    # Crear datos de ejemplo
    print("\n🎯 Creando datos de ejemplo...")
    crear_datos_ejemplo()
    
    # Generar reporte
    print("\n📊 Generando reporte de migración...")
    reporte = generar_reporte_migracion()
    
    print(f"\n✅ Migración completada!")
    print(f"📊 Resumen:")
    print(f"   - Pacientes: {reporte['total_pacientes']}")
    print(f"   - Sesiones: {reporte['total_sesiones']}")
    print(f"   - Tareas: {reporte['total_tareas']}")


if __name__ == "__main__":
    main()