"""
Script de migración de configuración para el Trader LSTM
"""

import os
import json
import shutil
from pathlib import Path
from src.config.security_manager import SecurityManager, ApiCredentials
from src.utils.error_handler import ErrorLogger


def migrate_configuration():
    """Migrar configuración antigua al nuevo sistema"""
    print("Iniciando migración de configuración...")
    
    # Inicializar componentes
    error_logger = ErrorLogger("migrator")
    security_manager = SecurityManager()
    
    # Directorios
    old_dir = Path.cwd()
    new_config_dir = old_dir / "config"
    new_src_dir = old_dir / "src"
    
    # Crear directorios si no existen
    new_config_dir.mkdir(exist_ok=True)
    new_src_dir.mkdir(exist_ok=True)
    
    # 1. Migrar credenciales de entorno variables o crear archivo .env
    env_file = new_config_dir / ".env"
    
    if not env_file.exists():
        print("Creando archivo .env...")
        
        # Intentar cargar credenciales desde variables de entorno
        base_url = os.getenv("ALPACA_BASE_URL", "")
        api_token = os.getenv("ALPACA_API_TOKEN", "")
        admin_token = os.getenv("ALPACA_ADMIN_TOKEN", "")
        actor_id = os.getenv("ALPACA_ACTOR_ID", "")
        
        if all([base_url, api_token, admin_token, actor_id]):
            # Guardar en .env
            with open(env_file, 'w') as f:
                f.write(f"ALPACA_BASE_URL={base_url}\n")
                f.write(f"ALPACA_API_TOKEN={api_token}\n")
                f.write(f"ALPACA_ADMIN_TOKEN={admin_token}\n")
                f.write(f"ALPACA_ACTOR_ID={actor_id}\n")
            print("✓ Credenciales guardadas en .env")
        else:
            # Copiar .env.example como plantilla
            if (old_dir / ".env.example").exists():
                shutil.copy2(old_dir / ".env.example", env_file)
                print("✓ Archivo .env creado con plantilla")
            else:
                # Crear archivo básico
                with open(env_file, 'w') as f:
                    f.write("# Configuración de API para Trader LSTM\n")
                    f.write("# Rellena tus credenciales aquí\n")
                    f.write("ALPACA_BASE_URL=https://paper-api.alpaca.markets\n")
                    f.write("ALPACA_API_TOKEN=\n")
                    f.write("ALPACA_ADMIN_TOKEN=\n")
                    f.write("ALPACA_ACTOR_ID=\n")
                print("✓ Archivo .env creado (requiere configuración)")
    
    # 2. Migrar configuración existente
    config_file = new_config_dir / "config.json"
    
    if not config_file.exists():
        print("Migrando configuración existente...")
        
        # Configuración por defecto
        default_config = {
            "loop_interval_ms": 4000,
            "loop_retry_ms": 1200,
            "max_loop_errors": 3,
            "max_drawdown_stop_pct": 8.0,
            "tickers": ["AAPL", "MSFT"],
            "sample_periods": 252,
            "prediction_horizon": 5,
            "log_level": "INFO",
            "log_file": "logs/trader_app.log"
        }
        
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print("✓ Configuración migrada")
    
    # 3. Verificar credenciales
    credentials = security_manager.get_credentials()
    if credentials:
        print("✓ Credenciales válidas encontradas")
        print(f"  - Base URL: {credentials.base_url}")
        print(f"  - Actor ID: {credentials.actor_id}")
    else:
        print("⚠ No se encontraron credenciales válidas")
        print("  Configura tus credenciales en el archivo .env")
    
    # 4. Crear script de ejecución mejorado
    run_script = old_dir / "run_trader_improved.sh"
    
    script_content = """#!/bin/bash
# Script mejorado para ejecutar el Trader LSTM

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activar entorno virtual
if [ -d "$DIR/.venv" ]; then
    echo "Activando entorno virtual..."
    source "$DIR/.venv/bin/activate"
fi

# Verificar credenciales
if [ ! -f "$DIR/config/.env" ]; then
    echo "Error: No se encontró archivo de configuración en $DIR/config/.env"
    echo "Copia $DIR/config/.env.example a $DIR/config/.env y configura tus credenciales"
    exit 1
fi

# Ejecutar aplicación
echo "Iniciando Trader LSTM..."
cd "$DIR"
python -m src.main
"""
    
    with open(run_script, 'w') as f:
        f.write(script_content)
    
    os.chmod(run_script, 0o755)
    print("✓ Script de ejecución mejorado creado (run_trader_improved.sh)")
    
    # 5. Crear requirements.txt si no existe
    req_file = old_dir / "requirements.txt"
    
    if not req_file.exists():
        requirements = """customtkinter>=5.1.0
tensorflow>=2.12.0
numpy>=1.24.0
pandas>=2.0.0
ta-lib>=0.4.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0
jupyter>=1.0.0
optuna>=3.0.0
pyyaml>=6.0
prometheus-client>=0.17.0
"""
        
        with open(req_file, 'w') as f:
            f.write(requirements)
        
        print("✓ requirements.txt creado")
    
    print("\n✅ Migración completada!")
    print("\nPróximos pasos:")
    print("1. Configura tus credenciales en config/.env")
    print("2. Ejecuta 'bash run_trader_improved.sh' para iniciar la aplicación mejorada")
    print("3. Revisa los logs en logs/ para verificar que todo funciona correctamente")


if __name__ == "__main__":
    migrate_configuration()