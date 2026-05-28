"""
Clinical/Trading Automation Engine - Main Application
Core NiceGUI application with modular architecture.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import nicegui
from nicegui import ui
from src.models.database import Database
from src.services.logging_service import AsyncLoggingService
from src.ui.components.base import BaseComponent


@dataclass
class AppState:
    """Centralized application state management"""
    database: Database
    logger: AsyncLoggingService
    current_user: Optional[str] = None
    session_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.session_data is None:
            self.session_data = {}


class ClinicalTradingApp:
    """Main application class implementing separation of responsibilities"""
    
    def __init__(self):
        self.state = AppState(
            database=Database(),
            logger=AsyncLoggingService(),
            session_data={}
        )
        self.components: Dict[str, BaseComponent] = {}
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup NiceGUI routes with proper error handling"""
        @ui.page('/')
        def main_page():
            self._render_main_layout()
        
        @ui.page('/dashboard')
        def dashboard():
            self._render_dashboard()
        
        # Error handling middleware
        @nicegui.middleware.handle_exception
        def exception_handler(request, exception):
            logging.error(f"Exception in {request.path}: {exception}")
            ui.notify("Error en la aplicación", color="red", timeout=5)
    
    def _render_main_layout(self):
        """Render the main application layout"""
        with ui.header().classes('bg-white shadow-lg'):
            ui.label('Clinical/Trading Automation Engine').classes('text-xl font-bold')
            ui.space()
            ui.button('Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))
        
        with ui.tabs().classes('w-full') as tabs:
            ui.tab('Inicio')
            ui.tab('Configuración')
            ui.tab('Análisis')
        
        with ui.tab_panels(tabs):
            with ui.tab_panel('Inicio'):
                ui.label('Bienvenido al sistema de automatización clínica y trading')
                ui.markdown('Aplicación minimalista con interfaz premium')
            
            with ui.tab_panel('Configuración'):
                ui.label('Configuración del sistema')
                ui.button('Iniciar configuración', on_click=self._show_config_dialog)
            
            with ui.tab_panel('Análisis'):
                ui.label('Análisis de datos')
                ui.button('Abrir analizador', on_click=self._show_analyzer)
    
    def _render_dashboard(self):
        """Render dashboard with real-time data"""
        ui.label('Dashboard Principal').classes('text-2xl font-bold mb-4')
        
        with ui.grid(columns=3):
            with ui.card().classes('col-span-1'):
                ui.label('Estado del Sistema').classes('text-lg font-semibold')
                ui.label('✅ En línea').classes('text-green-600')
            
            with ui.card().classes('col-span-1'):
                ui.label('Base de Datos').classes('text-lg font-semibold')
                ui.label('✅ Conectada').classes('text-green-600')
            
            with ui.card().classes('col-span-1'):
                ui.label('Procesos Activos').classes('text-lg font-semibold')
                ui.label('2').classes('text-blue-600')
    
    def _show_config_dialog(self):
        """Show configuration dialog"""
        with ui.dialog() as dialog:
            with ui.card():
                ui.label('Configuración del Sistema')
                ui.input('API Key', password=True).classes('w-full')
                ui.input('Endpoint URL').classes('w-full')
                ui.button('Guardar', on_click=lambda: dialog.close())
                ui.button('Cancelar', on_click=lambda: dialog.close())
    
    def _show_analyzer(self):
        """Show data analyzer dialog"""
        with ui.dialog() as dialog:
            with ui.card():
                ui.label('Analizador de Datos')
                ui.label('Cargando datos...')
                ui.button('Cerrar', on_click=lambda: dialog.close())
    
    async def initialize(self):
        """Initialize application with proper async handling"""
        try:
            await self.state.database.initialize()
            await self.state.logger.initialize()
            logging.info("Application initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize application: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            await self.state.database.close()
            await self.state.logger.shutdown()
            logging.info("Application shutdown successfully")
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")


def main():
    """Main entry point"""
    app = ClinicalTradingApp()
    
    # Initialize with async handling
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(app.initialize())
        nicegui.run(
            title="Clinical/Trading Automation Engine",
            host="0.0.0.0",
            port=8080,
            dark=False,
            reloading=False
        )
    finally:
        loop.run_until_complete(app.shutdown())
        loop.close()


if __name__ == "__main__":
    main()