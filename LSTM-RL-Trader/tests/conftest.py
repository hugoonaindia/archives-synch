"""Pytest configuration and fixtures for LSTM-RL-Trader tests."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from trading_lstm_rl_app import (
    _APP_STATE,
    LOG_QUEUE,
    AppConfig,
    AppState,
    BacktestConfig,
    LSTMConfig,
    RLConfig,
    _experiment_manager,
    _validate_csv_path,
    _validate_date,
    _validate_ticker,
)


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    LOG_QUEUE.clear()
    _APP_STATE.ui_log = None
    _APP_STATE.current_run_dir = None
    _APP_STATE.config = None
    _experiment_manager.end_run()
    yield
    LOG_QUEUE.clear()
    _APP_STATE.ui_log = None
    _APP_STATE.current_run_dir = None
    _APP_STATE.config = None
    _experiment_manager.end_run()


@pytest.fixture
def valid_lstm_config():
    """Valid LSTM configuration for testing."""
    return LSTMConfig(
        sequence_length=60,
        prediction_horizon=5,
        hidden_size=64,
        num_layers=2,
        dropout=0.2,
        learning_rate=0.001,
        batch_size=64,
        epochs=50,
        weight_decay=1e-5,
        early_stopping_patience=8,
        bullish_threshold=0.01,
        bearish_threshold=-0.01,
        threshold_long=0.6,
        threshold_short=0.6,
    )


@pytest.fixture
def valid_backtest_config():
    """Valid BacktestConfig for testing."""
    return BacktestConfig(
        initial_cash=10000.0,
        commission=0.001,
        slippage=0.0005,
        position_size=1.0,
        stop_loss=0.03,
        take_profit=0.06,
    )


@pytest.fixture
def valid_rl_config():
    """Valid RLConfig for testing."""
    return RLConfig(
        algorithm="PPO",
        total_timesteps=100000,
        gamma=0.99,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        reward_asymmetry_factor=1.5,
        max_drawdown_limit=0.15,
        max_drawdown_penalty=10.0,
        reward_alpha=0.2,
        vol_action_mask_threshold=2.0,
    )


@pytest.fixture
def valid_app_config(valid_lstm_config, valid_backtest_config, valid_rl_config):
    """Valid AppConfig for testing."""
    return AppConfig(
        ticker="AAPL",
        csv_path="",
        start_date="2020-01-01",
        end_date="2023-12-31",
        seed=42,
        train_ratio=0.7,
        val_ratio=0.15,
        lstm=valid_lstm_config,
        backtest=valid_backtest_config,
        rl=valid_rl_config,
    )


@pytest.fixture
def mock_ui_log():
    """Mock NiceGUI ui.log element."""
    mock = MagicMock()
    return mock
