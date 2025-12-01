from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

import pytest

from src.core import auth_bootstrap
from src.utils import prefs as prefs_module


@pytest.fixture
def temp_auth_prefs_dir_bootstrap(monkeypatch, tmp_path):
    prefs_dir = tmp_path / "auth_prefs_bootstrap"
    prefs_dir.mkdir()
    monkeypatch.setattr("src.utils.prefs._get_base_dir", lambda: str(prefs_dir))
    return prefs_dir


def test_is_persisted_auth_session_valid_with_recent_date():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": created_at,
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now, max_age_days=7) is True


def test_is_persisted_auth_session_valid_expired():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    created_at = (now - timedelta(days=8)).isoformat()
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": created_at,
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now, max_age_days=7) is False


class DummyAuth:
    def __init__(self):
        self.last_session = None
        self.access_token = ""
        self.refresh_token = ""

    def set_session(self, access_token, refresh_token):
        self.last_session = (access_token, refresh_token)
        self.access_token = access_token
        self.refresh_token = refresh_token

        class DummyResponse:
            session = object()

        return DummyResponse()

    def get_session(self):
        class DummySession:
            def __init__(self, at, rt):
                self.access_token = at
                self.refresh_token = rt
                self.user = type("U", (), {"id": "uid-1", "email": "user@test.com"})

        return DummySession(self.access_token, self.refresh_token)


class DummyClient:
    def __init__(self):
        self.auth = DummyAuth()


def test_restore_persisted_auth_session_if_any_success(temp_auth_prefs_dir_bootstrap):
    prefs_module.save_auth_session("at", "rt", keep_logged=True)

    client = DummyClient()
    restored = auth_bootstrap.restore_persisted_auth_session_if_any(client)

    assert restored is True
    assert client.auth.last_session == ("at", "rt")


def test_restore_persisted_auth_session_if_any_expired(temp_auth_prefs_dir_bootstrap):
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    path = prefs_module._auth_session_path()
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    data = {"access_token": "at", "refresh_token": "rt", "created_at": old_date, "keep_logged": True}
    Path(path).write_text(json.dumps(data), encoding="utf-8")

    client = DummyClient()
    restored = auth_bootstrap.restore_persisted_auth_session_if_any(client)

    assert restored is False
    assert client.auth.last_session is None
