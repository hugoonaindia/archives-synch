"""
Clinical/Trading Automation Engine - Source Package
"""

__version__ = "1.0.0"
__author__ = "Clinical/Trading Development Team"
__description__ = "A minimalist premium interface for clinical and trading automation"

try:
    from .models.database import Database, DatabaseConfig
    from .services.logging_service import AsyncLoggingService
    from .ui.components.base import BaseComponent, HeaderComponent, SidebarComponent
except ImportError as e:
    # Log the import error but don't fail the package loading
    print(f"Warning: Some modules could not be imported: {e}")
    Database = None
    DatabaseConfig = None
    AsyncLoggingService = None
    BaseComponent = None
    HeaderComponent = None
    SidebarComponent = None

__all__ = [
    'Database',
    'DatabaseConfig',
    'AsyncLoggingService', 
    'BaseComponent',
    'HeaderComponent',
    'SidebarComponent'
]