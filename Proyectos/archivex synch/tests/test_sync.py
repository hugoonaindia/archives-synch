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


class TestKnowledge:
    KB_FIXTURE = {
        "version": 1,
        "recon_date": "2026-05-25",
        "window": {"x": 0, "y": 0, "w": 1440, "h": 900},
        "grid": {
            "start_hour": 8,
            "end_hour": 20,
            "col_offsets_pct": [0.10, 0.24, 0.38, 0.52, 0.66, 0.80, 0.94],
            "first_row_y_pct": 0.10,
            "last_row_y_pct": 0.98,
        },
        "elements": {
            "nav_prev_pct":       {"x": 0.05, "y": 0.04},
            "nav_next_pct":       {"x": 0.95, "y": 0.04},
            "patient_search_pct": {"x": 0.45, "y": 0.35},
            "first_result_pct":   {"x": 0.45, "y": 0.42},
            "save_btn_pct":       {"x": 0.65, "y": 0.85},
        },
        "visual_signatures": {
            "empty_slot":       "slot vacío sin color de fondo",
            "occupied_slot":    "slot con fondo coloreado y nombre de paciente",
            "form_open":        "modal de nueva cita visible con campo de búsqueda",
            "patient_selected": "nombre de paciente relleno en el campo",
            "appointment_saved": "formulario cerrado, cita visible en el calendario",
        },
    }

    def test_validate_knowledge_valid(self, sync):
        sync.validate_knowledge(self.KB_FIXTURE)   # should not raise

    def test_validate_knowledge_missing_key(self, sync):
        bad = {k: v for k, v in self.KB_FIXTURE.items() if k != "grid"}
        with pytest.raises(KeyError):
            sync.validate_knowledge(bad)

    def test_abs_coords_top_left(self, sync):
        x, y = sync.abs_coords(0.0, 0.0, wx=100, wy=50, ww=1440, wh=900)
        assert x == 100
        assert y == 50

    def test_abs_coords_center(self, sync):
        x, y = sync.abs_coords(0.5, 0.5, wx=0, wy=0, ww=1000, wh=800)
        assert x == 500
        assert y == 400

    def test_slot_coords_first_col_start_hour(self, sync):
        kb = self.KB_FIXTURE
        x, y = sync.slot_coords(
            day_offset=0, hour=8, minute=0,
            kb=kb, wx=0, wy=0, ww=1440, wh=900,
        )
        assert x == int(0.10 * 1440)
        assert y == int(0.10 * 900)

    def test_slot_coords_last_col_end_hour(self, sync):
        kb = self.KB_FIXTURE
        x, y = sync.slot_coords(
            day_offset=6, hour=20, minute=0,
            kb=kb, wx=0, wy=0, ww=1440, wh=900,
        )
        assert x == int(0.94 * 1440)
        assert y == int(0.98 * 900)
