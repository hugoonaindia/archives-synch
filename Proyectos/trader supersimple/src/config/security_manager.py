"""
Gestión segura de credenciales y configuración

Este módulo proporciona herramientas para manejar de forma segura
las credenciales de API y configuración de la aplicación.
Implementa validación básica y manejo de múltiples fuentes
(entorno, archivos).

Funcionalidades principales:
- Manejo de credenciales API con validación
- Carga desde variables de entorno o archivos
- Encriptación básica (placeholder para implementación completa)
- Gestión de configuración general de la aplicación

Ejemplos:
    >>> security = SecurityManager()
    >>> creds = security.load_credentials_from_env()
    >>> if creds:
    ...     security.save_credentials(creds)
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class ApiCredentials:
    """
    Credenciales de API con manejo seguro.
    
    Esta clase almacena de forma estructurada las credenciales
    necesarias para la conexión con APIs financieras. Incluye
    validación básica y métodos de serialización.
    
    Atributos:
        base_url: URL base de la API
        api_token: Token de autenticación de API
        admin_token: Token de administrador (opcional)
        actor_id: ID del actor/usuario
        
    Ejemplos:
        >>> creds = ApiCredentials(
        ...     base_url="https://api.example.com",
        ...     api_token="token123",
        ...     admin_token="admin456",
        ...     actor_id="user789"
        ... )
        >>> creds_dict = creds.to_dict()
    """
    
    base_url: str
    api_token: str
    admin_token: str
    actor_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertir credenciales a diccionario.
        
        Returns:
            Dict: Diccionario con todas las credenciales
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiCredentials':
        """
        Crear instancia desde diccionario.
        
        Args:
            data: Diccionario con credenciales
            
        Returns:
            ApiCredentials: Nueva instancia creada
        """
        return cls(**data)


class SecurityManager:
    """
    Gestión segura de credenciales y configuración.
    
    Esta clase proporciona una interfaz unificada para manejar credenciales
    de API y configuración de la aplicación con múltiples fuentes de datos
    y validación de seguridad.
    
    Atributos:
        config_dir: Directorio donde se almacenan configuraciones
        credentials_file: Archivo para credenciales
        config_file: Archivo para configuración general
        logger: Logger para operaciones seguras
        credentials: Credenciales cargadas actualmente
        
    Ejemplos:
        >>> security = SecurityManager("/etc/myapp")
        >>> creds = security.load_credentials_from_env()
        >>> if security.validate_credentials(creds):
        ...     security.save_credentials(creds)
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Inicializar gestor de seguridad.
        
        Args:
            config_dir: Directorio de configuración (por defecto: ./config)
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.credentials_file = self.config_dir / "credentials.enc"
        self.config_file = self.config_dir / "config.json"
        
        self.logger = logging.getLogger("security_manager")
        self.credentials: Optional[ApiCredentials] = None
        
    def load_credentials_from_env(self) -> Optional[ApiCredentials]:
        """Cargar credenciales desde variables de entorno"""
        base_url = os.getenv("ALPACA_BASE_URL", "").strip()
        api_token = os.getenv("ALPACA_API_TOKEN", "").strip()
        admin_token = os.getenv("ALPACA_ADMIN_TOKEN", "").strip()
        actor_id = os.getenv("ALPACA_ACTOR_ID", "").strip()
        
        if all([base_url, api_token, admin_token, actor_id]):
            self.credentials = ApiCredentials(
                base_url=base_url,
                api_token=api_token,
                admin_token=admin_token,
                actor_id=actor_id
            )
            self.logger.info("Credenciales cargadas desde variables de entorno")
            return self.credentials
        
        self.logger.warning("No se encontraron credenciales en variables de entorno")
        return None
    
    def load_credentials_from_file(self) -> Optional[ApiCredentials]:
        """Cargar credenciales desde archivo (con manejo básico)"""
        if not self.credentials_file.exists():
            return None
        
        try:
            with open(self.credentials_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Simplemente cargamos - en producción se debería desencriptar
            self.credentials = ApiCredentials.from_dict(data)
            self.logger.info("Credenciales cargadas desde archivo")
            return self.credentials
            
        except Exception as e:
            self.logger.error(f"Error al cargar credenciales: {e}")
            return None
    
    def save_credentials(self, credentials: ApiCredentials, encrypt: bool = False) -> bool:
        """Guardar credenciales de forma segura"""
        try:
            data = credentials.to_dict()
            
            if encrypt:
                # En producción, aquí se debería implementar encriptación
                # Por ahora guardamos en formato JSON básico
                self.logger.warning("Encriptación no implementada - guardando en texto plano")
            
            with open(self.credentials_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.credentials = credentials
            self.logger.info("Credenciales guardadas exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al guardar credenciales: {e}")
            return False
    
    def get_credentials(self) -> Optional[ApiCredentials]:
        """Obtener credenciales con fallback"""
        if self.credentials:
            return self.credentials
        
        # Intentar cargar desde variables de entorno primero
        if self.load_credentials_from_env():
            return self.credentials
        
        # Luego intentar desde archivo
        if self.load_credentials_from_file():
            return self.credentials
        
        return None
    
    def validate_credentials(self, credentials: ApiCredentials) -> bool:
        """Validar credenciales mínimas"""
        required_fields = {
            'base_url': bool(credentials.base_url),
            'api_token': bool(credentials.api_token),
            'admin_token': bool(credentials.admin_token),
            'actor_id': bool(credentials.actor_id)
        }
        
        missing = [field for field, valid in required_fields.items() if not valid]
        
        if missing:
            self.logger.error(f"Credenciales incompletas: faltan {missing}")
            return False
        
        # Validar formato de URL
        if not credentials.base_url.startswith(('http://', 'https://')):
            self.logger.error(f"URL de base inválida: {credentials.base_url}")
            return False
        
        return True
    
    def clear_credentials(self) -> bool:
        """Borrar credenciales almacenadas"""
        try:
            if self.credentials_file.exists():
                self.credentials_file.unlink()
                self.credentials = None
                self.logger.info("Credenciales borradas exitosamente")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error al borrar credenciales: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Cargar configuración general"""
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error al cargar configuración: {e}")
            return {}
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Guardar configuración general"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("Configuración guardada exitosamente")
            return True
        except Exception as e:
            self.logger.error(f"Error al guardar configuración: {e}")
            return False