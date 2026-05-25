"""
test_archivex_sync.py — Unit tests for archivex_sync.py
"""
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch, Mock
import sys

import pytest


@pytest.fixture(autouse=True)
def mock_pyautogui():
    """Mock pyautogui before importing archivex_sync."""
    sys.modules['pyautogui'] = Mock()
    yield
    if 'archivex_sync' in sys.modules:
        del sys.modules['archivex_sync']


@pytest.fixture
def load_module():
    """Lazy load archivex_sync after mocks are in place."""
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import archivex_sync
    return archivex_sync


class TestAppointment:
    """Test Appointment dataclass."""

    def test_appointment_creation(self, load_module):
        """Test creating an Appointment."""
        Appointment = load_module.Appointment
        appt = Appointment(
            patient="John Doe",
            date=date(2024, 1, 15),
            start_time="10:00",
            end_time="11:00",
            day_offset=0,
            hour=10,
            minute=0,
        )
        assert appt.patient == "John Doe"
        assert appt.date == date(2024, 1, 15)
        assert appt.start_time == "10:00"


class TestCalcGridMetrics:
    """Test grid metric calculations."""

    def test_calc_grid_metrics_basic(self, load_module):
        """Test basic grid metrics calculation."""
        calc_grid_metrics = load_module.calc_grid_metrics
        # Window: 1000x800, top=135, bottom=145, col=65
        # Time slot at 10:00 (2 hours from grid_start=8)
        grid_h, grid_w, y_ratio, col_w, cell_y = calc_grid_metrics(
            wx=0, wy=0, ww=1000, wh=800, hour=10, minute=0
        )
        assert grid_h > 0
        assert grid_w > 0
        assert 0 <= y_ratio <= 1
        assert col_w > 0
        assert cell_y > 0

    def test_calc_grid_metrics_edge_cases(self, load_module):
        """Test grid metrics at grid boundaries."""
        calc_grid_metrics = load_module.calc_grid_metrics
        # At grid start (8:00)
        _, _, y_ratio_start, _, _ = calc_grid_metrics(
            wx=0, wy=0, ww=1000, wh=800, hour=8, minute=0
        )
        assert y_ratio_start == 0.0

        # At grid end (20:00)
        _, _, y_ratio_end, _, _ = calc_grid_metrics(
            wx=0, wy=0, ww=1000, wh=800, hour=20, minute=0
        )
        assert y_ratio_end == 1.0


class TestGetWeekAppointments:
    """Test Google Calendar appointment fetching."""

    def test_get_week_appointments_empty(self, load_module):
        """Test with no events in calendar."""
        get_week_appointments = load_module.get_week_appointments
        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {"items": []}

        result = get_week_appointments(mock_service, date(2024, 1, 8))

        assert result == []

    def test_get_week_appointments_with_events(self, load_module):
        """Test with events in calendar."""
        get_week_appointments = load_module.get_week_appointments
        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {
            "items": [
                {
                    "summary": "Patient: John Doe",
                    "start": {"dateTime": "2024-01-08T10:00:00+01:00"},
                    "end": {"dateTime": "2024-01-08T11:00:00+01:00"},
                }
            ]
        }

        result = get_week_appointments(mock_service, date(2024, 1, 8))

        assert len(result) == 1
        assert result[0].patient == "Patient: John Doe"
        assert result[0].start_time == "10:00"
        assert result[0].end_time == "11:00"

    def test_get_week_appointments_ignores_all_day(self, load_module):
        """Test that all-day events are ignored."""
        get_week_appointments = load_module.get_week_appointments
        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {
            "items": [
                {
                    "summary": "All day event",
                    "start": {"date": "2024-01-08"},
                    "end": {"date": "2024-01-09"},
                }
            ]
        }

        result = get_week_appointments(mock_service, date(2024, 1, 8))

        assert len(result) == 0


class TestAskConflictAction:
    """Test conflict action prompt."""

    def test_ask_conflict_action_create(self, load_module, monkeypatch):
        """Test user choosing 'create'."""
        ask_conflict_action = load_module.ask_conflict_action
        Appointment = load_module.Appointment
        monkeypatch.setattr("builtins.input", lambda _: "c")
        appt = Appointment(
            patient="Test", date=date(2024, 1, 8), start_time="10:00",
            end_time="11:00", day_offset=0, hour=10, minute=0
        )
        result = ask_conflict_action(appt)
        assert result == "crear"

    def test_ask_conflict_action_skip(self, load_module, monkeypatch):
        """Test user choosing 'skip'."""
        ask_conflict_action = load_module.ask_conflict_action
        Appointment = load_module.Appointment
        monkeypatch.setattr("builtins.input", lambda _: "s")
        appt = Appointment(
            patient="Test", date=date(2024, 1, 8), start_time="10:00",
            end_time="11:00", day_offset=0, hour=10, minute=0
        )
        result = ask_conflict_action(appt)
        assert result == "saltar"

    def test_ask_conflict_action_stop(self, load_module, monkeypatch):
        """Test user choosing 'stop'."""
        ask_conflict_action = load_module.ask_conflict_action
        Appointment = load_module.Appointment
        monkeypatch.setattr("builtins.input", lambda _: "p")
        appt = Appointment(
            patient="Test", date=date(2024, 1, 8), start_time="10:00",
            end_time="11:00", day_offset=0, hour=10, minute=0
        )
        result = ask_conflict_action(appt)
        assert result == "parar"


class TestConflictStopException:
    """Test ConflictStopException."""

    def test_conflict_stop_exception_raised(self, load_module):
        """Test that ConflictStopException can be raised and caught."""
        ConflictStopException = load_module.ConflictStopException
        with pytest.raises(ConflictStopException):
            raise ConflictStopException()
