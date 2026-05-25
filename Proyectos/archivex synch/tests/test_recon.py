"""Unit tests for recon.py validation logic."""
import sys
from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def mock_pyautogui():
    sys.modules["pyautogui"] = Mock()
    yield
    sys.modules.pop("recon", None)


@pytest.fixture
def recon():
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    import recon as r
    return r


class TestValidateReconOutput:
    VALID = {
        "version": 1,
        "recon_date": "2026-05-25",
        "window": {"x": 0, "y": 0, "w": 1440, "h": 900},
        "grid": {
            "start_hour": 8,
            "end_hour": 20,
            "col_offsets_pct": [0.1, 0.24, 0.38, 0.52, 0.66, 0.80, 0.94],
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
            "empty_slot":        "slot vacío",
            "occupied_slot":     "slot ocupado",
            "form_open":         "formulario abierto",
            "patient_selected":  "paciente seleccionado",
            "appointment_saved": "cita guardada",
        },
    }

    def test_valid_knowledge_passes(self, recon):
        recon.validate_recon_output(self.VALID)   # no exception

    def test_missing_grid_raises(self, recon):
        bad = {k: v for k, v in self.VALID.items() if k != "grid"}
        with pytest.raises(ValueError, match="grid"):
            recon.validate_recon_output(bad)

    def test_wrong_col_count_raises(self, recon):
        bad = {**self.VALID, "grid": {**self.VALID["grid"],
               "col_offsets_pct": [0.1, 0.2]}}
        with pytest.raises(ValueError, match="7"):
            recon.validate_recon_output(bad)

    def test_coord_out_of_range_raises(self, recon):
        bad = {**self.VALID, "elements": {
            **self.VALID["elements"],
            "nav_next_pct": {"x": 1.5, "y": 0.04},
        }}
        with pytest.raises(ValueError, match="rango"):
            recon.validate_recon_output(bad)

    def test_missing_visual_signature_raises(self, recon):
        bad = {**self.VALID, "visual_signatures": {
            k: v for k, v in self.VALID["visual_signatures"].items()
            if k != "empty_slot"
        }}
        with pytest.raises(ValueError, match="empty_slot"):
            recon.validate_recon_output(bad)
