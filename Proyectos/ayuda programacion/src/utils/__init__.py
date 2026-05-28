"""
Utilities module for common functionality.
"""

import asyncio
import hashlib
import json
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid


class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple[str, str]:
        """Hash a password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Using SHA-256 for password hashing (in production, use bcrypt or Argon2)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Verify a password against its hash"""
        computed_hash, _ = SecurityUtils.hash_password(password, salt)
        return computed_hash == hashed_password
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Basic input sanitization"""
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '$', '(', ')', '[', ']', '{', '}']
        for char in dangerous_chars:
            text = text.replace(char, '')
        return text


class DataProcessor:
    """Data processing utilities"""
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """Safely convert value to int"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100) -> str:
        """Truncate text to maximum length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    @staticmethod
    def merge_dictionaries(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two dictionaries recursively"""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataProcessor.merge_dictionaries(result[key], value)
            else:
                result[key] = value
        return result


class ValidationUtils:
    """Validation utility functions"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Basic email validation"""
        if not email or '@' not in email:
            return False
        
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain or '.' not in domain:
            return False
        
        return True
    
    @staticmethod
    def is_valid_username(username: str, min_length: int = 3, max_length: int = 20) -> bool:
        """Validate username format"""
        if not username:
            return False
        
        if len(username) < min_length or len(username) > max_length:
            return False
        
        # Username should only contain alphanumeric characters and underscores
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        return all(char in allowed_chars for char in username)
    
    @staticmethod
    def is_valid_date_string(date_string: str, format_string: str = "%Y-%m-%d") -> bool:
        """Validate date string format"""
        try:
            datetime.strptime(date_string, format_string)
            return True
        except ValueError:
            return False


class AsyncUtils:
    """Async utility functions"""
    
    @staticmethod
    async def run_in_executor(func, *args, **kwargs):
        """Run a function in an executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    @staticmethod
    async def gather_with_timeout(coroutines, timeout: float = 30.0) -> List[Any]:
        """Run multiple coroutines with timeout"""
        tasks = [asyncio.create_task(coro) for coro in coroutines]
        done, pending = await asyncio.wait(tasks, timeout=timeout)
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
        
        if pending:
            raise asyncio.TimeoutError(f"Timeout after {timeout} seconds")
        
        return [task.result() for task in done]
    
    @staticmethod
    def create_task_with_timeout(coro, timeout: float = 30.0):
        """Create a task with automatic timeout"""
        async def wrapper():
            try:
                return await asyncio.wait_for(coro, timeout)
            except asyncio.TimeoutError:
                raise Exception(f"Task timed out after {timeout} seconds")
        
        return asyncio.create_task(wrapper())


class CacheManager:
    """Simple in-memory cache manager"""
    
    def __init__(self, default_timeout: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_timeout = default_timeout
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if datetime.now() > entry['expires_at']:
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, timeout: int = None) -> None:
        """Set value in cache with timeout"""
        if timeout is None:
            timeout = self.default_timeout
        
        expires_at = datetime.now() + timedelta(seconds=timeout)
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
    
    def delete(self, key: str) -> None:
        """Delete value from cache"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        now = datetime.now()
        expired_keys = [key for key, entry in self._cache.items() if now > entry['expires_at']]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)


# Global cache instance
_cache = CacheManager()


def get_cache() -> CacheManager:
    """Get the global cache instance"""
    return _cache


def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())


def to_json_safe(obj: Any) -> Any:
    """Convert object to JSON-safe format"""
    if isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_json_safe(item) for item in obj]
    elif isinstance(obj, tuple):
        return [to_json_safe(item) for item in obj]
    elif isinstance(obj, set):
        return [to_json_safe(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return to_json_safe(obj.__dict__)
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        return str(obj)