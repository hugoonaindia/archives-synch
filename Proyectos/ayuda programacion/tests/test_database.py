"""
Test cases for database module.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path

from src.models.database import Database, DatabaseConfig


class TestDatabase:
    """Test cases for Database class"""
    
    @pytest.fixture
    def temp_db_config(self):
        """Create a temporary database configuration"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        config = DatabaseConfig(
            db_path=db_path,
            wal_mode=True,
            timeout=10.0
        )
        
        yield config
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def database(self, temp_db_config):
        """Create a database instance"""
        return Database(temp_db_config)
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, database):
        """Test database initialization"""
        result = await database.initialize()
        assert result is True
        assert database._connection is not None
    
    @pytest.mark.asyncio
    async def test_create_user(self, database):
        """Test user creation"""
        await database.initialize()
        
        user_id = await database.create_user(
            username="testuser",
            email="test@example.com",
            preferences={"theme": "dark"}
        )
        
        assert user_id is not None
        assert isinstance(user_id, int)
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, database):
        """Test getting user by username"""
        await database.initialize()
        
        # Create user
        await database.create_user(
            username="testuser",
            email="test@example.com"
        )
        
        # Get user
        user = await database.get_user_by_username("testuser")
        
        assert user is not None
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, database):
        """Test getting non-existent user"""
        await database.initialize()
        
        user = await database.get_user_by_username("nonexistent")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_create_session(self, database):
        """Test session creation"""
        await database.initialize()
        
        # Create user first
        user_id = await database.create_user("testuser", "test@example.com")
        
        session_id = await database.create_session(
            user_id=user_id,
            session_data={"key": "value"},
            expires_at=None
        )
        
        assert session_id is not None
        assert isinstance(session_id, int)
    
    @pytest.mark.asyncio
    async def test_add_trading_data(self, database):
        """Test adding trading data"""
        await database.initialize()
        
        data_id = await database.add_trading_data(
            symbol="AAPL",
            open_price=150.0,
            close_price=155.0,
            high_price=160.0,
            low_price=148.0,
            volume=1000000,
            metadata={"market": "NASDAQ"}
        )
        
        assert data_id is not None
        assert isinstance(data_id, int)
    
    @pytest.mark.asyncio
    async def test_get_trading_data(self, database):
        """Test getting trading data"""
        await database.initialize()
        
        # Add test data
        await database.add_trading_data(
            symbol="AAPL",
            open_price=150.0,
            close_price=155.0,
            high_price=160.0,
            low_price=148.0,
            volume=1000000
        )
        
        # Get data
        data = await database.get_trading_data("AAPL", limit=10)
        
        assert len(data) == 1
        assert data[0]["symbol"] == "AAPL"
        assert data[0]["open_price"] == 150.0
    
    @pytest.mark.asyncio
    async def test_add_clinical_data(self, database):
        """Test adding clinical data"""
        await database.initialize()
        
        data_id = await database.add_clinical_data(
            patient_id="patient_001",
            session_id="session_001",
            data_type="vital_signs",
            measurement_data={"heart_rate": 72, "blood_pressure": "120/80"},
            metadata={"device": "monitor_001"}
        )
        
        assert data_id is not None
        assert isinstance(data_id, int)
    
    @pytest.mark.asyncio
    async def test_get_clinical_data(self, database):
        """Test getting clinical data"""
        await database.initialize()
        
        # Add test data
        await database.add_clinical_data(
            patient_id="patient_001",
            session_id="session_001",
            data_type="vital_signs",
            measurement_data={"heart_rate": 72}
        )
        
        # Get data
        data = await database.get_clinical_data("patient_001", "vital_signs", limit=10)
        
        assert len(data) == 1
        assert data[0]["patient_id"] == "patient_001"
        assert data[0]["data_type"] == "vital_signs"
    
    @pytest.mark.asyncio
    async def test_database_close(self, database):
        """Test database connection closing"""
        await database.initialize()
        assert database._connection is not None
        
        await database.close()
        assert database._connection is None