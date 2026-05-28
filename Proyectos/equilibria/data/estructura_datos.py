"""
Estructura de datos para el sistema de gestión de práctica terapéutica equilibria.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Paciente:
    """Clase para representar un paciente"""
    id: str
    nombre: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    fecha_registro: str = ""
    notas: List[Dict[str, Any]] = None
    metadatos: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.notas is None:
            self.notas = []
        if self.metadatos is None:
            self.metadatos = {}
        if not self.fecha_registro:
            self.fecha_registro = datetime.now().isoformat()


@dataclass
class Sesion:
    """Clase para representar una sesión terapéutica"""
    id: str
    paciente_id: str
    fecha: str
    duracion: int  # en minutos
    costo: float
    notas: str
    estado: str = "completada"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class TareaAdministrativa:
    """Clase para representar tareas administrativas"""
    id: str
    tipo: str  # "colegio", "paciente", "general"
    titulo: str
    descripcion: str
    fecha_limite: str
    completada: bool = False
    prioridad: str = "media"
    asignada_a: str = ""
    
    def __post_init__(self):
        if not self.fecha_limite:
            self.fecha_limite = datetime.now().isoformat()


class SistemaEquilibria:
    """Sistema principal de gestión para equilibria"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Rutas de archivos
        self.pacientes_file = self.data_dir / "pacientes.json"
        self.sesiones_file = self.data_dir / "sesiones.json"
        self.tareas_file = self.data_dir / "tareas.json"
        
        # Datos en memoria
        self.pacientes: Dict[str, Paciente] = {}
        self.sesiones: Dict[str, Sesion] = {}
        self.tareas: Dict[str, TareaAdministrativa] = {}
        
        # Inicializar sistema
        self.cargar_datos()
    
    def cargar_datos(self):
        """Cargar datos desde archivos JSON"""
        try:
            if self.pacientes_file.exists():
                with open(self.pacientes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for p_data in data:
                        paciente = Paciente(**p_data)
                        self.pacientes[paciente.id] = paciente
        except Exception as e:
            print(f"Error cargando pacientes: {e}")
        
        try:
            if self.sesiones_file.exists():
                with open(self.sesiones_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for s_data in data:
                        sesion = Sesion(**s_data)
                        self.sesiones[sesion.id] = sesion
        except Exception as e:
            print(f"Error cargando sesiones: {e}")
        
        try:
            if self.tareas_file.exists():
                with open(self.tareas_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for t_data in data:
                        tarea = TareaAdministrativa(**t_data)
                        self.tareas[tarea.id] = tarea
        except Exception as e:
            print(f"Error cargando tareas: {e}")
    
    def guardar_datos(self):
        """Guardar datos en archivos JSON"""
        try:
            with open(self.pacientes_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(p) for p in self.pacientes.values()], f, 
                         indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando pacientes: {e}")
        
        try:
            with open(self.sesiones_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(s) for s in self.sesiones.values()], f, 
                         indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando sesiones: {e}")
        
        try:
            with open(self.tareas_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(t) for t in self.tareas.values()], f, 
                         indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando tareas: {e}")
    
    def crear_paciente(self, nombre: str, email: str = None, telefono: str = None) -> str:
        """Crear un nuevo paciente"""
        import uuid
        paciente_id = str(uuid.uuid4())
        
        paciente = Paciente(
            id=paciente_id,
            nombre=nombre,
            email=email,
            telefono=telefono
        )
        
        self.pacientes[paciente_id] = paciente
        self.guardar_datos()
        
        return paciente_id
    
    def agregar_nota_paciente(self, paciente_id: str, nota: str, tags: List[str] = None) -> bool:
        """Agregar una nota a un paciente"""
        if paciente_id not in self.pacientes:
            return False
        
        if tags is None:
            tags = []
        
        nota_data = {
            "fecha": datetime.now().isoformat(),
            "nota": nota,
            "tags": tags
        }
        
        self.pacientes[paciente_id].notas.append(nota_data)
        self.guardar_datos()
        
        return True
    
    def crear_sesion(self, paciente_id: str, duracion: int, costo: float, 
                    notas: str, tags: List[str] = None) -> str:
        """Crear una nueva sesión"""
        import uuid
        sesion_id = str(uuid.uuid4())
        
        sesion = Sesion(
            id=sesion_id,
            paciente_id=paciente_id,
            fecha=datetime.now().isoformat(),
            duracion=duracion,
            costo=costo,
            notas=notas,
            tags=tags or []
        )
        
        self.sesiones[sesion_id] = sesion
        self.guardar_datos()
        
        return sesion_id
    
    def crear_tarea(self, tipo: str, titulo: str, descripcion: str, 
                   fecha_limite: str = None, prioridad: str = "media",
                   asignada_a: str = "") -> str:
        """Crear una nueva tarea administrativa"""
        import uuid
        tarea_id = str(uuid.uuid4())
        
        tarea = TareaAdministrativa(
            id=tarea_id,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            fecha_limite=fecha_limite or datetime.now().isoformat(),
            prioridad=prioridad,
            asignada_a=asignada_a
        )
        
        self.tareas[tarea_id] = tarea
        self.guardar_datos()
        
        return tarea_id
    
    def get_paciente(self, paciente_id: str) -> Optional[Paciente]:
        """Obtener un paciente por ID"""
        return self.pacientes.get(paciente_id)
    
    def get_pacientes(self) -> List[Paciente]:
        """Obtener todos los pacientes"""
        return list(self.pacientes.values())
    
    def get_sesiones_paciente(self, paciente_id: str) -> List[Sesion]:
        """Obtener todas las sesiones de un paciente"""
        return [s for s in self.sesiones.values() if s.paciente_id == paciente_id]
    
    def get_tareas_pendientes(self) -> List[TareaAdministrativa]:
        """Obtener tareas pendientes"""
        return [t for t in self.tareas.values() if not t.completada]
    
    def marcar_tarea_completada(self, tarea_id: str) -> bool:
        """Marcar una tarea como completada"""
        if tarea_id in self.tareas:
            self.tareas[tarea_id].completada = True
            self.guardar_datos()
            return True
        return False
    
    def exportar_datos(self, formato: str = "json") -> str:
        """Exportar datos en formato específico"""
        datos = {
            "pacientes": [asdict(p) for p in self.pacientes.values()],
            "sesiones": [asdict(s) for s in self.sesiones.values()],
            "tareas": [asdict(t) for t in self.tareas.values()],
            "exportado_el": datetime.now().isoformat()
        }
        
        if formato.lower() == "json":
            return json.dumps(datos, indent=2, ensure_ascii=False)
        elif formato.lower() == "csv":
            # Implementar exportación CSV
            pass
        
        return json.dumps(datos, indent=2, ensure_ascii=False)


# Instancia global del sistema
sistema = SistemaEquilibria()


def get_sistema() -> SistemaEquilibria:
    """Obtener la instancia global del sistema"""
    return sistema