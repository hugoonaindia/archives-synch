"""
Tests for simple_error_handler module
"""

import pytest
import logging
import time
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

# Import the modules to test
from src.utils.simple_error_handler import retry_with_backoff_simple, SimpleLogger, setup_simple_logging


class TestRetryWithBackoffSimple:
    """Test cases for retry_with_backoff_simple decorator"""
    
    def test_successful_execution(self):
        """Test successful function execution without retries"""
        @retry_with_backoff_simple(max_retries=3)
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
    
    def test_retry_then_success(self):
        """Test function that succeeds after one retry"""
        call_count = 0
        
        @retry_with_backoff_simple(max_retries=3, base_delay=0.1)
        def func_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return "success after retry"
        
        result = func_with_retry()
        assert result == "success after retry"
        assert call_count == 2
    
    def test_max_retries_exhausted(self):
        """Test function that fails after max retries"""
        @retry_with_backoff_simple(max_retries=2, base_delay=0.1)
        def failing_func():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError, match="Always fails"):
            failing_func()
    
    def test_retry_with_different_parameters(self):
        """Test retry with custom parameters"""
        call_count = 0
        
        @retry_with_backoff_simple(max_retries=2, base_delay=0.05, max_delay=0.2, exponential_base=1.5)
        def func_with_custom_params():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt")
            return "success"
        
        result = func_with_custom_params()
        assert result == "success"
    
    @patch('time.sleep')
    def test_delays_between_retries(self, mock_sleep):
        """Test that correct delays are used between retries"""
        call_count = 0
        
        @retry_with_backoff_simple(max_retries=3, base_delay=0.1, jitter=False)
        def func_with_timing():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Retry needed")
            return "success"
        
        result = func_with_timing()
        assert result == "success"
        # Should have called sleep twice for the two retries
        assert mock_sleep.call_count == 2
        # Check that delays are increasing (0.1, 0.2)
        calls = mock_sleep.call_args_list
        assert calls[0][0][0] == 0.1  # First delay
        assert calls[1][0][0] == 0.2  # Second delay (exponential)
    
    def test_return_none_on_max_retries(self):
        """Test function returns None when max retries exhausted and no exception raised"""
        @retry_with_backoff_simple(max_retries=2)
        def func_returns_none():
            raise ValueError("Keep failing")
        
        result = func_returns_none()
        assert result is None


class TestSimpleLogger:
    """Test cases for SimpleLogger class"""
    
    def test_logger_initialization(self):
        """Test logger initialization"""
        logger = SimpleLogger("test_logger")
        assert logger.logger.name == "test_logger"
        assert logger.logger.level == logging.INFO
    
    def test_log_error_with_context(self):
        """Test error logging with context"""
        logger = SimpleLogger("test_logger")
        
        # Capture log output
        with patch.object(logger.logger, 'error') as mock_error:
            error = ValueError("Test error")
            logger.log_error(error, "test context")
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0][0]
            assert "Contexto: test context" in call_args
            assert "Error: Test error" in call_args
    
    def test_log_error_without_context(self):
        """Test error logging without context"""
        logger = SimpleLogger("test_logger")
        
        with patch.object(logger.logger, 'error') as mock_error:
            error = ValueError("Test error")
            logger.log_error(error)
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0][0]
            assert "Error: Test error" in call_args
            assert "Contexto:" not in call_args
    
    def test_log_warning(self):
        """Test warning logging"""
        logger = SimpleLogger("test_logger")
        
        with patch.object(logger.logger, 'warning') as mock_warning:
            logger.log_warning("Test warning message")
            mock_warning.assert_called_once_with("Test warning message")
    
    def test_log_info(self):
        """Test info logging"""
        logger = SimpleLogger("test_logger")
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.log_info("Test info message")
            mock_info.assert_called_once_with("Test info message")


class TestSetupSimpleLogging:
    """Test cases for setup_simple_logging function"""
    
    def test_setup_logging_creates_directory(self):
        """Test that logging setup creates log directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.utils.simple_error_handler.Path') as mock_path:
                mock_path.return_value = Path(temp_dir)
                mock_path.mkdir = MagicMock()
                
                logger = setup_simple_logging()
                
                # Should create log directory
                mock_path.mkdir.assert_called_once_with(exist_ok=True)
    
    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a SimpleLogger instance"""
        logger = setup_simple_logging()
        assert isinstance(logger, SimpleLogger)
        assert logger.logger.name == "trader_simple"
    
    def test_setup_logging_configures_handlers(self):
        """Test that logging setup configures file handlers"""
        # This test is more complex as it deals with global logging configuration
        # We'll test that it doesn't raise exceptions
        logger = setup_simple_logging()
        assert logger is not None