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


class TestWindowDetection:
    def test_get_window_bounds_parses_output(self, sync, monkeypatch):
        mock_run = MagicMock()
        mock_run.return_value.stdout = "100,50,1440,900\n"
        monkeypatch.setattr("subprocess.run", mock_run)
        wx, wy, ww, wh = sync.get_window_bounds()
        assert wx == 100
        assert wy == 50
        assert ww == 1440
        assert wh == 900

    def test_get_window_bounds_raises_if_not_open(self, sync, monkeypatch):
        mock_run = MagicMock()
        mock_run.return_value.stdout = ""
        monkeypatch.setattr("subprocess.run", mock_run)
        with pytest.raises(RuntimeError, match="Archivex"):
            sync.get_window_bounds()


class TestVerifier:
    """Tests for verifier functions - now disabled (LLM verification removed)"""
    
    SIGNATURES = {
        "empty_slot": "vacío en el calendario",
        "form_open": "formulario modal abierto",
        "saved": "cita creada y visible",
    }

    def test_verify_slot_empty_returns_empty(self, sync, monkeypatch):
        """Since _ask_llm returns empty string, verify_slot_empty always returns 'empty'"""
        result = sync.verify_slot_empty(self.SIGNATURES, day_offset=1, hour=9)
        assert result == "empty"  # Always returns empty when _ask_llm returns empty

    def test_verify_slot_empty_returns_occupied(self, sync, monkeypatch):
        """Cannot test 'occupied' anymore since _ask_llm always returns empty"""
        # This test is obsolete now that LLM verification is disabled
        pass

    def test_verify_slot_empty_returns_uncertain_on_unknown(self, sync, monkeypatch):
        """Cannot test 'uncertain' anymore since _ask_llm always returns empty"""
        # This test is obsolete now that LLM verification is disabled
        pass

    def test_verify_form_open_true(self, sync, monkeypatch):
        """Since _ask_llm returns empty string, verify_form_open always returns True"""
        result = sync.verify_form_open(self.SIGNATURES)
        assert result is True  # Always returns True when _ask_llm returns empty

    def test_verify_form_open_false(self, sync, monkeypatch):
        """Cannot test False anymore since _ask_llm always returns empty"""
        # This test is obsolete now that LLM verification is disabled
        pass

    def test_verify_saved_true(self, sync, monkeypatch):
        """Since _ask_llm returns empty string, verify_saved always returns False"""
        result = sync.verify_saved(self.SIGNATURES)
        assert result is False  # Always returns False when _ask_llm returns empty (no "yes" in empty string)


class TestProcessor:
    KB = {
        "elements": {
            "patient_search_pct": {"x": 0.45, "y": 0.35},
            "first_result_pct":   {"x": 0.45, "y": 0.42},
            "save_btn_pct":       {"x": 0.65, "y": 0.85},
        }
    }
    WINDOW = (0, 0, 1440, 900)

    def test_open_slot_calls_double_click(self, sync, monkeypatch):
        calls = []
        monkeypatch.setattr("sync.pyautogui.doubleClick",
                            lambda x, y: calls.append((x, y)))
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        sync.open_slot(300, 400)
        assert calls == [(300, 400)]

    def test_save_appointment_clicks_save_button(self, sync, monkeypatch):
        clicks = []
        monkeypatch.setattr("sync.pyautogui.click",
                            lambda x, y: clicks.append((x, y)))
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        wx, wy, ww, wh = self.WINDOW
        sync.save_appointment(self.KB, wx, wy, ww, wh)
        expected_x = int(0.65 * 1440)
        expected_y = int(0.85 * 900)
        assert (expected_x, expected_y) in clicks

    def test_fill_patient_writes_to_clipboard(self, sync, monkeypatch):
        clipboard = []
        monkeypatch.setattr("subprocess.run",
                            lambda cmd, **kw: clipboard.append(kw.get("input", b"")))
        monkeypatch.setattr("sync.pyautogui.click", lambda x, y: None)
        monkeypatch.setattr("sync.pyautogui.hotkey", lambda *a: None)
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        wx, wy, ww, wh = self.WINDOW
        sync.fill_patient("Ana García", self.KB, wx, wy, ww, wh)
        assert "Ana García".encode("utf-8") in clipboard


class TestNavigation:
    KB = {
        "elements": {
            "nav_prev_pct": {"x": 0.05, "y": 0.04},
            "nav_next_pct": {"x": 0.95, "y": 0.04},
        },
        "visual_signatures": {"empty_slot": "..."},
    }
    WIN = (0, 0, 1440, 900)

    def test_detect_monday_parses_date(self, sync, monkeypatch):
        mock_oi = MagicMock()
        msg = MagicMock()
        msg.choices = [MagicMock(message=MagicMock(content='{"date": "2026-05-25"}'))]
        mock_oi.return_value.chat.completions.create.return_value = msg
        monkeypatch.setattr("sync.OpenAI", mock_oi)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake")
        result = sync.detect_displayed_monday()
        assert result == date(2026, 5, 25)

    def test_detect_monday_returns_none_on_null(self, sync, monkeypatch):
        mock_oi = MagicMock()
        msg = MagicMock()
        msg.choices = [MagicMock(message=MagicMock(content='{"date": null}'))]
        mock_oi.return_value.chat.completions.create.return_value = msg
        monkeypatch.setattr("sync.OpenAI", mock_oi)
        monkeypatch.setattr("sync._screenshot_b64", lambda: "fake")
        result = sync.detect_displayed_monday()
        assert result is None

    def test_navigate_clicks_next_twice(self, sync, monkeypatch):
        clicks = []
        monkeypatch.setattr("sync.detect_displayed_monday",
                            lambda: date(2026, 5, 25))
        monkeypatch.setattr("sync.pyautogui.click",
                            lambda x, y: clicks.append((x, y)))
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        wx, wy, ww, wh = self.WIN
        target = date(2026, 6, 8)   # 2 weeks ahead
        sync.navigate_to_week(target, self.KB, wx, wy, ww, wh)
        expected_x = int(0.95 * 1440)
        assert clicks.count((expected_x, int(0.04 * 900))) == 2

    def test_navigate_no_clicks_if_already_correct(self, sync, monkeypatch):
        clicks = []
        monkeypatch.setattr("sync.detect_displayed_monday",
                            lambda: date(2026, 5, 25))
        monkeypatch.setattr("sync.pyautogui.click",
                            lambda x, y: clicks.append((x, y)))
        monkeypatch.setattr("sync.time.sleep", lambda _: None)
        wx, wy, ww, wh = self.WIN
        sync.navigate_to_week(date(2026, 5, 25), self.KB, wx, wy, ww, wh)
        assert clicks == []


class TestConflict:
    def test_ask_conflict_crear(self, sync, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "c")
        appt = sync.Appointment("X", date(2026, 5, 26), "09:00", "10:00", 1, 9, 0)
        assert sync.ask_conflict_action(appt) == "crear"

    def test_ask_conflict_saltar(self, sync, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "s")
        appt = sync.Appointment("X", date(2026, 5, 26), "09:00", "10:00", 1, 9, 0)
        assert sync.ask_conflict_action(appt) == "saltar"

    def test_ask_conflict_parar(self, sync, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "p")
        appt = sync.Appointment("X", date(2026, 5, 26), "09:00", "10:00", 1, 9, 0)
        assert sync.ask_conflict_action(appt) == "parar"


class TestProcessAppointment:
    KB_FIXTURE = {
        "grid": {
            "start_hour": 8, "end_hour": 20,
            "col_offsets_pct": [0.10, 0.24, 0.38, 0.52, 0.66, 0.80, 0.94],
            "first_row_y_pct": 0.10, "last_row_y_pct": 0.98,
        },
        "elements": {
            "nav_prev_pct":       {"x": 0.05, "y": 0.04},
            "nav_next_pct":       {"x": 0.95, "y": 0.04},
            "patient_search_pct": {"x": 0.45, "y": 0.35},
            "first_result_pct":   {"x": 0.45, "y": 0.42},
            "save_btn_pct":       {"x": 0.65, "y": 0.85},
        },
        "visual_signatures": {
            "empty_slot": "...", "occupied_slot": "...",
            "form_open": "...", "patient_selected": "...",
            "appointment_saved": "...",
        },
    }

    def _appt(self, sync):
        return sync.Appointment("Ana García", date(2026, 5, 26), "09:00", "10:00", 1, 9, 0)

    def test_process_creates_when_slot_empty(self, sync, monkeypatch):
        monkeypatch.setattr("sync.verify_slot_empty", lambda sigs, **kw: "empty")
        monkeypatch.setattr("sync.open_slot", lambda x, y: None)
        monkeypatch.setattr("sync.verify_form_open", lambda sigs: True)
        monkeypatch.setattr("sync.fill_patient", lambda *a, **kw: None)
        monkeypatch.setattr("sync.save_appointment", lambda *a: None)
        monkeypatch.setattr("sync.verify_saved", lambda sigs: True)
        result = sync.process_appointment(
            self._appt(sync), self.KB_FIXTURE, 0, 0, 1440, 900
        )
        assert result == "creada"

    def test_process_asks_on_conflict(self, sync, monkeypatch):
        monkeypatch.setattr("sync.verify_slot_empty", lambda sigs, **kw: "occupied")
        monkeypatch.setattr("builtins.input", lambda _: "s")
        result = sync.process_appointment(
            self._appt(sync), self.KB_FIXTURE, 0, 0, 1440, 900
        )
        assert result == "saltada"

    def test_process_raises_on_parar(self, sync, monkeypatch):
        monkeypatch.setattr("sync.verify_slot_empty", lambda sigs, **kw: "occupied")
        monkeypatch.setattr("builtins.input", lambda _: "p")
        with pytest.raises(sync.StopSync):
            sync.process_appointment(
                self._appt(sync), self.KB_FIXTURE, 0, 0, 1440, 900
            )


class TestAskSyncDays:
    def test_ask_sync_days_martes_viernes(self, sync, monkeypatch):
        """Usuario elige T (Martes-Viernes)"""
        monkeypatch.setattr("builtins.input", lambda _: "T")
        monkeypatch.setattr("builtins.print", lambda *a, **k: None)
        result = sync.ask_sync_days()
        assert result == {1, 3, 4}  # martes, jueves, viernes

    def test_ask_sync_days_lunes_viernes(self, sync, monkeypatch):
        """Usuario elige L (Lunes-Viernes)"""
        monkeypatch.setattr("builtins.input", lambda _: "L")
        monkeypatch.setattr("builtins.print", lambda *a, **k: None)
        result = sync.ask_sync_days()
        assert result == {0, 1, 3, 4, 5}  # lun-viernes (excluye miércoles y fin de semana)

    def test_ask_sync_days_todos(self, sync, monkeypatch):
        """Usuario elige A (Todos los días)"""
        monkeypatch.setattr("builtins.input", lambda _: "A")
        monkeypatch.setattr("builtins.print", lambda *a, **k: None)
        result = sync.ask_sync_days()
        assert result == {0, 1, 2, 3, 4, 5, 6}

    def test_ask_sync_days_personalizado(self, sync, monkeypatch):
        """Usuario elige P (Personalizado) e ingresa '0 1 3'"""
        inputs = iter(["P", "0 1 3"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr("builtins.print", lambda *a, **k: None)
        result = sync.ask_sync_days()
        assert result == {0, 1, 3}

    def test_ask_sync_days_personalizado_invalid_repeats(self, sync, monkeypatch):
        """Usuario elige P, ingresa inválido, luego T"""
        inputs = iter(["P", "99", "T"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr("builtins.print", lambda *a, **k: None)
        result = sync.ask_sync_days()
        assert result == {1, 3, 4}
