import pytest
from pathlib import Path


@pytest.fixture
def temp_login_prefs_dir(monkeypatch, tmp_path):
    prefs_dir = tmp_path / "login_prefs"
    prefs_dir.mkdir()
    monkeypatch.setattr("src.utils.prefs._get_base_dir", lambda: str(prefs_dir))
    return prefs_dir


def test_save_and_load_login_prefs_basic(temp_login_prefs_dir):
    from src.utils import prefs as prefs_module

    prefs_module.save_login_prefs("user@test.com", True)
    data = prefs_module.load_login_prefs()

    assert data.get("email") == "user@test.com"
    assert data.get("remember_email") is True


def test_save_login_prefs_clear_when_not_remember(temp_login_prefs_dir):
    from src.utils import prefs as prefs_module

    prefs_module.save_login_prefs("user@test.com", True)
    assert prefs_module.load_login_prefs().get("email") == "user@test.com"

    prefs_module.save_login_prefs("outra@test.com", False)
    data = prefs_module.load_login_prefs()
    assert data == {} or not data.get("email")


def test_load_login_prefs_corrupted_returns_empty(temp_login_prefs_dir):
    from src.utils import prefs as prefs_module

    path = Path(prefs_module._login_prefs_path())
    path.write_text("{ invalid json }", encoding="utf-8")

    data = prefs_module.load_login_prefs()
    assert data == {}
