# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Dockerfile HEALTHCHECK now runs as `appuser` instead of root (security hardening)
- `ExperimentManager.save_config()` now wraps serialization errors in RuntimeError
- `ExperimentManager._app_state` now has explicit type hint

### Changed
- Section numbering comments corrected (#3 for experiment persistence, #4 for main entry point)

## [0.2.0] - 2026-05-05

### Added
- 41 new tests covering seed determinism, config edge cases, and error paths (101 total, 84% coverage)
- Subprocess-isolated tests for APP_PORT environment variable handling
- Tests for log file writing and UI push failure handling

### Fixed
- `set_global_seed()` SB3 import: `set_seed` → `set_random_seed` (API compatibility fix)

## [0.1.0] - 2026-05-04

### Added
- Initial project structure with LSTM + RL Trading App
- Configuration system with dataclasses (LSTMConfig, BacktestConfig, RLConfig, AppConfig)
- Input validation for ticker symbols, dates, and CSV paths
- Experiment manager for run tracking and metrics persistence
- Centralized logging with thread-safe queue and file output
- NiceGUI-based UI framework with placeholder components
- Multi-backend dependency loading (torch, numpy, pandas, sklearn, etc.)
- Global seed setting for reproducibility
- Docker multi-stage build
- Basic pytest test suite for configuration validation and logging

### Fixed
- Thread safety: LOG_QUEUE.append() now protected by _LOG_LOCK
- Empty csv_path validation: now normalizes to empty string (treated as yfinance fallback) instead of allowing unvalidated paths
- Port env parsing: invalid TRADING_APP_PORT values no longer crash on import
- Silent exception swallowing in UI log push: now logs warnings instead of silent pass