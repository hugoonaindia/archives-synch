"""
Versión simplificada del Trader LSTM con mejoras de estabilidad
"""

import logging
import sys
import time
from pathlib import Path

# Agregar directorio raíz al path para imports relativos
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.simple_error_handler import setup_simple_logging, SimpleLogger
from src.api.simple_api_client import SimpleApiClient


def main():
    """Función principal de la aplicación mejorada y simplificada"""
    print("🚀 Iniciando Trader LSTM versión mejorada y simplificada...")
    
    # Configurar logging
    logger = setup_simple_logging()
    logger.log_info("Aplicación iniciada")
    
    try:
        # Cargar configuración directamente (como en el original)
        base_url = "https://paper-api.alpaca.markets"
        api_token = ""  # Se mantendrá como en el original
        admin_token = ""  # Se mantendrá como en el original
        actor_id = ""   # Se mantendrá como en el original
        
        # Inicializar cliente API mejorado
        logger.log_info("Inicializando cliente API mejorado...")
        api_client = SimpleApiClient(base_url, api_token, admin_token, actor_id)
        
        # Verificar salud del sistema
        logger.log_info("Verificando salud del sistema...")
        
        # Verificar API
        try:
            api_healthy = api_client.is_available()
            if api_healthy:
                logger.log_info("✓ API disponible")
            else:
                logger.log_warning("⚠️ API no disponible, se usará modo offline")
        except Exception as e:
            logger.log_error(e, "Error al verificar API")
            logger.log_warning("⚠️ API no disponible, se usará modo offline")
        
        # Aquí iría la lógica principal de la aplicación
        # Mejorada con manejo de errores y logging
        
        logger.log_info("Iniciando bucle principal...")
        loop_count = 0
        max_loops = 10  # Bucle de demostración
        
        while loop_count < max_loops:
            try:
                loop_count += 1
                logger.log_info(f"Bucle {loop_count}/{max_loops}")
                
                # Simular trabajo con mejor logging
                time.sleep(2)
                
                # Verificar salud periódicamente
                if loop_count % 3 == 0:
                    try:
                        api_healthy = api_client.is_available()
                        status = "healthy" if api_healthy else "unhealthy"
                        logger.log_info(f"API status: {status}")
                    except Exception as e:
                        logger.log_error(e, "Error en verificación de API")
                
            except KeyboardInterrupt:
                logger.log_info("Interrupción recibida, deteniendo...")
                break
            except Exception as e:
                logger.log_error(e, f"Error en loop {loop_count}")
                time.sleep(5)  # Esperar antes de reintentar
        
        logger.log_info("Aplicación finalizada exitosamente")
        print("✅ Aplicación finalizada correctamente")
        return 0
        
    except Exception as e:
        logger.log_error(e, "Error crítico")
        print(f"❌ Error crítico: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())