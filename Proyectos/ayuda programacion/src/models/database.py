"""
Database module with proper separation of responsibilities.
Implements repository pattern for data access.
"""

import sqlite3
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from contextlib import asynccontextmanager
from datetime import datetime
import json


@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = "clinical_trading.db"
    wal_mode: bool = True
    timeout: float = 30.0


class Database:
    """Database class with async operations and proper error handling"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._connection: Optional[sqlite3.Connection] = None
        self._logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize database with proper async handling"""
        try:
            self._connection = await self._get_connection()
            await self._create_tables()
            self._logger.info("Database initialized successfully")
            return True
        except Exception as e:
            self._logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with async wrapper"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: sqlite3.connect(
                self.config.db_path, 
                timeout=self.config.timeout,
                check_same_thread=False  # Allow connection to be used across threads
            )
        )
    
    async def _create_tables(self):
        """Create database tables with proper schema"""
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        loop = asyncio.get_event_loop()
        
        # Enable WAL mode if requested
        if self.config.wal_mode:
            await loop.run_in_executor(
                None, 
                lambda: self._connection.execute("PRAGMA journal_mode=WAL")
            )
        
        # Create users table
        await loop.run_in_executor(
            None,
            self._connection.execute,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                preferences TEXT
            )
            """
        )
        
        # Create sessions table
        await loop.run_in_executor(
            None,
            self._connection.execute,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        
        # Create trading_data table
        await loop.run_in_executor(
            None,
            self._connection.execute,
            """
            CREATE TABLE IF NOT EXISTS trading_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                open_price REAL,
                close_price REAL,
                high_price REAL,
                low_price REAL,
                volume INTEGER,
                metadata TEXT
            )
            """
        )
        
        # Create clinical_data table
        await loop.run_in_executor(
            None,
            self._connection.execute,
            """
            CREATE TABLE IF NOT EXISTS clinical_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                data_type TEXT NOT NULL,
                measurement_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            """
        )
        
        await loop.run_in_executor(
            None,
            self._connection.execute,
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
        )
        await loop.run_in_executor(
            None,
            self._connection.execute,
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"
        )
        await loop.run_in_executor(
            None,
            self._connection.execute,
            "CREATE INDEX IF NOT EXISTS idx_trading_symbol ON trading_data(symbol)"
        )
        
        self._connection.commit()
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and return results"""
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        loop = asyncio.get_event_loop()
        cursor = await loop.run_in_executor(
            None, 
            lambda: self._connection.execute(query, params)
        )
        
        columns = [description[0] for description in cursor.description]
        results = []
        
        async for row in self._fetch_rows(cursor):
            results.append(dict(zip(columns, row)))
        
        return results
    
    async def execute_write(self, query: str, params: tuple = ()) -> int:
        """Execute a write operation"""
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        loop = asyncio.get_event_loop()
        cursor = await loop.run_in_executor(
            None, 
            lambda: self._connection.execute(query, params)
        )
        
        self._connection.commit()
        return cursor.lastrowid
    
    async def _fetch_rows(self, cursor) -> AsyncGenerator[tuple, None]:
        """Async row fetcher"""
        loop = asyncio.get_event_loop()
        while True:
            row = await loop.run_in_executor(None, cursor.fetchone)
            if row is None:
                break
            yield row
    
    async def create_user(self, username: str, email: str, preferences: Dict[str, Any] = None) -> int:
        """Create a new user"""
        preferences_json = json.dumps(preferences or {})
        user_id = await self.execute_write(
            "INSERT INTO users (username, email, preferences) VALUES (?, ?, ?)",
            (username, email, preferences_json)
        )
        return user_id
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        users = await self.execute_query(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        return users[0] if users else None
    
    async def create_session(self, user_id: int, session_data: Dict[str, Any] = None, 
                           expires_at: Optional[datetime] = None) -> int:
        """Create a new session"""
        session_data_json = json.dumps(session_data or {})
        expires_at_str = expires_at.isoformat() if expires_at else None
        
        session_id = await self.execute_write(
            "INSERT INTO sessions (user_id, session_data, expires_at) VALUES (?, ?, ?)",
            (user_id, session_data_json, expires_at_str)
        )
        return session_id
    
    async def add_trading_data(self, symbol: str, open_price: float, close_price: float,
                            high_price: float, low_price: float, volume: int = 0,
                            metadata: Dict[str, Any] = None) -> int:
        """Add trading data"""
        metadata_json = json.dumps(metadata or {})
        return await self.execute_write(
            """
            INSERT INTO trading_data (symbol, open_price, close_price, high_price, low_price, volume, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (symbol, open_price, close_price, high_price, low_price, volume, metadata_json)
        )
    
    async def get_trading_data(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trading data for a symbol"""
        return await self.execute_query(
            "SELECT * FROM trading_data WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
            (symbol, limit)
        )
    
    async def add_clinical_data(self, patient_id: str, session_id: str, 
                              data_type: str, measurement_data: Dict[str, Any],
                              metadata: Dict[str, Any] = None) -> int:
        """Add clinical data"""
        measurement_json = json.dumps(measurement_data)
        metadata_json = json.dumps(metadata or {})
        
        return await self.execute_write(
            """
            INSERT INTO clinical_data (patient_id, session_id, data_type, measurement_data, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (patient_id, session_id, data_type, measurement_json, metadata_json)
        )
    
    async def get_clinical_data(self, patient_id: str, data_type: str = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Get clinical data for a patient"""
        query = "SELECT * FROM clinical_data WHERE patient_id = ?"
        params = [patient_id]
        
        if data_type:
            query += " AND data_type = ?"
            params.append(data_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        return await self.execute_query(query, tuple(params))
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        result = await self.execute_write(
            "DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at < datetime('now')"
        )
        return result
    
    async def close(self):
        """Close database connection"""
        if self._connection:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._connection.close)
            self._connection = None
            self._logger.info("Database connection closed")
    
    def __del__(self):
        """Cleanup on destruction"""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                self._logger.error(f"Error closing database connection: {e}")