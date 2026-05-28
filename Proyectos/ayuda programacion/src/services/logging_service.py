"""
Async logging service with proper separation of responsibilities.
Replaces synchronous logging to avoid UI blocking.
"""

import asyncio
import logging
import logging.handlers
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json
from queue import Queue
import threading
from pathlib import Path


@dataclass
class LogConfig:
    """Logging configuration"""
    log_level: str = "INFO"
    log_file: str = "app.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    structured_logging: bool = True


class LogEntry:
    """Structured log entry"""
    
    def __init__(self, level: str, message: str, context: Dict[str, Any] = None):
        self.timestamp = datetime.now()
        self.level = level
        self.message = message
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for structured logging"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'message': self.message,
            'context': self.context
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class AsyncLoggingHandler:
    """Async-compatible logging handler"""
    
    def __init__(self, log_queue: Queue):
        self.log_queue = log_queue
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the logging worker"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()
    
    def stop(self):
        """Stop the logging worker"""
        if self._running:
            self._running = False
            if self._worker_thread:
                self._worker_thread.join(timeout=5)
    
    def _worker(self):
        """Worker thread for processing log entries"""
        while self._running:
            try:
                log_entry = self.log_queue.get(timeout=1)
                if log_entry is None:  # Shutdown signal
                    break
                
                # Process the log entry
                self._process_log_entry(log_entry)
                self.log_queue.task_done()
                
            except Exception as e:
                # Don't let logging errors break the application
                pass
    
    def _process_log_entry(self, log_entry: LogEntry):
        """Process a single log entry"""
        logger = logging.getLogger(log_entry.level)
        log_method = getattr(logger, log_entry.level.lower(), logger.info)
        
        if log_entry.context:
            log_method(f"{log_entry.message} - Context: {log_entry.context}")
        else:
            log_method(log_entry.message)


class AsyncLoggingService:
    """Async logging service with non-blocking operations"""
    
    def __init__(self, config: Optional[LogConfig] = None):
        self.config = config or LogConfig()
        self.log_queue: Queue = Queue()
        self.handler: Optional[AsyncLoggingHandler] = None
        self._logger = logging.getLogger(__name__)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the logging service"""
        if self._initialized:
            return
        
        try:
            # Configure logging
            logging.basicConfig(
                level=getattr(logging, self.config.log_level.upper()),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Setup file handler with rotation
            log_file = Path(self.config.log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count
            )
            
            # Setup console handler
            console_handler = logging.StreamHandler()
            
            # Add handlers to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            
            if self.config.console_output:
                root_logger.addHandler(console_handler)
            
            # Initialize async handler
            self.handler = AsyncLoggingHandler(self.log_queue)
            self.handler.start()
            
            self._initialized = True
            self._logger.info("Async logging service initialized successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize logging service: {e}")
            raise
    
    async def log(self, level: str, message: str, context: Dict[str, Any] = None):
        """Log a message asynchronously"""
        if not self._initialized:
            await self.initialize()
        
        log_entry = LogEntry(level, message, context)
        
        # Put the log entry in the queue
        try:
            self.log_queue.put_nowait(log_entry)
        except asyncio.QueueFull:
            # If queue is full, drop the log entry to avoid blocking
            self._logger.warning("Log queue full, dropping log entry")
    
    async def info(self, message: str, context: Dict[str, Any] = None):
        """Log info message"""
        await self.log("INFO", message, context)
    
    async def error(self, message: str, context: Dict[str, Any] = None):
        """Log error message"""
        await self.log("ERROR", message, context)
    
    async def warning(self, message: str, context: Dict[str, Any] = None):
        """Log warning message"""
        await self.log("WARNING", message, context)
    
    async def debug(self, message: str, context: Dict[str, Any] = None):
        """Log debug message"""
        await self.log("DEBUG", message, context)
    
    async def log_exception(self, exception: Exception, context: Dict[str, Any] = None):
        """Log exception with context"""
        error_message = f"Exception: {str(exception)}"
        await self.error(error_message, context or {"exception_type": type(exception).__name__})
    
    async def get_recent_logs(self, level: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent log entries (mock implementation)"""
        # In a real implementation, this would read from a log database or file
        return []
    
    async def shutdown(self):
        """Shutdown the logging service"""
        if self.handler:
            self.handler.stop()
        
        # Flush remaining log entries
        while not self.log_queue.empty():
            try:
                log_entry = self.log_queue.get_nowait()
                if log_entry:
                    self.handler._process_log_entry(log_entry)
            except:
                break
        
        self._initialized = False
        self._logger.info("Async logging service shutdown completed")


# Global logger instance
_logger_instance: Optional[AsyncLoggingService] = None


def get_logger() -> AsyncLoggingService:
    """Get the global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AsyncLoggingService()
    return _logger_instance


def set_logger(logger: AsyncLoggingService):
    """Set the global logger instance"""
    global _logger_instance
    _logger_instance = logger