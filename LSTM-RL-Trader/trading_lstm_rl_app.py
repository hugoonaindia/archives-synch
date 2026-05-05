# ============================================================
# 1. Imports and global configuration
# ADVERTENCIA: No eliminar ningún import de esta sección aunque parezca
# inutilizado. Todos serán referenciados en fases posteriores del proyecto.
# ============================================================

"""LSTM + RL Trading App — Research and backtesting platform combining LSTM price prediction with RL trading agents."""

from __future__ import annotations

__all__ = [
    "LSTMConfig",
    "BacktestConfig",
    "RLConfig",
    "AppConfig",
    "AppState",
    "LogPushable",
    "ExperimentManager",
    "set_global_seed",
    "initialize_app",
    "build_ui",
    "main",
    "log",
    "BASE_DIR",
    "MODELS_DIR",
    "RUNS_DIR",
    "DATA_DIR",
    "APP_PORT",
    "LOG_QUEUE",
]

import json
import os
import random
import re
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, Literal, Optional, Protocol, Tuple, Union, runtime_checkable

# Optional dependencies with graceful degradation
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from sklearn.preprocessing import StandardScaler

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from nicegui import ui

    HAS_NICEGUI = True
except ImportError:
    HAS_NICEGUI = False

try:
    import gymnasium as gym
    from gymnasium import spaces

    HAS_GYMNASIUM = True
except ImportError:
    HAS_GYMNASIUM = False

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_checker import check_env
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False

try:
    import yfinance as yf

    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


# ============================================================
# Global paths, constants, and shared state
# ============================================================
BASE_DIR = Path(__file__).parent.resolve()
MODELS_DIR = BASE_DIR / "models"
RUNS_DIR = BASE_DIR / "runs"
DATA_DIR = BASE_DIR / "data"

# Configurable port via environment variable
try:
    APP_PORT = int(os.environ.get("TRADING_APP_PORT", 8080))
except ValueError:
    import warnings

    warnings.warn(f"Invalid TRADING_APP_PORT='{os.environ.get('TRADING_APP_PORT')}', using default 8080", stacklevel=2)
    APP_PORT = 8080

# Regex patterns for input validation
_TICKER_RE = re.compile(r"^[A-Z]{1,5}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_ticker(ticker: str) -> str:
    """Validate and normalize a stock ticker symbol.

    Args:
        ticker: Raw ticker string (case-insensitive).

    Returns:
        Uppercase ticker if valid.

    Raises:
        ValueError: If ticker format is invalid.
    """
    cleaned = ticker.strip().upper()
    if not _TICKER_RE.match(cleaned):
        raise ValueError(f"Invalid ticker '{ticker}'. Must be 1-5 uppercase letters (A-Z).")
    return cleaned


def _validate_date(date_str: str, field_name: str) -> str:
    """Validate a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate.
        field_name: Name of the config field (for error messages).

    Returns:
        The date string if valid.

    Raises:
        ValueError: If date format is invalid or represents an impossible date.
    """
    if not isinstance(date_str, str):
        raise ValueError(f"Invalid {field_name}: expected str, got {type(date_str).__name__}.")
    if not _DATE_RE.match(date_str.strip()):
        raise ValueError(f"Invalid {field_name} '{date_str}'. Expected format: YYYY-MM-DD.")
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid {field_name} '{date_str}'. Not a real date (e.g. 2024-02-30).")
    return date_str.strip()


def _validate_csv_path(csv_path: str) -> str:
    """Validate a CSV file path to prevent path traversal attacks.

    Args:
        csv_path: Raw file path string. Empty string is allowed (means use yfinance).

    Returns:
        The normalized path string if valid.

    Raises:
        ValueError: If path contains traversal sequences or escapes BASE_DIR.
    """
    if not csv_path.strip():
        return ""
    if "\x00" in csv_path:
        raise ValueError(f"Invalid csv_path '{csv_path}'. Null bytes are not allowed.")
    if ".." in csv_path.replace("\\", "/").split("/"):
        raise ValueError(f"Invalid csv_path '{csv_path}'. Path traversal ('..') is not allowed.")
    normalized = os.path.normpath(csv_path)
    resolved = Path(normalized).resolve()
    try:
        resolved.relative_to(BASE_DIR)
    except ValueError:
        raise ValueError("Invalid csv_path. Path must be within the application data directory.")
    return normalized


# ============================================================
# Shared application state (encapsulated per AGENTS.md)
# ============================================================


@runtime_checkable
class LogPushable(Protocol):
    """Protocol for objects that support pushing log lines (e.g., NiceGUI ui.log)."""

    def push(self, line: str) -> None: ...


@dataclass
class AppState:
    """Encapsulates all mutable global state for the application.

    This replaces scattered global variables to improve testability,
    prevent race conditions, and allow multiple experiments to run
    in isolation if needed.
    """

    config: Optional["AppConfig"] = None
    current_run_dir: Optional[Path] = None
    ui_log: Optional[LogPushable] = None


_APP_STATE = AppState()

LOG_QUEUE: Deque[str] = deque(maxlen=10000)
_LOG_LOCK = threading.Lock()


def log(message: str, level: Literal["INFO", "WARNING", "ERROR", "DEBUG"] = "INFO") -> None:
    """Central logging function.

    Writes to console, appends to in-memory queue, pushes to NiceGUI
    ui.log element (if available), and writes to the active run's
    log file (if a run is active).

    Note: Uses print() for console output during the bootstrap phase
    before the NiceGUI UI is available. This is the ONLY place where
    print() is permitted per AGENTS.md exception policy.

    Args:
        message: Log message text.
        level: Log level (INFO, WARNING, ERROR, DEBUG).
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    ui_log_ref = None
    run_dir_ref = None
    with _LOG_LOCK:
        print(line)
        LOG_QUEUE.append(line)
        if _APP_STATE.ui_log is not None:
            ui_log_ref = _APP_STATE.ui_log
        if _APP_STATE.current_run_dir is not None and _APP_STATE.current_run_dir.exists():
            run_dir_ref = _APP_STATE.current_run_dir
    if ui_log_ref is not None:
        try:
            ui_log_ref.push(line)
        except (RuntimeError, OSError, AttributeError) as e:
            print(f"[{timestamp}] [WARNING] Failed to push log to UI: {e}")
    if run_dir_ref is not None:
        log_file = run_dir_ref / "log.txt"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:
            print(f"[{timestamp}] [WARNING] Failed to write log file: {e}")


# ============================================================
# 2. Dataclasses and configuration schemas
# ============================================================


@dataclass
class LSTMConfig:
    """Configuration for LSTM prediction model."""

    sequence_length: int = 60
    prediction_horizon: int = 5
    hidden_size: int = 64
    num_layers: int = 2
    dropout: float = 0.2
    learning_rate: float = 0.001
    batch_size: int = 64
    epochs: int = 50
    weight_decay: float = 1e-5
    early_stopping_patience: int = 8
    bullish_threshold: float = 0.01
    bearish_threshold: float = -0.01
    threshold_long: float = 0.6
    threshold_short: float = 0.6

    def __post_init__(self) -> None:
        """Validate field constraints; raises ValueError on invalid input."""
        if self.sequence_length <= 0:
            raise ValueError(f"sequence_length must be > 0, got {self.sequence_length}")
        if self.prediction_horizon <= 0:
            raise ValueError(f"prediction_horizon must be > 0, got {self.prediction_horizon}")
        if self.hidden_size <= 0:
            raise ValueError(f"hidden_size must be > 0, got {self.hidden_size}")
        if self.num_layers <= 0:
            raise ValueError(f"num_layers must be > 0, got {self.num_layers}")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError(f"dropout must be in [0, 1), got {self.dropout}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be > 0, got {self.learning_rate}")
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be > 0, got {self.batch_size}")
        if self.epochs <= 0:
            raise ValueError(f"epochs must be > 0, got {self.epochs}")
        if self.weight_decay < 0:
            raise ValueError(f"weight_decay must be >= 0, got {self.weight_decay}")
        if self.early_stopping_patience <= 0:
            raise ValueError(f"early_stopping_patience must be > 0, got {self.early_stopping_patience}")
        if self.bullish_threshold <= 0:
            raise ValueError(f"bullish_threshold must be > 0, got {self.bullish_threshold}")
        if self.bearish_threshold >= 0:
            raise ValueError(f"bearish_threshold must be < 0, got {self.bearish_threshold}")
        if not 0.0 < self.threshold_long <= 1.0:
            raise ValueError(f"threshold_long must be in (0, 1], got {self.threshold_long}")
        if not 0.0 < self.threshold_short <= 1.0:
            raise ValueError(f"threshold_short must be in (0, 1], got {self.threshold_short}")


@dataclass
class BacktestConfig:
    """Configuration for backtesting engine."""

    initial_cash: float = 10000.0
    commission: float = 0.001
    slippage: float = 0.0005
    position_size: float = 1.0
    stop_loss: float = 0.03
    take_profit: float = 0.06

    def __post_init__(self) -> None:
        """Validate field constraints; raises ValueError on invalid input."""
        if self.initial_cash <= 0:
            raise ValueError(f"initial_cash must be > 0, got {self.initial_cash}")
        if self.commission < 0:
            raise ValueError(f"commission must be >= 0, got {self.commission}")
        if self.slippage < 0:
            raise ValueError(f"slippage must be >= 0, got {self.slippage}")
        if not 0.0 < self.position_size <= 1.0:
            raise ValueError(f"position_size must be in (0, 1], got {self.position_size}")
        if self.stop_loss < 0:
            raise ValueError(f"stop_loss must be >= 0, got {self.stop_loss}")
        if self.take_profit < 0:
            raise ValueError(f"take_profit must be >= 0, got {self.take_profit}")
        if self.stop_loss == 0 and self.take_profit == 0:
            raise ValueError("stop_loss and take_profit cannot both be 0 (no risk management)")


@dataclass
class RLConfig:
    """Configuration for reinforcement learning agent."""

    algorithm: str = "PPO"
    total_timesteps: int = 100000
    gamma: float = 0.99
    learning_rate: float = 0.0003
    n_steps: int = 2048
    batch_size: int = 64
    reward_asymmetry_factor: float = 1.5
    max_drawdown_limit: float = 0.15
    max_drawdown_penalty: float = 10.0
    reward_alpha: float = 0.2
    vol_action_mask_threshold: float = 2.0

    def __post_init__(self) -> None:
        """Validate field constraints; raises ValueError on invalid input."""
        if self.algorithm not in ("PPO",):
            raise ValueError(f"algorithm must be 'PPO', got '{self.algorithm}'")
        if self.total_timesteps <= 0:
            raise ValueError(f"total_timesteps must be > 0, got {self.total_timesteps}")
        if not 0.0 < self.gamma <= 1.0:
            raise ValueError(f"gamma must be in (0, 1], got {self.gamma}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be > 0, got {self.learning_rate}")
        if self.n_steps <= 0:
            raise ValueError(f"n_steps must be > 0, got {self.n_steps}")
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be > 0, got {self.batch_size}")
        if self.reward_asymmetry_factor <= 0:
            raise ValueError(f"reward_asymmetry_factor must be > 0, got {self.reward_asymmetry_factor}")
        if not 0.0 < self.max_drawdown_limit < 1.0:
            raise ValueError(f"max_drawdown_limit must be in (0, 1), got {self.max_drawdown_limit}")
        if self.max_drawdown_penalty < 0:
            raise ValueError(f"max_drawdown_penalty must be >= 0, got {self.max_drawdown_penalty}")
        if not 0.0 <= self.reward_alpha <= 1.0:
            raise ValueError(f"reward_alpha must be in [0, 1], got {self.reward_alpha}")
        if self.vol_action_mask_threshold < 0:
            raise ValueError(f"vol_action_mask_threshold must be >= 0, got {self.vol_action_mask_threshold}")


@dataclass
class AppConfig:
    """Top-level application configuration."""

    ticker: str = "SPY"
    csv_path: str = ""
    start_date: str = "2018-01-01"
    end_date: str = "2023-12-31"
    seed: int = 42
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    lstm: LSTMConfig = field(default_factory=LSTMConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    rl: RLConfig = field(default_factory=RLConfig)

    def __post_init__(self) -> None:
        """Validate field constraints and dates; raises ValueError on invalid input."""
        self.ticker = _validate_ticker(self.ticker)
        self.csv_path = _validate_csv_path(self.csv_path)
        self.start_date = _validate_date(self.start_date, "start_date")
        self.end_date = _validate_date(self.end_date, "end_date")
        if self.end_date <= self.start_date:
            raise ValueError(f"end_date ({self.end_date}) must be after start_date ({self.start_date})")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError(f"seed must be a non-negative integer, got {self.seed}")
        if not 0.0 < self.train_ratio < 1.0:
            raise ValueError(f"train_ratio must be in (0, 1), got {self.train_ratio}")
        if not 0.0 < self.val_ratio < 1.0:
            raise ValueError(f"val_ratio must be in (0, 1), got {self.val_ratio}")
        if self.train_ratio + self.val_ratio >= 1.0:
            raise ValueError(f"train_ratio ({self.train_ratio}) + val_ratio ({self.val_ratio}) must be < 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to a flat dictionary including all nested dataclasses."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Deserialize from dict, ignoring unknown keys for forward compatibility.

        Args:
            data: Dictionary with configuration values.

        Returns:
            AppConfig instance with validated values.

        Raises:
            TypeError: If data is not a dict or nested fields have wrong types.
            ValueError: If any field value fails validation.
        """
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")

        raw_ticker = cls._get_typed(data, "ticker", str, "SPY")
        raw_csv_path = cls._get_typed(data, "csv_path", str, "")
        raw_start_date = cls._get_typed(data, "start_date", str, "2018-01-01")
        raw_end_date = cls._get_typed(data, "end_date", str, "2023-12-31")
        raw_seed = cls._get_typed(data, "seed", int, 42, reject_bool=True)
        raw_train_ratio = cls._get_typed(data, "train_ratio", (int, float), 0.7)
        raw_val_ratio = cls._get_typed(data, "val_ratio", (int, float), 0.15)

        lstm_raw = cls._normalize_subconfig(data.get("lstm"), "lstm")
        backtest_raw = cls._normalize_subconfig(data.get("backtest"), "backtest")
        rl_raw = cls._normalize_subconfig(data.get("rl"), "rl")

        cls._validate_nested_fields(lstm_raw, _LSTM_FIELD_SPEC, "lstm")
        cls._validate_nested_fields(backtest_raw, _BACKTEST_FIELD_SPEC, "backtest")
        cls._validate_nested_fields(rl_raw, _RL_FIELD_SPEC, "rl")

        lstm_fields = {k: v for k, v in lstm_raw.items() if k in LSTMConfig.__dataclass_fields__}
        backtest_fields = {k: v for k, v in backtest_raw.items() if k in BacktestConfig.__dataclass_fields__}
        rl_fields = {k: v for k, v in rl_raw.items() if k in RLConfig.__dataclass_fields__}

        return cls(
            ticker=raw_ticker,
            csv_path=raw_csv_path,
            start_date=raw_start_date,
            end_date=raw_end_date,
            seed=raw_seed,
            train_ratio=float(raw_train_ratio),
            val_ratio=float(raw_val_ratio),
            lstm=LSTMConfig(**lstm_fields),
            backtest=BacktestConfig(**backtest_fields),
            rl=RLConfig(**rl_fields),
        )

    @staticmethod
    def _get_typed(
        data: Dict[str, Any],
        key: str,
        expected_type: type | tuple[type, ...],
        default: Any,
        reject_bool: bool = False,
    ) -> Any:
        """Extract and type-check a single field from a dict.

        Args:
            data: Source dictionary.
            key: Field name.
            expected_type: Allowed type(s).
            default: Fallback value if key is missing.
            reject_bool: If True, reject bool values even if expected_type includes int.

        Returns:
            The validated value.

        Raises:
            TypeError: If value has wrong type.
        """
        value = data.get(key, default)
        ok = isinstance(value, expected_type)
        if ok and reject_bool and isinstance(value, bool):
            ok = False
        if not ok:
            if isinstance(expected_type, tuple):
                type_name = " or ".join(t.__name__ for t in expected_type)
            else:
                type_name = getattr(expected_type, "__name__", str(expected_type))
            raise TypeError(f"'{key}' must be {type_name}, got {type(value).__name__}")
        return value

    @staticmethod
    def _normalize_subconfig(raw: Any, field_name: str = "subconfig") -> Dict[str, Any]:
        """Coerce None/missing subconfigs to empty dicts and validate type.

        Args:
            raw: Raw value for a nested config section.
            field_name: Name of the field for error messages.

        Returns:
            Validated dict (defaults to {} if raw is None).

        Raises:
            TypeError: If raw is not a dict or None.
        """
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise TypeError(f"'{field_name}' must be dict or None, got {type(raw).__name__}")
        return raw

    @staticmethod
    def _validate_nested_fields(raw: Dict[str, Any], field_spec: Tuple[_FieldSpec, ...], prefix: str) -> None:
        """Validate types of nested dataclass fields.

        Args:
            raw: Dictionary with field values.
            field_spec: Tuple of (key, expected_type) pairs.
            prefix: Parent config name for error messages.

        Raises:
            TypeError: If any field has wrong type.
        """
        for key, expected_type in field_spec:
            if key not in raw:
                continue
            value = raw[key]
            if isinstance(expected_type, tuple):
                type_name = " or ".join(t.__name__ for t in expected_type)
            else:
                type_name = getattr(expected_type, "__name__", str(expected_type))
            if isinstance(value, bool) and expected_type in (int, (int, float)):
                raise TypeError(f"'{prefix}.{key}' must be {type_name}, got bool")
            if not isinstance(value, expected_type):
                raise TypeError(f"'{prefix}.{key}' must be {type_name}, got {type(value).__name__}")


# Type alias for field spec entries used by from_dict() validation.
_FieldSpec = Tuple[str, Union[type, Tuple[type, ...]]]

# Field spec tables for nested config type validation in from_dict()
_LSTM_FIELD_SPEC: tuple[_FieldSpec, ...] = (
    ("sequence_length", int),
    ("prediction_horizon", int),
    ("hidden_size", int),
    ("num_layers", int),
    ("dropout", (int, float)),
    ("learning_rate", (int, float)),
    ("batch_size", int),
    ("epochs", int),
    ("weight_decay", (int, float)),
    ("early_stopping_patience", int),
    ("bullish_threshold", (int, float)),
    ("bearish_threshold", (int, float)),
    ("threshold_long", (int, float)),
    ("threshold_short", (int, float)),
)

_BACKTEST_FIELD_SPEC: tuple[_FieldSpec, ...] = (
    ("initial_cash", (int, float)),
    ("commission", (int, float)),
    ("slippage", (int, float)),
    ("position_size", (int, float)),
    ("stop_loss", (int, float)),
    ("take_profit", (int, float)),
)

_RL_FIELD_SPEC: tuple[_FieldSpec, ...] = (
    ("algorithm", str),
    ("total_timesteps", int),
    ("gamma", (int, float)),
    ("learning_rate", (int, float)),
    ("n_steps", int),
    ("batch_size", int),
    ("reward_asymmetry_factor", (int, float)),
    ("max_drawdown_limit", (int, float)),
    ("max_drawdown_penalty", (int, float)),
    ("reward_alpha", (int, float)),
    ("vol_action_mask_threshold", (int, float)),
)


# ============================================================
# 3. Experiment persistence and logging
# ============================================================


class ExperimentManager:
    """Manages experiment runs: creates run directories, persists config and metrics.

    Accepts an optional AppState to synchronize the active run directory.
    When provided, start_run() and end_run() update the shared state.
    """

    def __init__(self, app_state: Optional["AppState"] = None) -> None:
        self._run_id: Optional[str] = None
        self._run_dir: Optional[Path] = None
        self._metrics: Dict[str, Any] = {}
        self._app_state: Optional[AppState] = app_state

    @property
    def run_id(self) -> Optional[str]:
        """The unique run identifier (timestamp-ticker format)."""
        return self._run_id

    @property
    def run_dir(self) -> Optional[Path]:
        """The filesystem path for the active run directory."""
        return self._run_dir

    def start_run(self, ticker: str) -> str:
        """Create a new run directory and activate it as the global log target."""
        ticker = _validate_ticker(ticker)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = f"{random.randint(0, 0xFFFF):04X}"
        self._run_id = f"{timestamp}-{ticker}-{suffix}"
        self._run_dir = RUNS_DIR / self._run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._metrics = {}
        if self._app_state is not None:
            self._app_state.current_run_dir = self._run_dir
        log(f"Run started: {self._run_id} -> {self._run_dir}")
        return self._run_id

    def log_metric(self, name: str, value: Union[int, float, str], step: Optional[int] = None) -> None:
        """Record a scalar metric, optionally indexed by step."""
        if not isinstance(name, str) or not name:
            raise ValueError("metric name must be a non-empty string")
        entry: Dict[str, Any] = {"value": value}
        if step is not None:
            entry["step"] = step
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(entry)

    def save_config(self, config: "AppConfig") -> None:
        """Serialize AppConfig to config.json inside the active run directory.

        Raises:
            RuntimeError: If no active run or serialization fails.
        """
        if self._run_dir is None:
            raise RuntimeError("No active run. Call start_run() first.")
        config_path = self._run_dir / "config.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2)
        except (TypeError, ValueError, OSError) as exc:
            raise RuntimeError(f"Failed to save config to {config_path}: {exc}") from exc
        log(f"Config saved to {config_path}")

    def end_run(self) -> None:
        """Flush accumulated metrics to metrics.json and deactivate the run."""
        if self._run_dir is None:
            return
        metrics_path = self._run_dir / "metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(self._metrics, f, indent=2)
        log(f"Run ended: {self._run_id}. Metrics saved to {metrics_path}")
        self._run_id = None
        self._run_dir = None
        self._metrics = {}
        if self._app_state is not None:
            self._app_state.current_run_dir = None


_experiment_manager = ExperimentManager(app_state=_APP_STATE)


# ============================================================
# 4. Main entry point
# ============================================================


def set_global_seed(seed: int) -> None:
    """Set seeds for all stochastic libraries for reproducibility.

    Args:
        seed: Non-negative integer seed value.
    """
    random.seed(seed)
    if HAS_NUMPY:
        np.random.seed(seed)
    if HAS_TORCH:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    if HAS_SB3:
        from stable_baselines3.common.utils import set_random_seed as sb3_set_seed

        sb3_set_seed(seed)


def initialize_app() -> "AppConfig":
    """Initialize application configuration and start experiment run.

    Returns:
        Validated AppConfig instance.

    Raises:
        ValueError: If default configuration values fail validation.
    """
    log("Starting LSTM + RL Trading App")

    # End any orphaned run before starting a new one
    if _experiment_manager.run_id is not None:
        log("Ending orphaned experiment run before starting new one", "WARNING")
        _experiment_manager.end_run()

    # Deferred directory creation (avoid import-time side effects)
    for directory in (MODELS_DIR, RUNS_DIR, DATA_DIR):
        directory.mkdir(exist_ok=True)

    log(f"Directories created/verified: models={MODELS_DIR}, runs={RUNS_DIR}, data={DATA_DIR}")

    # Log optional dependency status per section 4.2 of the master document
    if not HAS_NUMPY:
        log("numpy not installed. Feature engineering will be disabled. Install with: pip install numpy", "WARNING")
    if not HAS_PANDAS:
        log("pandas not installed. Data loading will be disabled. Install with: pip install pandas", "WARNING")
    if not HAS_SKLEARN:
        log("scikit-learn not installed. Feature scaling disabled. Install with: pip install scikit-learn", "WARNING")
    if not HAS_TORCH:
        log("PyTorch not installed. LSTM training tab will be disabled. Install with: pip install torch", "WARNING")
    if not HAS_GYMNASIUM:
        log("Gymnasium not installed. RL tabs will be disabled. Install with: pip install gymnasium", "WARNING")
    if not HAS_SB3:
        log(
            "Stable-Baselines3 not installed. RL training tab will be hidden. Install with: pip install stable-baselines3",
            "WARNING",
        )
    if not HAS_YFINANCE:
        log(
            "yfinance not installed. Download button hidden - CSV load only. Install with: pip install yfinance",
            "WARNING",
        )
    if not HAS_MATPLOTLIB:
        log("matplotlib not installed. Charts will be disabled. Install with: pip install matplotlib", "WARNING")

    # Initialize shared config
    config = AppConfig()
    _APP_STATE.config = config
    set_global_seed(config.seed)

    # Start experiment run
    _experiment_manager.start_run(config.ticker)
    _experiment_manager.save_config(config)

    return config


def build_ui(_config: "AppConfig") -> None:
    """Build the NiceGUI user interface.

    Args:
        _config: Application configuration (used for future tab initialization).
    """
    if not HAS_NICEGUI:
        log("NiceGUI not available. UI will not be built.", "WARNING")
        return
    # Disclaimer (mandatory per section 12.3 of the master document)
    with ui.column().classes("w-full items-center"):
        ui.label("LSTM + RL Trading App").classes("text-2xl font-bold mt-4")
        ui.label(
            "Modo investigación/backtesting. No ejecuta operaciones reales. No constituye asesoramiento financiero."
        ).classes("text-red-500 font-bold mt-2 mb-4")
        ui.label("Hello NiceGUI - placeholder UI. Tabs will be added in subsequent phases.").classes("text-gray-500")
        # UI log element for real-time log display
        _APP_STATE.ui_log = ui.log().classes("w-full h-48")


def main() -> None:
    """Application entry point: initializes config, builds UI, and starts the server."""
    if not HAS_NICEGUI:
        raise RuntimeError("NiceGUI is required to run the application. Install with: pip install nicegui")
    config = initialize_app()
    build_ui(config)
    ui.run(title="LSTM RL Trading", port=APP_PORT)


if __name__ == "__main__":
    main()
