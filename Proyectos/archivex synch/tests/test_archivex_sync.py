"""
test_archivex_sync.py — Unit tests for archivex_sync.py and vision_driver.py
"""
import sys
from datetime import date
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture(autouse=True)
def mock_pyautogui():
    """Mock pyautogui before importing archivex_sync."""
    sys.modules['pyautogui'] = Mock()
    yield
    for mod in ['archivex_sync', 'vision_driver']:
        sys.modules.pop(mod, None)


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
        """Test grid metrics at grid boundaries using the loaded CAL values."""
        calc_grid_metrics = load_module.calc_grid_metrics
        CAL = load_module.CAL

        # At grid start hour → y_ratio must be 0.0
        _, _, y_ratio_start, _, _ = calc_grid_metrics(
            wx=0, wy=0, ww=1000, wh=800,
            hour=CAL["grid_start_h"], minute=0
        )
        assert y_ratio_start == 0.0

        # At grid end hour → y_ratio must be 1.0
        _, _, y_ratio_end, _, _ = calc_grid_metrics(
            wx=0, wy=0, ww=1000, wh=800,
            hour=CAL["grid_end_h"], minute=0
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


class TestVisionDriver:
    """Tests for vision_driver.py (mocked Claude API)."""

    @pytest.fixture
    def vd(self):
        """Load vision_driver with anthropic mocked."""
        import importlib
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        mock_anthropic = MagicMock()
        sys.modules['anthropic'] = mock_anthropic
        import vision_driver
        importlib.reload(vision_driver)
        return vision_driver, mock_anthropic

    def _make_response(self, mock_anthropic, text: str):
        """Helper: configure mock to return text from Claude."""
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = msg

    def test_find_coords_parses_valid_json(self, vd):
        """find_coords returns (x, y) when Claude returns valid JSON."""
        vision_driver, mock_anthropic = vd
        self._make_response(mock_anthropic, '{"x": 120, "y": 350}')
        result = vision_driver.find_coords("search field")
        assert result == (120, 350)

    def test_find_coords_returns_none_when_not_found(self, vd):
        """find_coords returns None when Claude reports element not found."""
        vision_driver, mock_anthropic = vd
        self._make_response(mock_anthropic, '{"x": null, "y": null}')
        result = vision_driver.find_coords("nonexistent element")
        assert result is None

    def test_find_coords_fallback_regex(self, vd):
        """find_coords uses regex fallback if JSON has extra text."""
        vision_driver, mock_anthropic = vd
        self._make_response(mock_anthropic, 'Here it is: {"x": 200, "y": 400}')
        result = vision_driver.find_coords("button")
        assert result == (200, 400)

    def test_is_available_false_without_key(self, vd, monkeypatch):
        """is_available returns False when ANTHROPIC_API_KEY is not set."""
        vision_driver, _ = vd
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert vision_driver.is_available() is False

    def test_is_available_true_with_key(self, vd, monkeypatch):
        """is_available returns True when ANTHROPIC_API_KEY is set."""
        vision_driver, _ = vd
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        assert vision_driver.is_available() is True
