"""
Tests for simple_api_client module
"""

import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# Import the module to test
from src.api.simple_api_client import SimpleApiClient


class TestSimpleApiClient:
    """Test cases for SimpleApiClient class"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = SimpleApiClient(
            base_url="https://api.example.com",
            api_token="test_token",
            admin_token="admin_token", 
            actor_id="test_actor"
        )
    
    def test_initialization(self):
        """Test client initialization"""
        assert self.client.base_url == "https://api.example.com"
        assert self.client.api_token == "test_token"
        assert self.client.admin_token == "admin_token"
        assert self.client.actor_id == "test_actor"
        assert self.client.timeout == 20
    
    def test_build_url(self):
        """Test URL building"""
        url = self.client._build_url("/test/path")
        assert url == "https://api.example.com/test/path"
        
        # Test with trailing slash in base URL
        client2 = SimpleApiClient("https://api.example.com/", "token", "admin", "actor")
        url = client2._build_url("/test/path")
        assert url == "https://api.example.com/test/path"
    
    def test_build_headers_without_admin(self):
        """Test header building without admin token"""
        headers = self.client._build_headers(use_admin=False)
        expected = {
            "Content-Type": "application/json",
            "X-DT-Trade-Token": "test_token",
            "X-DT-Actor": "test_actor"
        }
        assert headers == expected
    
    def test_build_headers_with_admin(self):
        """Test header building with admin token"""
        headers = self.client._build_headers(use_admin=True)
        expected = {
            "Content-Type": "application/json",
            "X-DT-Trade-Token": "test_token",
            "X-DT-Actor": "test_actor",
            "X-DT-Trade-Admin-Token": "admin_token"
        }
        assert headers == expected
    
    def test_build_headers_empty_tokens(self):
        """Test header building with empty tokens"""
        client = SimpleApiClient("https://api.example.com", "", "", "")
        headers = client._build_headers(use_admin=True)
        expected = {
            "Content-Type": "application/json"
        }
        assert headers == expected
    
    def test_decode_response_valid_json(self):
        """Test JSON decoding with valid response"""
        data = b'{"key": "value", "number": 42}'
        result = self.client._decode_response(data)
        assert result == {"key": "value", "number": 42}
    
    def test_decode_response_empty_data(self):
        """Test JSON decoding with empty data"""
        data = b''
        result = self.client._decode_response(data)
        assert result == {}
    
    def test_decode_response_whitespace_only(self):
        """Test JSON decoding with whitespace only"""
        data = b'   '
        result = self.client._decode_response(data)
        assert result == {}
    
    def test_decode_response_invalid_json(self):
        """Test JSON decoding with invalid JSON"""
        data = b'{"invalid": json}'
        with pytest.raises(ValueError, match="Error al decodificar JSON"):
            self.client._decode_response(data)
    
    def test_decode_response_non_dict_json(self):
        """Test JSON decoding with non-dict JSON"""
        data = b'[1, 2, 3]'
        with pytest.raises(ValueError, match="inválida - no es un objeto JSON"):
            self.client._decode_response(data)
    
    @patch('urllib.request.urlopen')
    def test_make_request_success(self, mock_urlopen):
        """Test successful HTTP request"""
        mock_response = Mock()
        mock_response.read.return_value = b'{"result": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = self.client._make_request("GET", "/test")
        assert result == {"result": "success"}
    
    @patch('urllib.request.urlopen')
    def test_make_request_with_payload(self, mock_urlopen):
        """Test HTTP request with payload"""
        mock_response = Mock()
        mock_response.read.return_value = b'{"status": "created"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        payload = {"key": "value", "number": 42}
        result = self.client._make_request("POST", "/create", payload)
        
        # Check that the request was made with correct data
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        assert request_obj.data == b'{"key": "value", "number": 42}'
    
    @patch('urllib.request.urlopen')
    def test_make_request_http_error(self, mock_urlopen):
        """Test HTTP error handling"""
        mock_response = Mock()
        mock_response.read.return_value = b'{"error": "Not found"}'
        mock_error = HTTPError("http://api.example.com/test", 404, "Not Found", {}, mock_response)
        mock_urlopen.side_effect = mock_error
        
        with pytest.raises(RuntimeError, match="HTTP 404"):
            self.client._make_request("GET", "/test")
    
    @patch('urllib.request.urlopen')
    def test_make_request_url_error(self, mock_urlopen):
        """Test URL error handling"""
        mock_urlopen.side_effect = URLError("Connection failed")
        
        with pytest.raises(RuntimeError, match="No se pudo conectar con la API"):
            self.client._make_request("GET", "/test")
    
    @patch('src.api.simple_api_client.retry_with_backoff_simple')
    def test_health_check_decorator(self, mock_retry):
        """Test that health_check has retry decorator"""
        # This test just verifies the decorator is applied
        assert hasattr(self.client.health_check, '__wrapped__')
    
    @patch('src.api.simple_api_client.retry_with_backoff_simple')
    def test_train_sequence_decorator(self, mock_retry):
        """Test that train_sequence has retry decorator"""
        # This test just verifies the decorator is applied
        assert hasattr(self.client.train_sequence, '__wrapped__')
    
    @patch('src.api.simple_api_client.retry_with_backoff_simple')
    def test_promote_to_paper_decorator(self, mock_retry):
        """Test that promote_to_paper has retry decorator"""
        # This test just verifies the decorator is applied
        assert hasattr(self.client.promote_to_paper, '__wrapped__')
    
    @patch('urllib.request.urlopen')
    def test_health_check_success(self, mock_urlopen):
        """Test successful health check"""
        mock_response = Mock()
        mock_response.read.return_value = b'{"status": "healthy"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        with patch.object(self.client, '_make_request') as mock_make_request:
            mock_make_request.return_value = {"status": "healthy"}
            
            result = self.client.health_check()
            assert result == {"status": "healthy"}
    
    @patch('urllib.request.urlopen')
    def test_health_check_failure(self, mock_urlopen):
        """Test failed health check"""
        mock_urlopen.side_effect = URLError("Connection failed")
        
        with pytest.raises(Exception):
            self.client.health_check()
    
    def test_is_available_true(self):
        """Test is_available when API is available"""
        with patch.object(self.client, 'health_check') as mock_health:
            mock_health.return_value = {"status": "healthy"}
            
            result = self.client.is_available()
            assert result is True
    
    def test_is_available_false(self):
        """Test is_available when API is not available"""
        with patch.object(self.client, 'health_check') as mock_health:
            mock_health.side_effect = Exception("API down")
            
            result = self.client.is_available()
            assert result is False