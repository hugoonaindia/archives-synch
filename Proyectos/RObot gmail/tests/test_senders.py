"""Tests para persistencia y gestión de remitentes."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import gmail_bulk_trash as gbt


def test_load_senders_nonexistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "nonexistent_senders.json"
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            data = gbt.load_senders()
            assert data == {"blocked": [], "whitelist": []}


def test_load_senders_valid_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        fake_path.write_text(json.dumps({"blocked": ["a@b.com"], "whitelist": ["c@d.com"]}))
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            data = gbt.load_senders()
            assert data == {"blocked": ["a@b.com"], "whitelist": ["c@d.com"]}


def test_load_senders_corrupted_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        fake_path.write_text("{invalid json!!!")
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            data = gbt.load_senders()
            assert data == {"blocked": [], "whitelist": []}


def test_load_senders_missing_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        fake_path.write_text(json.dumps({"blocked": ["a@b.com"]}))
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            data = gbt.load_senders()
            assert data == {"blocked": [], "whitelist": []}


def test_save_senders():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            gbt.save_senders({"blocked": ["x@y.com"], "whitelist": []})
            saved = json.loads(fake_path.read_text())
            assert saved == {"blocked": ["x@y.com"], "whitelist": []}


def test_build_query_blocklist_only():
    senders = {"blocked": ["spam@test.com"], "whitelist": []}
    result = gbt.build_query("category:promotions", senders)
    expected = "(category:promotions) OR (from:spam@test.com)"
    assert result == expected, f"Expected {expected}, got {result}"


def test_build_query_whitelist_exclusion():
    senders = {"blocked": ["spam@test.com"], "whitelist": ["boss@company.com"]}
    result = gbt.build_query("category:promotions", senders)
    assert "-from:boss@company.com" in result
    assert "spam@test.com" in result


def test_build_query_empty():
    senders = {"blocked": [], "whitelist": []}
    assert gbt.build_query("", senders) == ""


def test_build_query_blocked_only():
    senders = {"blocked": ["a@x.com", "b@y.com"], "whitelist": []}
    result = gbt.build_query("", senders)
    assert "from:a@x.com" in result
    assert "from:b@y.com" in result


def test_api_call_with_retry_success():
    mock_fn = MagicMock(return_value="ok")
    result = gbt.api_call_with_retry(mock_fn, "test")
    assert result == "ok"
    mock_fn.assert_called_once()


def test_api_call_with_retry_rate_limit():
    from googleapiclient.errors import HttpError

    mock_resp = MagicMock()
    mock_resp.status = 429
    error_429 = HttpError(mock_resp, b"rate limit")

    mock_fn = MagicMock(side_effect=[error_429, "ok"])
    with patch("gmail_bulk_trash.time.sleep"):
        result = gbt.api_call_with_retry(mock_fn, "test")
    assert result == "ok"
    assert mock_fn.call_count == 2


def test_api_call_with_retry_non_429_raises():
    from googleapiclient.errors import HttpError

    mock_resp = MagicMock()
    mock_resp.status = 500
    error_500 = HttpError(mock_resp, b"server error")

    mock_fn = MagicMock(side_effect=error_500)
    try:
        gbt.api_call_with_retry(mock_fn, "test")
        assert False, "Should have raised"
    except HttpError:
        pass


def _make_args(**kwargs):
    import argparse
    defaults = {
        "add_sender": None, "remove_sender": None,
        "add_whitelist": None, "remove_whitelist": None,
        "list_senders": False, "query": None,
        "before": None, "after": None, "dry_run": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_manage_senders_add_blocked():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            args = _make_args(add_sender=["Spam@Test.COM"])
            result = gbt.manage_senders(args)
            assert result is True
            data = json.loads(fake_path.read_text())
            assert "spam@test.com" in data["blocked"]


def test_manage_senders_add_duplicate():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        fake_path.write_text(json.dumps({"blocked": ["spam@test.com"], "whitelist": []}))
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            args = _make_args(add_sender=["spam@test.com"])
            result = gbt.manage_senders(args)
            assert result is True
            data = json.loads(fake_path.read_text())
            assert data["blocked"].count("spam@test.com") == 1


def test_manage_senders_remove_blocked():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        fake_path.write_text(json.dumps({"blocked": ["a@x.com", "b@y.com"], "whitelist": []}))
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            args = _make_args(remove_sender=["a@x.com"])
            result = gbt.manage_senders(args)
            assert result is True
            data = json.loads(fake_path.read_text())
            assert "a@x.com" not in data["blocked"]
            assert "b@y.com" in data["blocked"]


def test_manage_senders_add_whitelist():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            args = _make_args(add_whitelist=["boss@work.com"])
            result = gbt.manage_senders(args)
            assert result is True
            data = json.loads(fake_path.read_text())
            assert "boss@work.com" in data["whitelist"]


def test_manage_senders_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        fake_path.write_text(json.dumps({"blocked": ["x@y.com"], "whitelist": ["a@b.com"]}))
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            args = _make_args(list_senders=True)
            result = gbt.manage_senders(args)
            assert result is True


def test_manage_senders_no_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            args = _make_args()
            result = gbt.manage_senders(args)
            assert result is False


def test_parse_email_simple():
    assert gbt.parse_email("user@example.com") == "user@example.com"


def test_parse_email_with_name():
    assert gbt.parse_email("User <user@example.com>") == "user@example.com"


def test_parse_email_multi_angle():
    assert gbt.parse_email("<a@x.com> <b@x.com>") == "a@x.com"


def test_parse_email_empty():
    assert gbt.parse_email("") == ""


def test_parse_email_whitespace():
    assert gbt.parse_email("  User <user@example.com>  ") == "user@example.com"


def test_get_top_senders_returns_sorted():
    mock_service = MagicMock()
    def mock_get(**kwargs):
        result = MagicMock()
        sender_map = {
            "id1": "spam@ads.com",
            "id2": "spam@ads.com",
            "id3": "news@promo.com",
            "id4": "spam@ads.com",
            "id5": "news@promo.com",
        }
        def execute():
            return {
                "payload": {
                    "headers": [{"name": "From", "value": sender_map.get(kwargs["id"], "unknown@x.com")}]
                }
            }
        result.execute = execute
        return result
    mock_service.users().messages().get = mock_get

    ids = ["id1", "id2", "id3", "id4", "id5"]
    top, sender_ids = gbt.get_top_senders(mock_service, ids, top_n=10)

    assert len(top) == 2
    assert top[0] == ("spam@ads.com", 3)
    assert top[1] == ("news@promo.com", 2)
    assert sender_ids["spam@ads.com"] == ["id1", "id2", "id4"]
    assert sender_ids["news@promo.com"] == ["id3", "id5"]


def test_get_top_senders_empty():
    mock_service = MagicMock()
    top, sender_ids = gbt.get_top_senders(mock_service, [], top_n=10)
    assert top == []
    assert sender_ids == {}


def test_get_top_senders_top_n():
    mock_service = MagicMock()
    def mock_get(**kwargs):
        result = MagicMock()
        def execute():
            return {"payload": {"headers": [{"name": "From", "value": f"sender{kwargs['id']}@x.com"}]}}
        result.execute = execute
        return result
    mock_service.users().messages().get = mock_get

    ids = [f"id{i}" for i in range(50)]
    top, sender_ids = gbt.get_top_senders(mock_service, ids, top_n=3)
    assert len(top) <= 3


def test_interactive_menu_quit():
    top = [("spam@x.com", 10), ("news@y.com", 5)]
    sender_ids = {"spam@x.com": ["a", "b"], "news@y.com": ["c"]}
    mock_service = MagicMock()

    with patch("builtins.input", side_effect=["q"]):
        result = gbt.interactive_sender_menu(mock_service, top, sender_ids, {"blocked": [], "whitelist": []})

    assert result is False


def test_interactive_menu_add_blocked():
    import tempfile, json
    from pathlib import Path

    top = [("spam@x.com", 10)]
    sender_ids = {"spam@x.com": ["a", "b"]}
    mock_service = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "senders.json"
        with patch.object(gbt, "SENDERS_FILE", fake_path):
            with patch("builtins.input", side_effect=["1", "3", "q"]):
                result = gbt.interactive_sender_menu(mock_service, top, sender_ids, {"blocked": [], "whitelist": []})
            data = json.loads(fake_path.read_text())
            assert "spam@x.com" in data["blocked"]
            assert result is True


def test_interactive_menu_trash():
    top = [("spam@x.com", 2)]
    sender_ids = {"spam@x.com": ["id1", "id2"]}
    mock_service = MagicMock()

    with patch("builtins.input", side_effect=["1", "1", "q"]):
        gbt.interactive_sender_menu(mock_service, top, sender_ids, {"blocked": [], "whitelist": []})

    mock_service.users().messages().batchModify.assert_called_once()
    call_body = mock_service.users().messages().batchModify.call_args[1]["body"]
    assert call_body["ids"] == ["id1", "id2"]
    assert "TRASH" in call_body["addLabelIds"]
