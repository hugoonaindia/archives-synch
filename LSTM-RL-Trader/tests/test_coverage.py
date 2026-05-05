"""Tests for set_global_seed, initialize_app, APP_PORT, and additional edge cases."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from trading_lstm_rl_app import (
    _APP_STATE,
    LOG_QUEUE,
    AppConfig,
    AppState,
    BacktestConfig,
    ExperimentManager,
    LSTMConfig,
    RLConfig,
    _validate_csv_path,
    _validate_date,
    log,
)


class TestSetGlobalSeed:
    """Tests for set_global_seed()."""

    def test_set_global_seed_deterministic_random(self):
        import random

        from trading_lstm_rl_app import set_global_seed

        set_global_seed(123)
        val1 = random.random()
        set_global_seed(123)
        val2 = random.random()
        assert abs(val1 - val2) < 1e-15

    def test_set_global_seed_deterministic_numpy(self):
        import numpy as np

        from trading_lstm_rl_app import set_global_seed

        set_global_seed(42)
        val1 = np.random.random()
        set_global_seed(42)
        val2 = np.random.random()
        assert abs(val1 - val2) < 1e-15

    def test_set_global_seed_deterministic_torch(self):
        import torch

        from trading_lstm_rl_app import set_global_seed

        set_global_seed(99)
        t1 = torch.rand(1)
        set_global_seed(99)
        t2 = torch.rand(1)
        assert torch.allclose(t1, t2)


class TestAppConfigPostInitEdgeCases:
    """Edge cases for AppConfig.__post_init__."""

    def test_seed_bool_rejected(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            AppConfig(seed=True)

    def test_seed_negative_rejected(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            AppConfig(seed=-1)

    def test_train_ratio_zero_rejected(self):
        with pytest.raises(ValueError, match="train_ratio must be in"):
            AppConfig(train_ratio=0.0)

    def test_train_ratio_one_rejected(self):
        with pytest.raises(ValueError, match="train_ratio must be in"):
            AppConfig(train_ratio=1.0)

    def test_val_ratio_zero_rejected(self):
        with pytest.raises(ValueError, match="val_ratio must be in"):
            AppConfig(val_ratio=0.0)

    def test_val_ratio_one_rejected(self):
        with pytest.raises(ValueError, match="val_ratio must be in"):
            AppConfig(val_ratio=1.0)


class TestLSTMConfigEdgeCases:
    """Edge cases for LSTMConfig validation."""

    def test_prediction_horizon_zero(self):
        with pytest.raises(ValueError, match="prediction_horizon must be > 0"):
            LSTMConfig(prediction_horizon=0)

    def test_hidden_size_negative(self):
        with pytest.raises(ValueError, match="hidden_size must be > 0"):
            LSTMConfig(hidden_size=-1)

    def test_num_layers_zero(self):
        with pytest.raises(ValueError, match="num_layers must be > 0"):
            LSTMConfig(num_layers=0)

    def test_learning_rate_zero(self):
        with pytest.raises(ValueError, match="learning_rate must be > 0"):
            LSTMConfig(learning_rate=0)

    def test_batch_size_negative(self):
        with pytest.raises(ValueError, match="batch_size must be > 0"):
            LSTMConfig(batch_size=-1)

    def test_epochs_zero(self):
        with pytest.raises(ValueError, match="epochs must be > 0"):
            LSTMConfig(epochs=0)

    def test_weight_decay_negative(self):
        with pytest.raises(ValueError, match="weight_decay must be >= 0"):
            LSTMConfig(weight_decay=-0.1)

    def test_early_stopping_patience_zero(self):
        with pytest.raises(ValueError, match="early_stopping_patience must be > 0"):
            LSTMConfig(early_stopping_patience=0)

    def test_threshold_long_zero(self):
        with pytest.raises(ValueError, match="threshold_long must be in"):
            LSTMConfig(threshold_long=0.0)

    def test_threshold_short_above_one(self):
        with pytest.raises(ValueError, match="threshold_short must be in"):
            LSTMConfig(threshold_short=1.5)


class TestBacktestConfigEdgeCases:
    """Edge cases for BacktestConfig validation."""

    def test_commission_negative(self):
        with pytest.raises(ValueError, match="commission must be >= 0"):
            BacktestConfig(commission=-0.01)

    def test_slippage_negative(self):
        with pytest.raises(ValueError, match="slippage must be >= 0"):
            BacktestConfig(slippage=-0.001)

    def test_stop_loss_negative(self):
        with pytest.raises(ValueError, match="stop_loss must be >= 0"):
            BacktestConfig(stop_loss=-0.01)

    def test_take_profit_negative(self):
        with pytest.raises(ValueError, match="take_profit must be >= 0"):
            BacktestConfig(take_profit=-0.01)

    def test_both_stop_loss_and_take_profit_zero(self):
        with pytest.raises(ValueError, match="no risk management"):
            BacktestConfig(stop_loss=0, take_profit=0)


class TestRLConfigEdgeCases:
    """Edge cases for RLConfig validation."""

    def test_total_timesteps_zero(self):
        with pytest.raises(ValueError, match="total_timesteps must be > 0"):
            RLConfig(total_timesteps=0)

    def test_learning_rate_negative(self):
        with pytest.raises(ValueError, match="learning_rate must be > 0"):
            RLConfig(learning_rate=-0.001)

    def test_n_steps_zero(self):
        with pytest.raises(ValueError, match="n_steps must be > 0"):
            RLConfig(n_steps=0)

    def test_batch_size_negative(self):
        with pytest.raises(ValueError, match="batch_size must be > 0"):
            RLConfig(batch_size=-1)

    def test_reward_asymmetry_factor_zero(self):
        with pytest.raises(ValueError, match="reward_asymmetry_factor must be > 0"):
            RLConfig(reward_asymmetry_factor=0)

    def test_max_drawdown_penalty_negative(self):
        with pytest.raises(ValueError, match="max_drawdown_penalty must be >= 0"):
            RLConfig(max_drawdown_penalty=-1.0)

    def test_vol_action_mask_threshold_negative(self):
        with pytest.raises(ValueError, match="vol_action_mask_threshold must be >= 0"):
            RLConfig(vol_action_mask_threshold=-0.1)

    def test_reward_alpha_boundary_values(self):
        """reward_alpha accepts 0.0 and 1.0 as valid boundaries."""
        config_min = RLConfig(reward_alpha=0.0)
        assert config_min.reward_alpha == 0.0
        config_max = RLConfig(reward_alpha=1.0)
        assert config_max.reward_alpha == 1.0

    def test_reward_alpha_out_of_bounds(self):
        with pytest.raises(ValueError, match="reward_alpha must be in"):
            RLConfig(reward_alpha=-0.1)
        with pytest.raises(ValueError, match="reward_alpha must be in"):
            RLConfig(reward_alpha=1.1)


class TestFromDictEdgeCases:
    """Edge cases for AppConfig.from_dict()."""

    def test_from_dict_non_dict_raises(self):
        with pytest.raises(TypeError, match="Expected dict"):
            AppConfig.from_dict("not a dict")

    def test_from_dict_seed_bool_rejected(self):
        data = {
            "ticker": "SPY",
            "csv_path": "",
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",
            "seed": True,
            "train_ratio": 0.7,
            "val_ratio": 0.15,
            "lstm": {},
            "backtest": {},
            "rl": {},
        }
        with pytest.raises(TypeError, match="'seed' must be int"):
            AppConfig.from_dict(data)

    def test_from_dict_lstm_non_dict_raises(self):
        data = {
            "ticker": "SPY",
            "csv_path": "",
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",
            "seed": 42,
            "train_ratio": 0.7,
            "val_ratio": 0.15,
            "lstm": "not a dict",
            "backtest": {},
            "rl": {},
        }
        with pytest.raises(TypeError, match="'lstm' must be dict"):
            AppConfig.from_dict(data)

    def test_from_dict_nested_bool_as_int_rejected(self):
        data = {
            "ticker": "SPY",
            "csv_path": "",
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",
            "seed": 42,
            "train_ratio": 0.7,
            "val_ratio": 0.15,
            "lstm": {"sequence_length": True},
            "backtest": {},
            "rl": {},
        }
        with pytest.raises(TypeError, match="'lstm.sequence_length' must be int, got bool"):
            AppConfig.from_dict(data)


class TestValidateCsvPathEdgeCases:
    """Edge cases for CSV path validation."""

    def test_null_byte_rejected(self):
        with pytest.raises(ValueError, match="Null bytes"):
            _validate_csv_path("data/file\x00.csv")

    def test_absolute_path_outside_base(self):
        with pytest.raises(ValueError, match="must be within"):
            _validate_csv_path("/etc/passwd")


class TestLogToFile:
    """Tests for log file writing."""

    def test_log_writes_to_file_when_run_active(self, tmp_path, monkeypatch):
        monkeypatch.setattr("trading_lstm_rl_app.RUNS_DIR", tmp_path / "runs")
        state = AppState()
        mgr = ExperimentManager(app_state=state)
        mgr.start_run("TEST")

        # Sync global state so log() can find the run directory
        _APP_STATE.current_run_dir = mgr.run_dir

        log("file test message", "INFO")

        log_file = mgr.run_dir / "log.txt"
        assert log_file.exists()
        content = log_file.read_text()
        assert "file test message" in content

        mgr.end_run()
        _APP_STATE.current_run_dir = None

    def test_log_handles_ui_push_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr("trading_lstm_rl_app.RUNS_DIR", tmp_path / "runs")
        bad_ui_log = MagicMock()
        bad_ui_log.push.side_effect = RuntimeError("UI disconnected")
        _APP_STATE.ui_log = bad_ui_log

        log("should not crash", "INFO")

        _APP_STATE.ui_log = None


class TestAppPortFallback:
    """Tests for APP_PORT environment variable handling.

    These tests use subprocess isolation to avoid module reload side effects
    that would break LOG_QUEUE references for subsequent tests.
    """

    def test_app_port_from_env(self):
        import subprocess

        result = subprocess.run(
            [
                "python",
                "-c",
                "import os; os.environ['TRADING_APP_PORT']='9090'; "
                "from trading_lstm_rl_app import APP_PORT; print(APP_PORT)",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )
        assert result.stdout.strip() == "9090"

    def test_app_port_invalid_env_uses_default(self):
        import subprocess

        result = subprocess.run(
            [
                "python",
                "-c",
                "import os, warnings; os.environ['TRADING_APP_PORT']='not_a_number'; "
                "warnings.filterwarnings('always'); "
                "from trading_lstm_rl_app import APP_PORT; print(APP_PORT)",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )
        assert result.stdout.strip() == "8080"
        assert "Invalid TRADING_APP_PORT" in result.stderr
