"""
Versión mejorada del Trader LSTM con arquitectura modular
"""

import logging
import sys
import time
from pathlib import Path

# Agregar directorio raíz al path para imports relativos
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.security_manager import SecurityManager
from utils.error_handler import ErrorLogger, HealthChecker
from api.api_client import ApiClient


def setup_logging():
    """Configurar logging estructurado"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Formato de logging
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Handler para archivo
    file_handler = logging.FileHandler(
        log_dir / "trader_improved.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return root_logger


def main():
    """Función principal de la aplicación mejorada"""
    print("🚀 Iniciando Trader LSTM versión mejorada...")
    
    # Configurar logging
    logger = setup_logging()
    logger.info("Aplicación iniciada")
    
    try:
        # Inicializar componentes de seguridad
        security_manager = SecurityManager()
        error_logger = ErrorLogger("trader_lstm")
        health_checker = HealthChecker(error_logger)
        
        # Verificar credenciales
        logger.info("Verificando credenciales...")
        credentials = security_manager.get_credentials()
        
        if not credentials:
            error_logger.log_error(
                Exception("Credenciales no encontradas"),
                "No se encontraron credenciales válidas"
            )
            print("❌ Error: No se encontraron credenciales válidas")
            print("Configura tus credenciales en config/.env usando config/.env.example como plantilla")
            return 1
        
        # Validar credenciales
        if not security_manager.validate_credentials(credentials):
            error_logger.log_error(
                Exception("Credenciales inválidas"),
                "Las credenciales no pasaron la validación"
            )
            print("❌ Error: Credenciales inválidas")
            return 1
        
        logger.info("✓ Credenciales válidas")
        
        # Inicializar cliente API
        logger.info("Inicializando cliente API...")
        api_client = ApiClient(security_manager, error_logger)
        
        # Verificar salud del sistema
        logger.info("Verificando salud del sistema...")
        
        # Verificar API
        api_healthy = health_checker.check_component(
            "api",
            api_client.is_available
        )
        
        if not api_healthy:
            error_logger.log_error(
                Exception("API no disponible"),
                "La API no está disponible en este momento"
            )
            print("⚠️  Advertencia: La API no está disponible, se usará modo offline")
        
        # Mostrar estado del sistema
        system_health = health_checker.get_system_health()
        logger.info("Estado del sistema:")
        for component, status in system_health.items():
            logger.info(f"  {component}: {status['status']} (último check: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['last_check']))})")
        
        # Aquí iría la lógica principal de la aplicación
        # Por ahora, un simple bucle de demostración
        
        logger.info("Iniciando bucle principal...")
        loop_count = 0
        
        while loop_count < 10:  # Bucle de demostración
            try:
                loop_count += 1
                logger.info(f"Loop {loop_count}")
                
                # Simular trabajo
                time.sleep(2)
                
                # Verificar salud periódicamente
                if loop_count % 3 == 0:
                    api_healthy = health_checker.check_component(
                        "api",
                        api_client.is_available
                    )
                    logger.info(f"API status: {'healthy' if api_healthy else 'unhealthy'}")
                
            except KeyboardInterrupt:
                logger.info("Interrupción recibida, deteniendo...")
                break
            except Exception as e:
                error_logger.log_error(e, f"Error en loop {loop_count}")
                time.sleep(5)  # Esperar antes de reintentar
        
        logger.info("Aplicación finalizada exitosamente")
        print("✅ Aplicación finalizada correctamente")
        return 0
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        print(f"❌ Error crítico: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())