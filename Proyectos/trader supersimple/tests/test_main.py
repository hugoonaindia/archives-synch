"""
Tests for main application modules
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import modules to test
from src.simple_main import main
from src.utils.simple_error_handler import SimpleLogger
from src.api.simple_api_client import SimpleApiClient


class TestSimpleMain:
    """Test cases for simple_main module"""
    
    @patch('src.simple_main.setup_simple_logging')
    @patch('src.simple_main.SimpleApiClient')
    @patch('src.simple_main.time.sleep')
    def test_main_success(self, mock_sleep, mock_client_class, mock_logging):
        """Test main function successful execution"""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client_class.return_value = mock_client
        
        # Test main function
        result = main()
        
        # Verify results
        assert result == 0
        mock_logger.log_info.assert_called()
        mock_client.is_available.assert_called()
    
    @patch('src.simple_main.setup_simple_logging')
    @patch('src.simple_main.SimpleApiClient')
    @patch('src.simple_main.time.sleep')
    def test_main_api_unavailable(self, mock_sleep, mock_client_class, mock_logging):
        """Test main function when API is unavailable"""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        mock_client_class.return_value = mock_client
        
        # Test main function
        result = main()
        
        # Verify results
        assert result == 0
        mock_logger.log_info.assert_called()
        mock_client.is_available.assert_called()
    
    @patch('src.simple_main.setup_simple_logging')
    @patch('src.simple_main.SimpleApiClient')
    @patch('src.simple_main.time.sleep')
    def test_main_with_api_exception(self, mock_sleep, mock_client_class, mock_logging):
        """Test main function when API raises exception"""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        
        mock_client = MagicMock()
        mock_client.is_available.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client
        
        # Test main function
        result = main()
        
        # Verify results
        assert result == 0
        mock_logger.log_warning.assert_called()
    
    @patch('src.simple_main.setup_simple_logging')
    @patch('src.simple_main.SimpleApiClient')
    @patch('src.simple_main.time.sleep')
    def test_main_keyboard_interrupt(self, mock_sleep, mock_client_class, mock_logging):
        """Test main function with keyboard interrupt"""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Simulate keyboard interrupt
        mock_sleep.side_effect = KeyboardInterrupt("Test interrupt")
        
        # Test main function
        result = main()
        
        # Verify results
        assert result == 0
        mock_logger.log_info.assert_called_with("Interrupción recibida, deteniendo...")
    
    @patch('src.simple_main.setup_simple_logging')
    @patch('src.simple_main.SimpleApiClient')
    @patch('src.simple_main.time.sleep')
    def test_main_critical_error(self, mock_sleep, mock_client_class, mock_logging):
        """Test main function with critical error"""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        
        mock_client = MagicMock()
        mock_client_class.side_effect = Exception("Critical error")
        
        # Test main function
        result = main()
        
        # Verify results
        assert result == 1
        mock_logger.log_error.assert_called()


class TestIntegration:
    """Integration tests for the application"""
    
    def test_app_initialization(self):
        """Test that the application can be initialized"""
        # This test ensures all imports work correctly
        from src.simple_main import main
        from src.utils.simple_error_handler import SimpleLogger
        from src.api.simple_api_client import SimpleApiClient
        
        # All imports should work without errors
        assert callable(main)
        assert SimpleLogger is not None
        assert SimpleApiClient is not None
    
    def test_error_handling_integration(self):
        """Test error handling across modules"""
        # Test that error handling works end-to-end
        logger = SimpleLogger("test_integration")
        
        # Test error logging
        error = ValueError("Test error")
        logger.log_error(error, "integration test")
        
        # Should not raise any exceptions
        assert True
    
    def test_api_client_initialization(self):
        """Test API client can be initialized with different configurations"""
        # Test with empty tokens (should work)
        client = SimpleApiClient(
            base_url="https://api.example.com",
            api_token="",
            admin_token="",
            actor_id=""
        )
        
        assert client.base_url == "https://api.example.com"
        assert client.api_token == ""
        assert client.admin_token == ""
        assert client.actor_id == ""
    
    def test_logger_configuration(self):
        """Test logger configuration"""
        logger = SimpleLogger("test_logger")
        
        # Test that logger is properly configured
        assert logger.logger.name == "test_logger"
        assert logger.logger.level == 20  # INFO level


class TestPerformance:
    """Performance-related tests"""
    
    @patch('src.simple_main.setup_simple_logging')
    @patch('src.simple_main.SimpleApiClient')
    @patch('src.simple_main.time.sleep')
    def test_main_execution_time(self, mock_sleep, mock_client_class, mock_logging):
        """Test main function execution time"""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client_class.return_value = mock_client
        
        # Track execution time
        start_time = time.time()
        result = main()
        end_time = time.time()
        
        # Verify execution time is reasonable (should be fast with mocked components)
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Should complete quickly
        assert result == 0