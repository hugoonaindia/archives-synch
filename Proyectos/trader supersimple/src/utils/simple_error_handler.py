"""
Manejo simple de errores sin seguridad compleja

Este módulo proporciona herramientas básicas para manejo de errores,
logging y reintentos con exponential backoff. Diseñado para ser
ligero y fácil de integrar en aplicaciones simples.

Funcionalidades principales:
- Decorador para reintentos con exponential backoff
- Logger simple con niveles estándar
- Manejo básico de errores con contexto
"""

import logging
import logging.handlers
import time
from pathlib import Path
from typing import Callable, Any, Optional
from functools import wraps


def retry_with_backoff_simple(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    raise_on_failure: bool = True
) -> Callable:
    """
    Decorador simple para reintentos con exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logging.error(f"Función {func.__name__} falló después de {max_retries} intentos")
                        if raise_on_failure:
                            raise
                        return None
                    
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + 0.5 * (time.time() % 1))
                    
                    logging.warning(
                        f"Intento {attempt + 1}/{max_retries} para {func.__name__} falló. "
                        f"Reintentando en {delay:.2f}s... Error: {str(e)}"
                    )
                    
                    time.sleep(delay)
            
            return None
        
        return wrapper
    return decorator


class SimpleLogger:
    """
    Logger simple y efectivo para aplicaciones trader.
    
    Esta clase proporciona una interfaz sencilla para logging con niveles
    estándar (INFO, WARNING, ERROR). Es diseñada para ser ligera y
    fácil de usar sin configuración compleja.
    
    Atributos:
        logger: Instancia de logging.Logger subyacente
        
    Ejemplos:
        >>> logger = SimpleLogger("mi_app")
        >>> logger.log_info("Aplicación iniciada")
        >>> logger.log_warning("Valor inusual detectado")
        >>> logger.log_error(ValueError("Error crítico"), "contexto")
    """
    
    def __init__(self, name: str = "trader_lstm"):
        """
        Inicializa un nuevo SimpleLogger.
        
        Args:
            name: Nombre del logger para identificación en logs
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_error(self, error: Exception, context: Optional[str] = None):
        """
        Registrar un error con contexto opcional.
        
        Este método registra errores en formato estructurado, incluyendo
        el mensaje de error y opcionalmente un contexto adicional que
        ayuda a identificar dónde ocurrió el problema.
        
        Args:
            error: Excepción que ocurrió
            context: Contexto adicional opcional para identificar el error
            
        Ejemplos:
            >>> try:
            ...     risky_operation()
            ... except ValueError as e:
            ...     logger.log_error(e, "Procesando datos del usuario")
        """
        error_msg = f"Error: {str(error)}"
        if context:
            error_msg = f"Contexto: {context} - {error_msg}"
        self.logger.error(error_msg)
    
    def log_warning(self, message: str):
        """
        Registrar una advertencia.
        
        Este método registra mensajes de advertencia que indican
        situaciones inusuales pero no críticas que podrían requerir
        atención futura.
        
        Args:
            message: Mensaje descriptivo de la advertencia
            
        Ejemplos:
            >>> logger.log_warning("API respondiendo lentamente")
            >>> logger.log_warning("Valor fuera de rango detectado")
        """
        self.logger.warning(message)
    
    def log_info(self, message: str):
        """
        Registrar información general.
        
        Este método registra mensajes informativos sobre el estado
        y operación normal de la aplicación. Útil para seguimiento
        y debugging durante desarrollo.
        
        Args:
            message: Mensaje informativo
            
        Ejemplos:
            >>> logger.log_info("Aplicación iniciada correctamente")
            >>> logger.log_info("Conexión a API establecida")
            >>> logger.log_info("Proceso completado en 5.2s")
        """
        self.logger.info(message)


def setup_simple_logging():
    """
    Configurar logging simple para la aplicación.
    
    Esta función configura un sistema de logging básico con:
    - Directorio de logs automático
    - Formato estándar con timestamp
    - Rotación de archivos para evitar crecimiento excesivo
    - Nivel DEBUG para máximo detalle
    
    Returns:
        SimpleLogger: Instancia de logger configurado
        
    Note:
        Crea el directorio 'logs' si no existe
        Configura rotación de 1MB con 5 backups
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Formato de logging
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para archivo con rotación
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "trader_simple.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    return SimpleLogger("trader_simple")