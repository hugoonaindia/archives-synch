"""Unit tests for logging functionality."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from trading_lstm_rl_app import _APP_STATE, LOG_QUEUE, log


class TestLog:
    """Tests for log() function."""

    def test_log_appends_to_queue(self):
        log("Test message", "INFO")
        assert len(LOG_QUEUE) == 1
        assert "Test message" in LOG_QUEUE[0]
        assert "[INFO]" in LOG_QUEUE[0]

    def test_log_with_different_levels(self):
        log("Warning message", "WARNING")
        assert "[WARNING]" in LOG_QUEUE[-1]

        log("Error message", "ERROR")
        assert "[ERROR]" in LOG_QUEUE[-1]

    def test_log_thread_safety(self):
        def log_many(n):
            for _ in range(100):
                log(f"Thread {n} message", "INFO")

        threads = [threading.Thread(target=log_many, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(LOG_QUEUE) == 500

    def test_log_with_mock_ui_log(self, mock_ui_log):
        _APP_STATE.ui_log = mock_ui_log
        log("Test with UI", "INFO")
        mock_ui_log.push.assert_called_once()
        _APP_STATE.ui_log = None

    def test_log_queue_maxlen(self):
        LOG_QUEUE.clear()
        for i in range(10001):
            log(f"Message {i}", "INFO")
        assert len(LOG_QUEUE) == 10000
