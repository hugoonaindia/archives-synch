"""
Tests for security_manager module
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Import the module to test
from src.config.security_manager import ApiCredentials, SecurityManager


class TestApiCredentials:
    """Test cases for ApiCredentials dataclass"""
    
    def test_credentials_creation(self):
        """Test ApiCredentials creation"""
        creds = ApiCredentials(
            base_url="https://api.example.com",
            api_token="test_token",
            admin_token="admin_token",
            actor_id="test_actor"
        )
        
        assert creds.base_url == "https://api.example.com"
        assert creds.api_token == "test_token"
        assert creds.admin_token == "admin_token"
        assert creds.actor_id == "test_actor"
    
    def test_credentials_to_dict(self):
        """Test ApiCredentials to_dict method"""
        creds = ApiCredentials(
            base_url="https://api.example.com",
            api_token="test_token",
            admin_token="admin_token",
            actor_id="test_actor"
        )
        
        result = creds.to_dict()
        expected = {
            "base_url": "https://api.example.com",
            "api_token": "test_token",
            "admin_token": "admin_token",
            "actor_id": "test_actor"
        }
        
        assert result == expected
    
    def test_credentials_from_dict(self):
        """Test ApiCredentials from_dict class method"""
        data = {
            "base_url": "https://api.example.com",
            "api_token": "test_token",
            "admin_token": "admin_token",
            "actor_id": "test_actor"
        }
        
        creds = ApiCredentials.from_dict(data)
        assert creds.base_url == "https://api.example.com"
        assert creds.api_token == "test_token"
        assert creds.admin_token == "admin_token"
        assert creds.actor_id == "test_actor"


class TestSecurityManager:
    """Test cases for SecurityManager class"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.security_manager = SecurityManager(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up temp files
        config_dir = Path(self.temp_dir)
        if config_dir.exists():
            for file in config_dir.glob("*"):
                file.unlink()
            config_dir.rmdir()
    
    def test_security_manager_initialization(self):
        """Test SecurityManager initialization"""
        assert self.security_manager.config_dir == Path(self.temp_dir)
        assert self.security_manager.credentials_file == Path(self.temp_dir) / "credentials.enc"
        assert self.security_manager.config_file == Path(self.temp_dir) / "config.json"
        assert self.security_manager.credentials is None
    
    def test_load_credentials_from_env_all_present(self):
        """Test loading credentials when all env vars are present"""
        env_vars = {
            "ALPACA_BASE_URL": "https://api.example.com",
            "ALPACA_API_TOKEN": "test_token",
            "ALPACA_ADMIN_TOKEN": "admin_token",
            "ALPACA_ACTOR_ID": "test_actor"
        }
        
        with patch.dict(os.environ, env_vars):
            creds = self.security_manager.load_credentials_from_env()
            
            assert creds is not None
            assert creds.base_url == "https://api.example.com"
            assert creds.api_token == "test_token"
            assert creds.admin_token == "admin_token"
            assert creds.actor_id == "test_actor"
            assert self.security_manager.credentials == creds
    
    def test_load_credentials_from_env_missing_some(self):
        """Test loading credentials when some env vars are missing"""
        env_vars = {
            "ALPACA_BASE_URL": "https://api.example.com",
            "ALPACA_API_TOKEN": "test_token",
            # Missing admin_token and actor_id
        }
        
        with patch.dict(os.environ, env_vars):
            creds = self.security_manager.load_credentials_from_env()
            
            assert creds is None
            assert self.security_manager.credentials is None
    
    def test_load_credentials_from_env_all_empty(self):
        """Test loading credentials when all env vars are empty"""
        env_vars = {
            "ALPACA_BASE_URL": "",
            "ALPACA_API_TOKEN": "",
            "ALPACA_ADMIN_TOKEN": "",
            "ALPACA_ACTOR_ID": ""
        }
        
        with patch.dict(os.environ, env_vars):
            creds = self.security_manager.load_credentials_from_env()
            
            assert creds is None
            assert self.security_manager.credentials is None
    
    def test_load_credentials_from_file_exists(self):
        """Test loading credentials from file when file exists"""
        # Create credentials file
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="file_token",
            admin_token="file_admin",
            actor_id="file_actor"
        )
        
        with open(self.security_manager.credentials_file, 'w', encoding='utf-8') as f:
            json.dump(credentials.to_dict(), f)
        
        creds = self.security_manager.load_credentials_from_file()
        
        assert creds is not None
        assert creds.base_url == "https://api.example.com"
        assert creds.api_token == "file_token"
        assert creds.admin_token == "file_admin"
        assert creds.actor_id == "file_actor"
        assert self.security_manager.credentials == creds
    
    def test_load_credentials_from_file_not_exists(self):
        """Test loading credentials from file when file doesn't exist"""
        creds = self.security_manager.load_credentials_from_file()
        
        assert creds is None
        assert self.security_manager.credentials is None
    
    def test_load_credentials_from_file_invalid_json(self):
        """Test loading credentials from file with invalid JSON"""
        # Create invalid JSON file
        with open(self.security_manager.credentials_file, 'w', encoding='utf-8') as f:
            f.write("invalid json content")
        
        creds = self.security_manager.load_credentials_from_file()
        
        assert creds is None
        assert self.security_manager.credentials is None
    
    def test_save_credentials_success(self):
        """Test successful credentials saving"""
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="save_token",
            admin_token="save_admin",
            actor_id="save_actor"
        )
        
        result = self.security_manager.save_credentials(credentials)
        
        assert result is True
        assert self.security_manager.credentials == credentials
        assert self.security_manager.credentials_file.exists()
        
        # Verify file content
        with open(self.security_manager.credentials_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        expected = credentials.to_dict()
        assert saved_data == expected
    
    def test_save_credentials_with_encrypt_warning(self):
        """Test credentials saving with encryption warning"""
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="encrypt_token",
            admin_token="encrypt_admin",
            actor_id="encrypt_actor"
        )
        
        with patch.object(self.security_manager.logger, 'warning') as mock_warning:
            result = self.security_manager.save_credentials(credentials, encrypt=True)
            
            assert result is True
            mock_warning.assert_called_once_with("Encriptación no implementada - guardando en texto plano")
    
    def test_save_credentials_failure(self):
        """Test credentials saving with failure"""
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="save_token",
            admin_token="save_admin",
            actor_id="save_actor"
        )
        
        # Mock file opening to raise exception
        with patch('builtins.open', side_effect=OSError("Permission denied")):
            with patch.object(self.security_manager.logger, 'error') as mock_error:
                result = self.security_manager.save_credentials(credentials)
                
                assert result is False
                mock_error.assert_called_once()
    
    def test_get_credentials_with_existing(self):
        """Test get_credentials when credentials already loaded"""
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="existing_token",
            admin_token="existing_admin",
            actor_id="existing_actor"
        )
        self.security_manager.credentials = credentials
        
        result = self.security_manager.get_credentials()
        
        assert result == credentials
    
    def test_get_credentials_from_env(self):
        """Test get_credentials loading from environment"""
        env_vars = {
            "ALPACA_BASE_URL": "https://api.example.com",
            "ALPACA_API_TOKEN": "env_token",
            "ALPACA_ADMIN_TOKEN": "env_admin",
            "ALPACA_ACTOR_ID": "env_actor"
        }
        
        with patch.dict(os.environ, env_vars):
            result = self.security_manager.get_credentials()
            
            assert result is not None
            assert result.base_url == "https://api.example.com"
            assert result.api_token == "env_token"
            assert self.security_manager.credentials == result
    
    def test_get_credentials_from_file(self):
        """Test get_credentials loading from file"""
        # Create credentials file
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="file_token",
            admin_token="file_admin",
            actor_id="file_actor"
        )
        
        with open(self.security_manager.credentials_file, 'w', encoding='utf-8') as f:
            json.dump(credentials.to_dict(), f)
        
        result = self.security_manager.get_credentials()
        
        assert result is not None
        assert result.base_url == "https://api.example.com"
        assert result.api_token == "file_token"
        assert self.security_manager.credentials == result
    
    def test_get_credentials_none(self):
        """Test get_credentials when no credentials available"""
        result = self.security_manager.get_credentials()
        
        assert result is None
    
    def test_validate_credentials_valid(self):
        """Test credential validation with valid credentials"""
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="valid_token",
            admin_token="valid_admin",
            actor_id="valid_actor"
        )
        
        result = self.security_manager.validate_credentials(credentials)
        
        assert result is True
    
    def test_validate_credentials_missing_fields(self):
        """Test credential validation with missing fields"""
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="",  # Empty
            admin_token="valid_admin",
            actor_id="valid_actor"
        )
        
        result = self.security_manager.validate_credentials(credentials)
        
        assert result is False
    
    def test_validate_credentials_invalid_url(self):
        """Test credential validation with invalid URL"""
        credentials = ApiCredentials(
            base_url="invalid_url",  # Missing protocol
            api_token="valid_token",
            admin_token="valid_admin",
            actor_id="valid_actor"
        )
        
        result = self.security_manager.validate_credentials(credentials)
        
        assert result is False
    
    def test_clear_credentials_success(self):
        """Test successful credentials clearing"""
        # Create credentials file
        credentials = ApiCredentials(
            base_url="https://api.example.com",
            api_token="token",
            admin_token="admin",
            actor_id="actor"
        )
        self.security_manager.credentials = credentials
        
        # Create file
        with open(self.security_manager.credentials_file, 'w', encoding='utf-8') as f:
            json.dump(credentials.to_dict(), f)
        
        result = self.security_manager.clear_credentials()
        
        assert result is True
        assert self.security_manager.credentials is None
        assert not self.security_manager.credentials_file.exists()
    
    def test_clear_credentials_no_file(self):
        """Test clearing credentials when no file exists"""
        result = self.security_manager.clear_credentials()
        
        assert result is False
    
    def test_get_config_no_file(self):
        """Test get_config when no config file exists"""
        result = self.security_manager.get_config()
        
        assert result == {}
    
    def test_get_config_success(self):
        """Test successful config loading"""
        config = {"setting1": "value1", "setting2": 42}
        
        with open(self.security_manager.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        result = self.security_manager.get_config()
        
        assert result == config
    
    def test_get_config_invalid_json(self):
        """Test get_config with invalid JSON"""
        with open(self.security_manager.config_file, 'w', encoding='utf-8') as f:
            f.write("invalid json")
        
        result = self.security_manager.get_config()
        
        assert result == {}
    
    def test_save_config_success(self):
        """Test successful config saving"""
        config = {"setting1": "value1", "setting2": 42}
        
        result = self.security_manager.save_config(config)
        
        assert result is True
        assert self.security_manager.config_file.exists()
        
        # Verify file content
        with open(self.security_manager.config_file, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        
        assert saved_config == config
    
    def test_save_config_failure(self):
        """Test config saving with failure"""
        config = {"setting1": "value1"}
        
        # Mock file opening to raise exception
        with patch('builtins.open', side_effect=OSError("Permission denied")):
            with patch.object(self.security_manager.logger, 'error') as mock_error:
                result = self.security_manager.save_config(config)
                
                assert result is False
                mock_error.assert_called_once()