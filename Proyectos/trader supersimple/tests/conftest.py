"""
Common test fixtures and utilities for trader supersimple tests
"""

import pytest
import tempfile
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test"""
    logging.getLogger().handlers.clear()
    logging.getLogger().setLevel(logging.INFO)
    yield
    logging.getLogger().handlers.clear()

@pytest.fixture
def temp_log_dir():
    """Create temporary directory for log files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "test_logs"
        log_path.mkdir(exist_ok=True)
        yield log_path

@pytest.fixture
def mock_api_response():
    """Mock API response for testing"""
    return {
        "status": "ok",
        "data": {
            "price": 150.0,
            "volume": 1000000,
            "timestamp": "2026-05-20T12:00:00Z"
        }
    }

@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return [
        {"open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000000},
        {"open": 104.0, "high": 108.0, "low": 103.0, "close": 107.0, "volume": 1200000},
        {"open": 107.0, "high": 110.0, "low": 106.0, "close": 109.0, "volume": 1100000},
    ]