"""
Cliente API simple con manejo de errores y reintentos

Este módulo proporciona un cliente HTTP robusto para la comunicación
con APIs financieras. Incluye manejo de errores, reintentos automáticos
y logging integrado para depuración.

Características principales:
- Reintentos con exponential backoff
- Manejo robusto de errores HTTP
- Logging detallado de operaciones
- Timeout configurable
- Soporte para autenticación múltiple

Ejemplos:
    >>> client = SimpleApiClient(
    ...     base_url="https://api.example.com",
    ...     api_token="token123",
    ...     admin_token="admin456",
    ...     actor_id="user789"
    ... )
    >>> status = client.is_available()
    >>> if status:
    ...     data = client.health_check()
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request
from ..utils.simple_error_handler import retry_with_backoff_simple


class SimpleApiClient:
    """
    Cliente API simple con manejo robusto de errores.
    
    Esta clase proporciona una interfaz sencilla pero robusta para
    comunicación con APIs financieras. Incluye manejo de errores,
    reintentos automáticos y logging para facilitar la depuración.
    
    Atributos:
        base_url: URL base de la API
        api_token: Token de autenticación
        admin_token: Token de administrador
        actor_id: ID del actor
        timeout: Timeout para peticiones en segundos
        
    Ejemplos:
        >>> client = SimpleApiClient(
        ...     base_url="https://api.alpaca.markets",
        ...     api_token="your_token_here",
        ...     admin_token="admin_token",
        ...     actor_id="trader_bot"
        ... )
        >>> if client.is_available():
        ...     response = client.health_check()
    """
    
    def __init__(self, base_url: str, api_token: str, admin_token: str, actor_id: str):
        """
        Inicializar el cliente API.
        
        Args:
            base_url: URL base de la API (sin trailing slash)
            api_token: Token de autenticación de la API
            admin_token: Token de administrador (opcional)
            actor_id: ID del actor/usuario
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token.strip()
        self.admin_token = admin_token.strip()
        self.actor_id = actor_id.strip()
        self.timeout = 20
        
        # Configurar logging
        self.logger = logging.getLogger("simple_api_client")
    
    def _build_url(self, path: str) -> str:
        """Construir URL completa"""
        return f"{self.base_url}{path}"
    
    def _build_headers(self, use_admin: bool = False) -> Dict[str, str]:
        """Construir headers de autenticación"""
        headers = {"Content-Type": "application/json"}
        
        if self.api_token:
            headers["X-DT-Trade-Token"] = self.api_token
        
        if use_admin and self.admin_token:
            headers["X-DT-Trade-Admin-Token"] = self.admin_token
        
        if self.actor_id:
            headers["X-DT-Actor"] = self.actor_id
        
        return headers
    
    def _decode_response(self, data: bytes) -> Dict[str, Any]:
        """Decodificar respuesta JSON"""
        text = data.decode("utf-8", errors="replace")
        if not text.strip():
            return {}
        
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise ValueError("Respuesta API inválida - no es un objeto JSON")
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al decodificar JSON: {e}")
    
    def _make_request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        use_admin: bool = False,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Realizar petición HTTP con manejo de errores"""
        url = self._build_url(path)
        headers = self._build_headers(use_admin)
        
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        
        req = Request(
            url=url,
            method=method,
            data=data,
            headers=headers
        )
        
        try:
            with urlopen(req, timeout=timeout or self.timeout) as response:
                response_data = response.read()
                return self._decode_response(response_data)
                
        except HTTPError as e:
            response_data = e.read()
            try:
                parsed_error = self._decode_response(response_data)
                error_msg = parsed_error.get("error") or parsed_error.get("message") or f"HTTP {e.code}"
            except ValueError:
                error_msg = f"HTTP {e.code}: {e.reason}"
            
            self.logger.error(f"Petición {method} {path} falló con HTTP {e.code}: {error_msg}")
            raise RuntimeError(error_msg) from e
            
        except URLError as e:
            error_msg = f"No se pudo conectar con la API: {e}"
            self.logger.error(f"Petición {method} {path} falló por conexión: {error_msg}")
            raise RuntimeError(error_msg) from e
    
    @retry_with_backoff_simple(max_retries=3, base_delay=2.0)
    def health_check(self) -> Dict[str, Any]:
        """Verificar salud de la API"""
        try:
            response = self._make_request("GET", "/api/v1/health")
            self.logger.info("Verificación de salud exitosa")
            return response
        except Exception as e:
            self.logger.error(f"Verificación de salud fallida: {e}")
            raise
    
    @retry_with_backoff_simple(max_retries=3, base_delay=2.0)
    def train_sequence(self, ticker: str, profile: str, sample_periods: int) -> Dict[str, Any]:
        """Entrenar modelo de secuencia"""
        payload = {
            "ticker": ticker,
            "profile": profile,
            "sample_periods": sample_periods
        }
        
        try:
            response = self._make_request(
                "POST", 
                "/api/v1/train/sequence", 
                payload
            )
            self.logger.info(f"Entrenamiento iniciado para {ticker}")
            return response
        except Exception as e:
            self.logger.error(f"Error al iniciar entrenamiento para {ticker}: {e}")
            raise
    
    @retry_with_backoff_simple(max_retries=2, base_delay=1.0)
    def promote_to_paper(self, run_id: str) -> Dict[str, Any]:
        """Promover ejecución a ambiente paper"""
        payload = {"run_id": run_id, "target": "paper"}
        
        try:
            response = self._make_request(
                "POST", 
                "/api/v1/registry/promote", 
                payload
            )
            self.logger.info(f"Ejecución {run_id} promovida a paper")
            return response
        except Exception as e:
            self.logger.error(f"Error al promover ejecución {run_id} a paper: {e}")
            raise
    
    def is_available(self) -> bool:
        """Verificar si la API está disponible"""
        try:
            self.health_check()
            return True
        except Exception:
            return False