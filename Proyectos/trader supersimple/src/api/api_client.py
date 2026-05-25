"""
Cliente API mejorado con manejo de errores y reintentos
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request
from ..utils.error_handler import retry_with_backoff, CircuitBreaker, ErrorLogger
from ..config.security_manager import SecurityManager, ApiCredentials


class ApiClient:
    """Cliente API con manejo robusto de errores"""
    
    def __init__(self, security_manager: SecurityManager, error_logger: ErrorLogger):
        self.security_manager = security_manager
        self.error_logger = error_logger
        
        self.credentials = security_manager.get_credentials()
        if not self.credentials:
            raise ValueError("No se encontraron credenciales válidas")
        
        # Circuit breaker para operaciones de red
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=(ConnectionError, TimeoutError, URLError)
        )
        
        self.base_url = self.credentials.base_url.rstrip("/")
        self.timeout = 20
        
        # Configurar reintentos para operaciones críticas
        self.retry_train = retry_with_backoff(
            max_retries=3,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True
        )
        
        self.retry_predict = retry_with_backoff(
            max_retries=2,
            base_delay=0.5,
            exponential_base=1.5,
            jitter=True
        )
    
    def _build_url(self, path: str) -> str:
        """Construir URL completa"""
        return f"{self.base_url}{path}"
    
    def _build_headers(self, use_admin: bool = False) -> Dict[str, str]:
        """Construir headers de autenticación"""
        headers = {"Content-Type": "application/json"}
        
        if self.credentials.api_token:
            headers["X-DT-Trade-Token"] = self.credentials.api_token
        
        if use_admin and self.credentials.admin_token:
            headers["X-DT-Trade-Admin-Token"] = self.credentials.admin_token
        
        if self.credentials.actor_id:
            headers["X-DT-Actor"] = self.credentials.actor_id
        
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
            
            self.error_logger.log_error(
                Exception(error_msg),
                f"Petición {method} {path} falló con HTTP {e.code}",
                {"status_code": e.code, "url": url}
            )
            raise RuntimeError(error_msg) from e
            
        except URLError as e:
            error_msg = f"No se pudo conectar con la API: {e}"
            self.error_logger.log_error(
                Exception(error_msg),
                f"Petición {method} {path} falló por conexión",
                {"url": url, "reason": str(e)}
            )
            raise RuntimeError(error_msg) from e
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def health_check(self) -> Dict[str, Any]:
        """Verificar salud de la API"""
        try:
            response = self._make_request("GET", "/api/v1/health")
            self.error_logger.log_info("Verificación de salud exitosa")
            return response
        except Exception as e:
            self.error_logger.log_error(e, "Verificación de salud fallida")
            raise
    
    @retry_with_backoff(max_retries=3, base_delay=2.0)
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
            self.error_logger.log_info(
                f"Entrenamiento iniciado para {ticker}",
                {"ticker": ticker, "profile": profile, "sample_periods": sample_periods}
            )
            return response
        except Exception as e:
            self.error_logger.log_error(
                e, 
                f"Error al iniciar entrenamiento para {ticker}",
                {"ticker": ticker, "profile": profile}
            )
            raise
    
    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def promote_to_paper(self, run_id: str) -> Dict[str, Any]:
        """Promover ejecución a ambiente paper"""
        payload = {"run_id": run_id, "target": "paper"}
        
        try:
            response = self._make_request(
                "POST", 
                "/api/v1/registry/promote", 
                payload
            )
            self.error_logger.log_info(
                f"Ejecución {run_id} promovida a paper",
                {"run_id": run_id}
            )
            return response
        except Exception as e:
            self.error_logger.log_error(
                e, 
                f"Error al promover ejecución {run_id} a paper",
                {"run_id": run_id}
            )
            raise
    
    def is_available(self) -> bool:
        """Verificar si la API está disponible"""
        try:
            self.health_check()
            return True
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado completo del cliente"""
        return {
            "api_available": self.is_available(),
            "credentials_valid": self.security_manager.validate_credentials(self.credentials),
            "circuit_breaker_state": self.circuit_breaker.state,
            "last_check": time.time()
        }