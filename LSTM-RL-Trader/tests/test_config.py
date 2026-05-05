"""Unit tests for configuration validation."""

import os

import pytest

from trading_lstm_rl_app import (
    AppConfig,
    BacktestConfig,
    LSTMConfig,
    RLConfig,
    _validate_csv_path,
    _validate_date,
    _validate_ticker,
)


class TestValidateTicker:
    """Tests for ticker validation."""

    def test_valid_ticker_uppercase(self):
        assert _validate_ticker("AAPL") == "AAPL"

    def test_valid_ticker_lowercase(self):
        assert _validate_ticker("aapl") == "AAPL"

    def test_valid_ticker_single_char(self):
        assert _validate_ticker("A") == "A"

    def test_valid_ticker_with_whitespace(self):
        assert _validate_ticker("  SPY  ") == "SPY"

    def test_invalid_ticker_too_long(self):
        with pytest.raises(ValueError, match="1-5 uppercase letters"):
            _validate_ticker("VERYLONG")

    def test_invalid_ticker_numbers(self):
        with pytest.raises(ValueError):
            _validate_ticker("AAP1")

    def test_invalid_ticker_special_chars(self):
        with pytest.raises(ValueError):
            _validate_ticker("AAPL*")


class TestValidateDate:
    """Tests for date validation."""

    def test_valid_date(self):
        assert _validate_date("2020-01-15", "start_date") == "2020-01-15"

    def test_valid_date_with_whitespace(self):
        assert _validate_date("  2020-01-15  ", "start_date") == "2020-01-15"

    def test_invalid_date_format(self):
        with pytest.raises(ValueError, match="Expected format: YYYY-MM-DD"):
            _validate_date("01-15-2020", "start_date")

    def test_invalid_date_real(self):
        with pytest.raises(ValueError, match="Not a real date"):
            _validate_date("2020-02-30", "start_date")

    def test_invalid_date_non_string(self):
        with pytest.raises(ValueError):
            _validate_date(20200115, "start_date")


class TestValidateCsvPath:
    """Tests for CSV path validation."""

    def test_valid_relative_path(self):
        assert _validate_csv_path("data/prices.csv") == "data/prices.csv"

    def test_valid_path_with_dots(self):
        assert _validate_csv_path("./data/prices.csv") == os.path.normpath("./data/prices.csv")

    def test_valid_path_with_normalized_dots(self):
        """Dots in filenames like 'my..csv' should be allowed."""
        normalized = _validate_csv_path("data/prices..csv")
        assert normalized == os.path.normpath("data/prices..csv")

    def test_invalid_path_traversal(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_csv_path("../etc/passwd")

    def test_invalid_path_traversal_root(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_csv_path("../../../etc/passwd")

    def test_empty_path_returns_empty(self):
        assert _validate_csv_path("") == ""


class TestLSTMConfig:
    """Tests for LSTMConfig validation."""

    def test_valid_config(self, valid_lstm_config):
        assert valid_lstm_config.sequence_length == 60
        assert valid_lstm_config.hidden_size == 64

    def test_invalid_sequence_length_zero(self):
        with pytest.raises(ValueError, match="sequence_length must be > 0"):
            LSTMConfig(sequence_length=0)

    def test_invalid_sequence_length_negative(self):
        with pytest.raises(ValueError, match="sequence_length must be > 0"):
            LSTMConfig(sequence_length=-1)

    def test_invalid_dropout(self):
        with pytest.raises(ValueError, match="dropout must be in"):
            LSTMConfig(dropout=1.5)

    def test_invalid_bullish_threshold_zero(self):
        with pytest.raises(ValueError, match="bullish_threshold must be > 0"):
            LSTMConfig(bullish_threshold=0)

    def test_invalid_bearish_threshold_zero(self):
        with pytest.raises(ValueError, match="bearish_threshold must be < 0"):
            LSTMConfig(bearish_threshold=0)


class TestBacktestConfig:
    """Tests for BacktestConfig validation."""

    def test_valid_config(self, valid_backtest_config):
        assert valid_backtest_config.initial_cash == 10000.0
        assert valid_backtest_config.commission == 0.001

    def test_invalid_initial_cash_zero(self):
        with pytest.raises(ValueError, match="initial_cash must be > 0"):
            BacktestConfig(initial_cash=0)

    def test_invalid_position_size(self):
        with pytest.raises(ValueError, match="position_size must be in"):
            BacktestConfig(position_size=1.5)


class TestRLConfig:
    """Tests for RLConfig validation."""

    def test_valid_config(self, valid_rl_config):
        assert valid_rl_config.algorithm == "PPO"
        assert valid_rl_config.gamma == 0.99

    def test_invalid_algorithm(self):
        with pytest.raises(ValueError, match="algorithm must be 'PPO'"):
            RLConfig(algorithm="DQN")

    def test_invalid_gamma(self):
        with pytest.raises(ValueError, match="gamma must be in"):
            RLConfig(gamma=1.5)

    def test_invalid_max_drawdown_limit_at_boundaries(self):
        with pytest.raises(ValueError, match="max_drawdown_limit must be in"):
            RLConfig(max_drawdown_limit=0.0)
        with pytest.raises(ValueError, match="max_drawdown_limit must be in"):
            RLConfig(max_drawdown_limit=1.0)
        with pytest.raises(ValueError, match="max_drawdown_limit must be in"):
            RLConfig(max_drawdown_limit=1.5)


class TestAppConfig:
    """Tests for AppConfig validation and serialization."""

    def test_valid_config(self, valid_app_config):
        assert valid_app_config.ticker == "AAPL"
        assert valid_app_config.train_ratio == 0.7

    def test_invalid_train_ratio_sum(self):
        with pytest.raises(ValueError, match=r"must be < 1\.0"):
            AppConfig(train_ratio=0.8, val_ratio=0.3)

    def test_to_dict(self, valid_app_config):
        d = valid_app_config.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["lstm"]["sequence_length"] == 60

    def test_from_dict(self, valid_app_config):
        d = valid_app_config.to_dict()
        reconstructed = AppConfig.from_dict(d)
        assert reconstructed.ticker == "AAPL"
        assert reconstructed.lstm.sequence_length == 60

    def test_from_dict_unknown_fields_ignored(self):
        data = {
            "ticker": "SPY",
            "csv_path": "",
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",
            "seed": 42,
            "train_ratio": 0.7,
            "val_ratio": 0.15,
            "lstm": {"sequence_length": 30, "unknown_field": 999},
            "backtest": {},
            "rl": {},
        }
        config = AppConfig.from_dict(data)
        assert config.lstm.sequence_length == 30
        assert not hasattr(config.lstm, "unknown_field")

    def test_from_dict_invalid_ticker_type(self):
        data = {
            "ticker": 123,
            "csv_path": "",
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",
            "seed": 42,
            "train_ratio": 0.7,
            "val_ratio": 0.15,
            "lstm": {},
            "backtest": {},
            "rl": {},
        }
        with pytest.raises(TypeError, match="'ticker' must be str"):
            AppConfig.from_dict(data)

    def test_invalid_end_date_before_start_date(self):
        """end_date must be after start_date."""
        with pytest.raises(ValueError, match="must be after start_date"):
            AppConfig(start_date="2023-12-31", end_date="2023-01-01")

    def test_invalid_end_date_equals_start_date(self):
        """end_date equal to start_date should also be rejected."""
        with pytest.raises(ValueError, match="must be after start_date"):
            AppConfig(start_date="2023-01-01", end_date="2023-01-01")
