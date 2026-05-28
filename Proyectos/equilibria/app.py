"""
Interfaz web para el sistema de gestión equilibria.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import sys
from pathlib import Path

# Añadir el directorio data al path
sys.path.append(str(Path(__file__).parent / "data"))

from estructura_datos import SistemaEquilibria, get_sistema

app = Flask(__name__)
sistema = get_sistema()


@app.route('/')
def index():
    """Página principal del sistema"""
    return render_template('index.html')


@app.route('/pacientes')
def listar_pacientes():
    """Listar todos los pacientes"""
    pacientes = sistema.get_pacientes()
    return render_template('pacientes.html', pacientes=pacientes)


@app.route('/pacientes/nuevo', methods=['GET', 'POST'])
def nuevo_paciente():
    """Formulario para nuevo paciente"""
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        
        if nombre:
            paciente_id = sistema.crear_paciente(nombre, email, telefono)
            return redirect(url_for('ver_paciente', paciente_id=paciente_id))
    
    return render_template('nuevo_paciente.html')


@app.route('/pacientes/<paciente_id>')
def ver_paciente(paciente_id):
    """Ver detalles de un paciente"""
    paciente = sistema.get_paciente(paciente_id)
    if not paciente:
        return "Paciente no encontrado", 404
    
    sesiones = sistema.get_sesiones_paciente(paciente_id)
    
    return render_template('paciente.html', paciente=paciente, sesiones=sesiones)


@app.route('/api/pacientes/<paciente_id>/notas', methods=['POST'])
def agregar_nota(paciente_id):
    """API para agregar nota a paciente"""
    data = request.get_json()
    
    if not paciente_id or not data.get('nota'):
        return jsonify({'error': 'Faltan datos'}), 400
    
    exito = sistema.agregar_nota_paciente(
        paciente_id, 
        data['nota'], 
        data.get('tags', [])
    )
    
    if exito:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Paciente no encontrado'}), 404


@app.route('/api/sesiones', methods=['POST'])
def crear_sesion():
    """API para crear nueva sesión"""
    data = request.get_json()
    
    campos_requeridos = ['paciente_id', 'duracion', 'costo', 'notas']
    for campo in campos_requeridos:
        if campo not in data:
            return jsonify({'error': f'Falta campo: {campo}'}), 400
    
    sesion_id = sistema.crear_sesion(
        data['paciente_id'],
        data['duracion'],
        data['costo'],
        data['notas'],
        data.get('tags', [])
    )
    
    return jsonify({'success': True, 'sesion_id': sesion_id})


@app.route('/tareas')
def listar_tareas():
    """Listar todas las tareas"""
    tareas = sistema.get_tareas_pendientes()
    return render_template('tareas.html', tareas=tareas)


@app.route('/tareas/nuevo', methods=['GET', 'POST'])
def nueva_tarea():
    """Formulario para nueva tarea"""
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        prioridad = request.form.get('prioridad', 'media')
        asignada_a = request.form.get('asignada_a')
        
        if titulo and tipo:
            tarea_id = sistema.crear_tarea(
                tipo, titulo, descripcion, 
                prioridad=prioridad, asignada_a=asignada_a
            )
            return redirect(url_for('ver_tarea', tarea_id=tarea_id))
    
    return render_template('nueva_tarea.html')


@app.route('/tareas/<tarea_id>')
def ver_tarea(tarea_id):
    """Ver detalles de una tarea"""
    tarea = sistema.tareas.get(tarea_id)
    if not tarea:
        return "Tarea no encontrada", 404
    
    return render_template('tarea.html', tarea=tarea)


@app.route('/api/tareas/<tarea_id>/completar', methods=['POST'])
def completar_tarea(tarea_id):
    """API para completar una tarea"""
    exito = sistema.marcar_tarea_completada(tarea_id)
    
    if exito:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Tarea no encontrada'}), 404


@app.route('/api/exportar')
def exportar_datos():
    """Exportar datos del sistema"""
    formato = request.args.get('formato', 'json')
    datos = sistema.exportar_datos(formato)
    
    if formato == 'json':
        return app.response_class(
            response=datos,
            status=200,
            mimetype='application/json'
        )
    else:
        return datos


@app.route('/dashboard')
def dashboard():
    """Panel de control principal"""
    total_pacientes = len(sistema.pacientes)
    total_sesiones = len(sistema.sesiones)
    total_tareas = len(sistema.tareas)
    tareas_pendientes = len(sistema.get_tareas_pendientes())
    
    # Calcular ingresos totales
    ingresos_totales = sum(s.costo for s in sistema.sesiones.values())
    
    # Últimas sesiones
    ultimas_sesiones = sorted(
        sistema.sesiones.values(), 
        key=lambda x: x.fecha, 
        reverse=True
    )[:5]
    
    # Tareas urgentes
    tareas_urgentes = [
        t for t in sistema.get_tareas_pendientes() 
        if t.prioridad == 'alta'
    ]
    
    return render_template(
        'dashboard.html',
        total_pacientes=total_pacientes,
        total_sesiones=total_sesiones,
        total_tareas=total_tareas,
        tareas_pendientes=tareas_pendientes,
        ingresos_totales=ingresos_totales,
        ultimas_sesiones=ultimas_sesiones,
        tareas_urgentes=tareas_urgentes
    )


if __name__ == '__main__':
    # Crear directorio de plantillas
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    print("🚀 Iniciando servidor web de equilibria...")
    print("📊 Accede a: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)