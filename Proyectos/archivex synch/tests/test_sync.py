"""Unit tests for sync.py."""
import sys
from datetime import date
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture(autouse=True)
def mock_pyautogui():
    sys.modules["pyautogui"] = Mock()
    yield
    for mod in ["sync"]:
        sys.modules.pop(mod, None)


@pytest.fixture
def sync(tmp_path):
    """Load sync module after mocks are in place."""
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    import sync as s
    return s


class TestAppointment:
    def test_creation(self, sync):
        appt = sync.Appointment(
            patient="Ana García",
            date=date(2026, 5, 26),
            start_time="09:00",
            end_time="10:00",
            day_offset=1,   # Tuesday
            hour=9,
            minute=0,
        )
        assert appt.patient == "Ana García"
        assert appt.day_offset == 1


class TestGetWeekAppointments:
    def _make_service(self, items):
        svc = MagicMock()
        svc.events().list().execute.return_value = {"items": items}
        return svc

    def test_empty_calendar(self, sync):
        svc = self._make_service([])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert result == []

    def test_parses_timed_event(self, sync):
        svc = self._make_service([{
            "summary": "Patient: Hugo",
            "start": {"dateTime": "2026-05-26T09:00:00+02:00"},
            "end":   {"dateTime": "2026-05-26T10:00:00+02:00"},
        }])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert len(result) == 1
        assert result[0].patient == "Patient: Hugo"
        assert result[0].start_time == "09:00"
        assert result[0].day_offset == 1   # Tuesday

    def test_skips_all_day_events(self, sync):
        svc = self._make_service([{
            "summary": "Holiday",
            "start": {"date": "2026-05-26"},
            "end":   {"date": "2026-05-27"},
        }])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert result == []

    def test_skips_monday(self, sync):
        # 2026-05-25 is a Monday
        svc = self._make_service([{
            "summary": "Patient: Lunes",
            "start": {"dateTime": "2026-05-25T10:00:00+02:00"},
            "end":   {"dateTime": "2026-05-25T11:00:00+02:00"},
        }])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert result == []

    def test_skips_wednesday(self, sync):
        # 2026-05-27 is a Wednesday
        svc = self._make_service([{
            "summary": "Patient: Miércoles",
            "start": {"dateTime": "2026-05-27T10:00:00+02:00"},
            "end":   {"dateTime": "2026-05-27T11:00:00+02:00"},
        }])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert result == []

    def test_keeps_tuesday_and_thursday(self, sync):
        svc = self._make_service([
            {
                "summary": "Patient: Martes",
                "start": {"dateTime": "2026-05-26T09:00:00+02:00"},
                "end":   {"dateTime": "2026-05-26T10:00:00+02:00"},
            },
            {
                "summary": "Patient: Jueves",
                "start": {"dateTime": "2026-05-28T11:00:00+02:00"},
                "end":   {"dateTime": "2026-05-28T12:00:00+02:00"},
            },
        ])
        result = sync.get_week_appointments(svc, date(2026, 5, 25))
        assert len(result) == 2
