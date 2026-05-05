"""Tests for ExperimentManager."""

import json
import re
from datetime import datetime

import pytest

from trading_lstm_rl_app import AppConfig, AppState, ExperimentManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """Fresh ExperimentManager with isolated run directory."""
    monkeypatch.setattr("trading_lstm_rl_app.RUNS_DIR", tmp_path / "runs")
    return ExperimentManager(app_state=AppState())


@pytest.fixture
def app_config():
    """Minimal valid AppConfig for testing."""
    return AppConfig(ticker="TEST", csv_path="")


class TestExperimentManagerInit:
    """Tests for ExperimentManager initialization."""

    def test_init_creates_empty_state(self, manager):
        assert manager.run_id is None
        assert manager.run_dir is None
        assert manager._metrics == {}


class TestStartRun:
    """Tests for start_run()."""

    def test_start_run_creates_directory_and_sets_state(self, manager):
        run_id = manager.start_run("tsla")
        assert re.match(r"^\d{8}-\d{6}-TSLA-[0-9A-F]{4}$", run_id)
        assert manager.run_dir.exists()
        assert manager._app_state.current_run_dir == manager.run_dir

    def test_start_run_returns_run_id(self, manager):
        run_id = manager.start_run("AAPL")
        assert isinstance(run_id, str)
        assert len(run_id) > 0

    def test_start_run_resets_metrics(self, manager):
        manager._metrics = {"old": [{"value": 1.0}]}
        manager.start_run("SPY")
        assert manager._metrics == {}


class TestLogMetric:
    """Tests for log_metric()."""

    def test_log_metric_single_value(self, manager):
        manager.log_metric("sharpe", 1.5)
        assert manager._metrics["sharpe"] == [{"value": 1.5}]

    def test_log_metric_with_step(self, manager):
        manager.log_metric("loss", 0.5, step=10)
        assert manager._metrics["loss"] == [{"value": 0.5, "step": 10}]

    def test_log_metric_multiple_entries(self, manager):
        manager.log_metric("loss", 1.0, step=1)
        manager.log_metric("loss", 0.8, step=2)
        manager.log_metric("loss", 0.6, step=3)
        assert len(manager._metrics["loss"]) == 3
        assert manager._metrics["loss"][-1]["value"] == 0.6

    def test_log_metric_multiple_names(self, manager):
        manager.log_metric("sharpe", 1.2)
        manager.log_metric("drawdown", 0.05)
        assert "sharpe" in manager._metrics
        assert "drawdown" in manager._metrics

    def test_log_metric_empty_name_raises(self, manager):
        with pytest.raises(ValueError, match="non-empty string"):
            manager.log_metric("", 1.0)

    def test_log_metric_non_string_name_raises(self, manager):
        with pytest.raises(ValueError, match="non-empty string"):
            manager.log_metric(123, 1.0)


class TestSaveConfig:
    """Tests for save_config()."""

    def test_save_config_writes_json(self, manager, app_config):
        manager.start_run("TEST")
        manager.save_config(app_config)
        config_path = manager.run_dir / "config.json"
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["ticker"] == "TEST"
        assert data["seed"] == 42

    def test_save_config_raises_without_active_run(self, manager, app_config):
        with pytest.raises(RuntimeError, match="No active run"):
            manager.save_config(app_config)

    def test_save_config_serialization_error_wrapped(self, manager, tmp_path, monkeypatch):
        """Verify json.dump failures are wrapped in RuntimeError."""
        monkeypatch.setattr("trading_lstm_rl_app.RUNS_DIR", tmp_path / "runs")
        manager.start_run("TEST")

        class BadConfig:
            def to_dict(self):
                raise TypeError("not serializable")

        with pytest.raises(RuntimeError, match="Failed to save config"):
            manager.save_config(BadConfig())  # type: ignore[arg-type]


class TestEndRun:
    """Tests for end_run()."""

    def test_end_run_writes_metrics_and_clears_state(self, manager):
        manager.start_run("TEST")
        manager.log_metric("sharpe", 1.5)
        metrics_path = manager.run_dir / "metrics.json"

        manager.end_run()

        assert metrics_path.exists()
        data = json.loads(metrics_path.read_text())
        assert data["sharpe"] == [{"value": 1.5}]
        assert manager.run_id is None
        assert manager.run_dir is None
        assert manager._metrics == {}
        assert manager._app_state.current_run_dir is None

    def test_end_run_noop_without_active_run(self, manager):
        manager.end_run()
        assert manager.run_id is None


class TestRunProperties:
    """Tests for run_id and run_dir properties."""

    def test_run_id_is_readonly(self, manager):
        with pytest.raises(AttributeError):
            manager.run_id = "forced"

    def test_run_dir_is_readonly(self, manager):
        with pytest.raises(AttributeError):
            manager.run_dir = "/forced/path"
