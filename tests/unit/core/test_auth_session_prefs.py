import pytest
from pathlib import Path

from src.utils import prefs as prefs_module


@pytest.fixture
def temp_auth_prefs_dir(monkeypatch, tmp_path):
    prefs_dir = tmp_path / "auth_prefs"
    prefs_dir.mkdir()
    monkeypatch.setattr("src.utils.prefs._get_base_dir", lambda: str(prefs_dir))
    return prefs_dir


def test_save_and_load_auth_session_basic(temp_auth_prefs_dir):
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    data = prefs_module.load_auth_session()
    assert data["access_token"] == "at"
    assert data["refresh_token"] == "rt"
    assert data["keep_logged"] is True
    assert data["created_at"]


def test_save_auth_session_clears_when_not_keep_logged(temp_auth_prefs_dir):
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    assert prefs_module.load_auth_session().get("access_token") == "at"

    prefs_module.save_auth_session("ignored", "ignored", keep_logged=False)
    data = prefs_module.load_auth_session()
    assert not data or not data.get("access_token")


def test_load_auth_session_corrupted_returns_empty(temp_auth_prefs_dir):
    path = Path(prefs_module._auth_session_path())
    path.write_text("{ invalid json", encoding="utf-8")

    data = prefs_module.load_auth_session()
    assert data == {}
