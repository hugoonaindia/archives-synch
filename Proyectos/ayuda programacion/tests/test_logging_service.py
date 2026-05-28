"""
Test cases for logging service.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path

from src.services.logging_service import AsyncLoggingService, LogConfig, LogEntry


class TestAsyncLoggingService:
    """Test cases for AsyncLoggingService class"""
    
    @pytest.fixture
    def temp_log_config(self):
        """Create a temporary logging configuration"""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as tmp_file:
            log_path = tmp_file.name
        
        config = LogConfig(
            log_level="DEBUG",
            log_file=log_path,
            max_file_size=1024,
            backup_count=2,
            console_output=True,
            structured_logging=True
        )
        
        yield config
        
        # Cleanup
        if os.path.exists(log_path):
            os.unlink(log_path)
    
    @pytest.fixture
    def logging_service(self, temp_log_config):
        """Create a logging service instance"""
        return AsyncLoggingService(temp_log_config)
    
    @pytest.mark.asyncio
    async def test_logging_service_initialization(self, logging_service):
        """Test logging service initialization"""
        await logging_service.initialize()
        assert logging_service._initialized is True
        assert logging_service.handler is not None
    
    @pytest.mark.asyncio
    async def test_log_message(self, logging_service):
        """Test logging a message"""
        await logging_service.initialize()
        
        await logging_service.log("INFO", "Test message", {"key": "value"})
        
        # Allow time for the async handler to process the message
        await asyncio.sleep(0.1)
        
        # Check that the log queue was processed
        assert logging_service.log_queue.empty()
    
    @pytest.mark.asyncio
    async def test_log_levels(self, logging_service):
        """Test different log levels"""
        await logging_service.initialize()
        
        await logging_service.info("Info message")
        await logging_service.warning("Warning message")
        await logging_service.error("Error message")
        await logging_service.debug("Debug message")
        
        # Allow time for processing
        await asyncio.sleep(0.1)
        
        assert logging_service.log_queue.empty()
    
    @pytest.mark.asyncio
    async def test_log_with_context(self, logging_service):
        """Test logging with context"""
        await logging_service.initialize()
        
        context = {
            "user_id": "123",
            "action": "login",
            "ip": "192.168.1.1"
        }
        
        await logging_service.log("INFO", "User login", context)
        
        # Allow time for processing
        await asyncio.sleep(0.1)
        
        assert logging_service.log_queue.empty()
    
    @pytest.mark.asyncio
    async def test_log_exception(self, logging_service):
        """Test logging exceptions"""
        await logging_service.initialize()
        
        try:
            raise ValueError("Test exception")
        except Exception as e:
            await logging_service.log_exception(e, {"context": "test"})
        
        # Allow time for processing
        await asyncio.sleep(0.1)
        
        assert logging_service.log_queue.empty()
    
    @pytest.mark.asyncio
    async def test_get_recent_logs(self, logging_service):
        """Test getting recent logs"""
        await logging_service.initialize()
        
        # Add some logs
        await logging_service.info("Test message 1")
        await logging_service.error("Test message 2")
        
        # Get recent logs (should be empty in mock implementation)
        logs = await logging_service.get_recent_logs()
        
        # This is a mock implementation, so it should return empty list
        assert isinstance(logs, list)
    
    @pytest.mark.asyncio
    async def test_logging_service_shutdown(self, logging_service):
        """Test logging service shutdown"""
        await logging_service.initialize()
        
        await logging_service.shutdown()
        
        assert logging_service._initialized is False
        assert logging_service.handler is None
    
    @pytest.mark.asyncio
    async def test_double_initialization(self, logging_service):
        """Test that double initialization doesn't cause issues"""
        await logging_service.initialize()
        assert logging_service._initialized is True
        
        # Initialize again
        await logging_service.initialize()
        assert logging_service._initialized is True
    
    @pytest.mark.asyncio
    async def test_queue_full_handling(self, logging_service):
        """Test handling when log queue is full"""
        await logging_service.initialize()
        
        # Fill the queue
        for i in range(1000):  # More than reasonable queue size
            await logging_service.log("INFO", f"Message {i}")
        
        # Allow time for processing
        await asyncio.sleep(0.1)
        
        # Service should still be working
        assert logging_service._initialized is True


class TestLogEntry:
    """Test cases for LogEntry class"""
    
    def test_log_entry_creation(self):
        """Test log entry creation"""
        entry = LogEntry("INFO", "Test message", {"key": "value"})
        
        assert entry.level == "INFO"
        assert entry.message == "Test message"
        assert entry.context == {"key": "value"}
        assert entry.timestamp is not None
    
    def test_log_entry_to_dict(self):
        """Test log entry to dictionary conversion"""
        entry = LogEntry("ERROR", "Error occurred", {"error_code": 500})
        
        result = entry.to_dict()
        
        assert result["level"] == "ERROR"
        assert result["message"] == "Error occurred"
        assert result["context"] == {"error_code": 500}
        assert "timestamp" in result
    
    def test_log_entry_to_json(self):
        """Test log entry to JSON conversion"""
        entry = LogEntry("WARNING", "Warning message", {"type": "security"})
        
        json_str = entry.to_json()
        
        assert isinstance(json_str, str)
        assert "level" in json_str
        assert "message" in json_str
        assert "context" in json_str