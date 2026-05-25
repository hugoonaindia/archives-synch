# Trader Supersimple

Versión mejorada y simplificada del Trader LSTM con arquitectura modular y robusta.

## 🚀 Descripción

Este proyecto es un sistema de trading automatizado diseñado para operar en mercados financieros con enfoque en simplicidad, estabilidad y mantenibilidad. A diferencia de la versión original, esta implementación incluye:

- **Arquitectura modular** para mejor organización y mantenibilidad
- **Manejo robusto de errores** con logging estructurado
- **Seguridad mejorada** con gestor de configuración y validación
- **Testing completo** con cobertura del 100% de los módulos principales
- **Documentación detallada** en cada componente

## 📁 Estructura del Proyecto

```
trader supersimple/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── api_client.py          # Cliente API original
│   │   └── simple_api_client.py  # Cliente API mejorado y simplificado
│   ├── config/
│   │   ├── __init__.py
│   │   ├── security_manager.py    # Gestor de seguridad y configuración
│   │   └── config.py             # Configuración básica
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── error_handler.py       # Manejador de errores original
│   │   ├── simple_error_handler.py # Manejador de errores mejorado
│   │   └── logging_utils.py      # Utilidades de logging
│   ├── main.py                    # Aplicación principal mejorada
│   └── simple_main.py             # Aplicación simplificada (recomendada)
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Configuración común de tests
│   ├── test_simple_main.py      # Tests de la aplicación principal
│   ├── test_simple_api_client.py # Tests del cliente API
│   ├── test_security_manager.py  # Tests del gestor de seguridad
│   └── test_simple_error_handler.py # Tests del manejador de errores
├── test_runner.py                # Script de ejecución de tests (original)
└── run_tests.py                  # Script de ejecución de tests mejorado
├── migrate_config.py            # Herramienta de migración de configuración
├── app_customtkinter_simple.py  # Interfaz gráfica simple
└── README.md                    # Este archivo
```

## ⚡ Características Principales

### 1. Cliente API Robusto (`simple_api_client.py`)
- Manejo automático de reintentos
- Logging estructurado para depuración
- Verificación de salud del sistema
- Manejo de errores con excepciones específicas

### 2. Gestor de Seguridad (`security_manager.py`)
- Validación de configuración segura
- Manejo de tokens de autenticación
- Logging de actividades sensibles
- Prevención de exposición de credenciales

### 3. Manejador de Errores (`simple_error_handler.py`)
- Logging estructurado con niveles
- Manejo de excepciones específicas
- Sistema de alertas configurables
- Registro de métricas de errores

### 4. Testing Completo
- Cobertura del 100% de los módulos principales
- Tests unitarios con mocking
- Tests de integración
- Reportes de cobertura detallados

## 🛠️ Instalación

### Requisitos
```bash
pip install pytest pytest-cov coverage
```

### Configuración Inicial
1. Clona el repositorio
2. Instala las dependencias
3. Configura tus credenciales en los archivos apropiados

## 🧪 Ejecución de Tests

### Ejecutar todos los tests
```bash
python run_tests.py
```

### Ejecutar tests con cobertura
```bash
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### Ejecutar tests específicos
```bash
python -m pytest tests/test_simple_api_client.py -v
```

## 📊 Métricas de Calidad

- **Cobertura de Tests**: 100% (módulos principales)
- **Documentación**: Docstrings completas en todas las clases y métodos
- **Manejo de Errores**: Excepciones específicas y logging estructurado
- **Seguridad**: Validación de configuración y protección de credenciales

## 🔧 Configuración

### Variables de Entorno
Las siguientes variables pueden ser configuradas:

```python
base_url = "https://paper-api.alpaca.markets"  # URL de la API
api_token = ""  # Token de API (obligatorio para producción)
admin_token = ""  # Token de administrador (opcional)
actor_id = ""  # ID del actor/usuario
```

### Archivos de Configuración
- `migrate_config.py`: Herramienta para migrar configuraciones entre versiones
- `security_manager.py`: Gestiona la seguridad y validación de configuración

## 🚨 Consideraciones de Seguridad

1. **Nunca expongas tokens** en el código fuente
2. **Usa variables de entorno** para credenciales sensibles
3. **Valida todas las entradas** del usuario
4. **Registra actividades sensibles** para auditoría

## 📈 Uso

### Ejecución Básica
```bash
python src/simple_main.py
```

### Ejecución con Logging Detallado
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('src/simple_main.py').read())"
```

## 🔄 Migración desde Versión Original

Para migrar desde la versión original:

1. Usa `migrate_config.py` para actualizar tu configuración
2. Ejecuta los tests para verificar que todo funciona
3. Revisa los logs para identificar cualquier problema
4. Actualiza tus scripts para usar las nuevas clases mejoradas

## 📝 Documentación Adicional

- **API Documentation**: Docstrings incluidas en cada clase y método
- **Test Documentation**: Cada archivo de test incluye explicación del propósito
- **Security Documentation**: Documentación de prácticas seguras en `security_manager.py`

## 🤝 Contribuciones

Para contribuir al proyecto:

1. Asegúrate de pasar todos los tests
2. Añade tests para cualquier nueva funcionalidad
3. Actualiza la documentación correspondiente
4. Sigue las prácticas de seguridad establecidas

## 📄 Licencia

[Indicar la licencia del proyecto]

## 🆘 Soporte

Para problemas o preguntas:

1. Revisa los logs en la consola
2. Ejecuta los tests para identificar problemas
3. Consulta la documentación de cada módulo
4. Contacta al equipo de desarrollo

---

*Este proyecto es una mejora de la versión original de Trader LSTM, enfocada en simplicidad, estabilidad y mantenibilidad.*