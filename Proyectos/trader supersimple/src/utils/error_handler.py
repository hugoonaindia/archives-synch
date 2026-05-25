"""
Manejo robusto de errores con reintentos y logging estructurado
"""

import logging
import random
import time
from typing import Callable, Any, Optional
from functools import wraps


class CircuitBreaker:
    """Implementa pattern Circuit Breaker para evitar cascadas de fallos"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, 
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half_open"
                else:
                    raise RuntimeError("Circuit breaker está abierto - operación bloqueada")
            
            try:
                result = func(*args, **kwargs)
                if self.state == "half_open":
                    self.state = "closed"
                    self.failure_count = 0
                return result
            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logging.error(f"Circuit breaker abierto después de {self.failure_count} fallos")
                
                raise e
        
        return wrapper


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> Callable:
    """
    Decorador para reintentos con exponential backoff
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
                        raise
                    
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logging.warning(
                        f"Intento {attempt + 1}/{max_retries} para {func.__name__} falló. "
                        f"Reintentando en {delay:.2f}s... Error: {str(e)}"
                    )
                    time.sleep(delay)
            
            return None
        
        return wrapper
    return decorator


class ErrorLogger:
    """Logging estructurado con categorías y niveles"""
    
    def __init__(self, name: str = "trader_lstm"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_error(self, error: Exception, context: Optional[str] = None, 
                 extra_data: Optional[dict] = None):
        """Registrar error con contexto"""
        error_msg = f"Error: {str(error)}"
        if context:
            error_msg = f"Contexto: {context} - {error_msg}"
        
        log_data = {"error": str(error), "type": type(error).__name__}
        if extra_data:
            log_data.update(extra_data)
        
        self.logger.error(error_msg, extra={"details": log_data})
    
    def log_warning(self, message: str, extra_data: Optional[dict] = None):
        """Registrar advertencia"""
        log_data = {"message": message}
        if extra_data:
            log_data.update(extra_data)
        
        self.logger.warning(message, extra={"details": log_data})
    
    def log_info(self, message: str, extra_data: Optional[dict] = None):
        """Registrar información"""
        log_data = {"message": message}
        if extra_data:
            log_data.update(extra_data)
        
        self.logger.info(message, extra={"details": log_data})


class HealthChecker:
    """Monitoreo de salud del sistema"""
    
    def __init__(self, error_logger: ErrorLogger):
        self.error_logger = error_logger
        self.health_status = {}
        self.last_check_time = {}
    
    def check_component(self, component_name: str, check_func: Callable) -> bool:
        """Verificar salud de un componente"""
        try:
            result = check_func()
            self.health_status[component_name] = "healthy"
            self.last_check_time[component_name] = time.time()
            return result
        except Exception as e:
            self.health_status[component_name] = "unhealthy"
            self.last_check_time[component_name] = time.time()
            self.error_logger.log_error(e, f"Verificación de salud de {component_name}")
            return False
    
    def get_system_health(self) -> dict:
        """Obtener estado general del sistema"""
        current_time = time.time()
        status = {}
        
        for component, health in self.health_status.items():
            last_check = self.last_check_time.get(component, 0)
            age = current_time - last_check
            
            status[component] = {
                "status": health,
                "last_check": last_check,
                "age_seconds": age,
                "is_healthy": health == "healthy"
            }
        
        return status