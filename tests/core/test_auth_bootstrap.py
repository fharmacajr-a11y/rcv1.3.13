from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

import src.core.auth_bootstrap as auth_bootstrap


class DummySplash:
    def __init__(self, exists: bool = True) -> None:
        self.exists = exists
        self.destroy_called = False

    def winfo_exists(self) -> bool:
        return self.exists

    def destroy(self) -> None:
        self.destroy_called = True


class DummyFooter:
    def __init__(self) -> None:
        self.emails: list[str] = []

    def set_user(self, email: str) -> None:
        self.emails.append(email)


class DummyStatusMonitor:
    def __init__(self) -> None:
        self.cloud_status: list[bool] = []

    def set_cloud_status(self, status: bool) -> None:
        self.cloud_status.append(status)


class DummyApp:
    def __init__(self) -> None:
        self.footer = DummyFooter()
        self._status_monitor = DummyStatusMonitor()
        self.deiconified = False
        self.user_status_updates = 0
        self.waited_windows: list[Any] = []

    def wait_window(self, window: Any) -> None:
        self.waited_windows.append(window)

    def deiconify(self) -> None:
        self.deiconified = True

    def _update_user_status(self) -> None:
        self.user_status_updates += 1


def _build_session(access_token: str | None = None, user_email: str | None = None, user_id: str | None = None):
    user = SimpleNamespace(email=user_email, id=user_id)
    return SimpleNamespace(
        user=user,
        access_token=access_token,
    )


def test_supabase_client_success(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(auth_bootstrap, "get_supabase", lambda: sentinel)
    assert auth_bootstrap._supabase_client() is sentinel


def test_supabase_client_handles_errors(monkeypatch):
    def boom():
        raise RuntimeError("fail")

    monkeypatch.setattr(auth_bootstrap, "get_supabase", boom)
    assert auth_bootstrap._supabase_client() is None


def test_bind_postgrest_handles_success(monkeypatch):
    calls: list[Any] = []
    monkeypatch.setattr(auth_bootstrap, "bind_postgrest_auth_if_any", lambda client: calls.append(client))
    sentinel = object()
    auth_bootstrap._bind_postgrest(sentinel)
    assert calls == [sentinel]


def test_bind_postgrest_handles_exception(monkeypatch):
    def boom(client):
        raise RuntimeError("fail")

    monkeypatch.setattr(auth_bootstrap, "bind_postgrest_auth_if_any", boom)
    auth_bootstrap._bind_postgrest(object())  # should not raise


def test_is_persisted_auth_session_valid_accepts_recent_session():
    now = datetime.now(timezone.utc)
    data = {
        "access_token": "a",
        "refresh_token": "r",
        "created_at": now.isoformat(),
        "keep_logged": True,
    }

    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now + timedelta(seconds=1))


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"keep_logged": False},
        {"access_token": "a"},
        {"access_token": "a", "refresh_token": "r", "keep_logged": True, "created_at": "invalid"},
    ],
)
def test_is_persisted_auth_session_valid_rejects_invalid_payloads(data):
    assert not auth_bootstrap.is_persisted_auth_session_valid(data, now=datetime.now(timezone.utc))


def test_restore_persisted_auth_session_success(monkeypatch):
    fake_store = {
        "access_token": "a",
        "refresh_token": "r",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "keep_logged": True,
    }
    monkeypatch.setattr(auth_bootstrap.prefs_utils, "load_auth_session", lambda: fake_store.copy())
    monkeypatch.setattr(auth_bootstrap.prefs_utils, "clear_auth_session", lambda: None)
    set_session_calls: list[tuple[str, str]] = []
    client = SimpleNamespace(auth=SimpleNamespace(set_session=lambda a, r: set_session_calls.append((a, r))))

    assert auth_bootstrap.restore_persisted_auth_session_if_any(client)
    assert set_session_calls == [("a", "r")]


def test_restore_persisted_auth_session_handles_invalid_data(monkeypatch):
    monkeypatch.setattr(auth_bootstrap.prefs_utils, "load_auth_session", lambda: {"keep_logged": False})
    cleared: list[bool] = []

    monkeypatch.setattr(auth_bootstrap.prefs_utils, "clear_auth_session", lambda: cleared.append(True))

    client = SimpleNamespace()
    assert not auth_bootstrap.restore_persisted_auth_session_if_any(client)
    assert cleared == [True]


def test_restore_persisted_auth_session_handles_set_session_error(monkeypatch):
    fake_store = {
        "access_token": "a",
        "refresh_token": "r",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "keep_logged": True,
    }
    monkeypatch.setattr(auth_bootstrap.prefs_utils, "load_auth_session", lambda: fake_store.copy())
    cleaned: list[bool] = []
    monkeypatch.setattr(auth_bootstrap.prefs_utils, "clear_auth_session", lambda: cleaned.append(True))

    def fail_set_session(*_args):
        raise RuntimeError("boom")

    client = SimpleNamespace(auth=SimpleNamespace(set_session=fail_set_session))
    assert not auth_bootstrap.restore_persisted_auth_session_if_any(client)
    assert cleaned == [True]


def test_restore_persisted_auth_session_handles_load_error(monkeypatch):
    def boom():
        raise RuntimeError("read error")

    monkeypatch.setattr(auth_bootstrap.prefs_utils, "load_auth_session", boom)
    client = SimpleNamespace(auth=SimpleNamespace())
    assert not auth_bootstrap.restore_persisted_auth_session_if_any(client)


def test_restore_persisted_auth_session_handles_clear_failures(monkeypatch):
    monkeypatch.setattr(auth_bootstrap.prefs_utils, "load_auth_session", lambda: {})

    def boom():
        raise RuntimeError("clear-fail")

    monkeypatch.setattr(auth_bootstrap.prefs_utils, "clear_auth_session", boom)
    client = SimpleNamespace(auth=SimpleNamespace())
    assert not auth_bootstrap.restore_persisted_auth_session_if_any(client)


def test_restore_persisted_auth_session_handles_missing_tokens(monkeypatch):
    now = datetime.now(timezone.utc)
    store = {
        "access_token": "",
        "refresh_token": "",
        "created_at": now.isoformat(),
        "keep_logged": True,
    }
    monkeypatch.setattr(auth_bootstrap.prefs_utils, "load_auth_session", lambda: store)

    def boom():
        raise RuntimeError("clear-fail")

    monkeypatch.setattr(auth_bootstrap.prefs_utils, "clear_auth_session", boom)
    client = SimpleNamespace(auth=SimpleNamespace())
    assert not auth_bootstrap.restore_persisted_auth_session_if_any(client)


def test_restore_persisted_auth_session_handles_clear_after_set_session_error(monkeypatch):
    now = datetime.now(timezone.utc)
    store = {
        "access_token": "a",
        "refresh_token": "r",
        "created_at": now.isoformat(),
        "keep_logged": True,
    }
    monkeypatch.setattr(auth_bootstrap.prefs_utils, "load_auth_session", lambda: store)

    def fail_set_session(*_args):
        raise RuntimeError("boom")

    def boom():
        raise RuntimeError("clear-fail")

    monkeypatch.setattr(auth_bootstrap.prefs_utils, "clear_auth_session", boom)
    client = SimpleNamespace(auth=SimpleNamespace(set_session=fail_set_session))
    assert not auth_bootstrap.restore_persisted_auth_session_if_any(client)


def test_ensure_logged_happy_path(monkeypatch):
    app = DummyApp()
    splash = DummySplash()
    client = SimpleNamespace(
        auth=SimpleNamespace(
            get_session=lambda: _build_session(access_token="token", user_email="user@example.com", user_id="uid")
        ),
    )

    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: client)

    monkeypatch.setattr(auth_bootstrap, "_get_access_token", lambda _client: "token")
    refreshed: list[bool] = []
    monkeypatch.setattr(auth_bootstrap, "_refresh_session_state", lambda client, logger: refreshed.append(True))
    monkeypatch.setattr(auth_bootstrap, "restore_persisted_auth_session_if_any", lambda client: True)
    monkeypatch.setattr(auth_bootstrap, "_bind_postgrest", lambda client: None)
    monkeypatch.setattr(auth_bootstrap, "_log_session_state", lambda logger: None)

    assert auth_bootstrap.ensure_logged(app, splash=splash)
    assert splash.destroy_called
    assert app.deiconified
    assert app.user_status_updates == 1
    assert refreshed == [True]
    assert app.footer.emails == ["user@example.com"]


def test_ensure_logged_handles_login_failure(monkeypatch):
    app = DummyApp()
    monkeypatch.setattr(
        auth_bootstrap,
        "_supabase_client",
        lambda: SimpleNamespace(auth=SimpleNamespace(get_session=lambda: _build_session())),
    )
    monkeypatch.setattr(auth_bootstrap, "_get_access_token", lambda client: None)
    monkeypatch.setattr(auth_bootstrap, "restore_persisted_auth_session_if_any", lambda client: None)
    monkeypatch.setattr(auth_bootstrap, "_bind_postgrest", lambda client: None)
    monkeypatch.setattr(auth_bootstrap, "_log_session_state", lambda logger: None)
    dummy_dialog = SimpleNamespace(login_success=False)
    monkeypatch.setattr(auth_bootstrap, "LoginDialog", lambda parent: dummy_dialog)

    assert not auth_bootstrap.ensure_logged(app, splash=None)


def test_ensure_logged_returns_false_when_client_missing(monkeypatch):
    app = DummyApp()
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: None)
    monkeypatch.setattr(auth_bootstrap, "_log_session_state", lambda logger: None)

    assert not auth_bootstrap.ensure_logged(app)


def test_mark_app_online_handles_status_monitor_errors(monkeypatch):
    app = DummyApp()
    app._status_monitor = None
    updates: list[bool] = []

    def fake_update_user_status():
        updates.append(True)

    app._update_user_status = fake_update_user_status  # type: ignore[assignment]
    client = SimpleNamespace(auth=SimpleNamespace(get_session=lambda: _build_session(user_email="user@example.com")))
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: client)

    auth_bootstrap._mark_app_online(app, logger=None)
    assert updates == [True]


def test_ensure_session_handles_restore_exception(monkeypatch):
    app = DummyApp()
    client = SimpleNamespace(
        auth=SimpleNamespace(
            get_session=lambda: _build_session(),
        )
    )
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: client)

    def boom(_client):
        raise RuntimeError("restore-fail")

    monkeypatch.setattr(auth_bootstrap, "restore_persisted_auth_session_if_any", boom)
    monkeypatch.setattr(auth_bootstrap, "_bind_postgrest", lambda client: None)
    monkeypatch.setattr(auth_bootstrap, "_get_access_token", lambda client: None)
    dummy_dialog = SimpleNamespace(login_success=False)
    monkeypatch.setattr(auth_bootstrap, "LoginDialog", lambda parent: dummy_dialog)
    assert not auth_bootstrap._ensure_session(app, logger=None)


def test_ensure_session_refreshes_after_dialog_success(monkeypatch):
    app = DummyApp()
    client = SimpleNamespace(
        auth=SimpleNamespace(
            get_session=lambda: _build_session(access_token="token", user_email="user@example.com"),
        )
    )
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: client)
    monkeypatch.setattr(auth_bootstrap, "restore_persisted_auth_session_if_any", lambda client: None)
    monkeypatch.setattr(auth_bootstrap, "_bind_postgrest", lambda client: None)
    monkeypatch.setattr(auth_bootstrap, "_get_access_token", lambda client: None)
    refreshed: list[bool] = []
    monkeypatch.setattr(auth_bootstrap, "_refresh_session_state", lambda client, logger: refreshed.append(True))
    success_dialog = SimpleNamespace(login_success=True)
    monkeypatch.setattr(auth_bootstrap, "LoginDialog", lambda parent: success_dialog)

    assert auth_bootstrap._ensure_session(app, logger=None)
    assert refreshed == [True]


def test_log_session_state_handles_missing_client(monkeypatch, caplog):
    caplog.set_level("INFO")
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: None)
    auth_bootstrap._log_session_state(logger=None)
    assert "Sess" not in caplog.text


def test_log_session_state_reports_info(monkeypatch, caplog):
    caplog.set_level("INFO")
    client = SimpleNamespace(
        auth=SimpleNamespace(get_session=lambda: _build_session(access_token="token", user_email=None, user_id="uid")),
    )
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: client)
    monkeypatch.setattr(auth_bootstrap, "_get_access_token", lambda client: True)
    auth_bootstrap._log_session_state(logger=None)
    assert "uid=uid" in caplog.text


def test_log_session_state_handles_errors(monkeypatch, caplog):
    caplog.set_level("WARNING")
    client = SimpleNamespace(
        auth=SimpleNamespace(get_session=lambda: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: client)
    auth_bootstrap._log_session_state(logger=None)
    assert "Erro ao verificar sessão inicial" in caplog.text


def test_destroy_splash_handles_missing(monkeypatch):
    splash = DummySplash(exists=False)
    auth_bootstrap._destroy_splash(splash)
    assert not splash.destroy_called


def test_destroy_splash_handles_exceptions(monkeypatch):
    class BadSplash:
        def winfo_exists(self):
            raise RuntimeError("fail")

    splash = BadSplash()
    auth_bootstrap._destroy_splash(splash)  # should swallow error


def test_is_persisted_auth_session_valid_handles_naive_datetime():
    created_at = datetime.now().replace(tzinfo=None).isoformat()
    data = {
        "access_token": "a",
        "refresh_token": "r",
        "created_at": created_at,
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=datetime.now(timezone.utc))


def test_refresh_session_state_handles_exception(monkeypatch, caplog):
    caplog.set_level("WARNING")

    def boom():
        raise RuntimeError("fail")

    monkeypatch.setattr(auth_bootstrap, "refresh_current_user_from_supabase", boom)
    auth_bootstrap._refresh_session_state(client=None, logger=None)
    assert "Falha ao hidratar" in caplog.text


def test_update_footer_email_handles_no_client(monkeypatch):
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: None)
    auth_bootstrap._update_footer_email(DummyApp())


def test_update_footer_email_handles_exception(monkeypatch):
    client = SimpleNamespace(
        auth=SimpleNamespace(
            get_session=lambda: _build_session(user_email="user@example.com"),
        )
    )
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: client)
    app = DummyApp()

    def boom(email):
        raise RuntimeError("fail")

    app.footer.set_user = boom  # type: ignore[assignment]
    auth_bootstrap._update_footer_email(app)


def test_mark_app_online_exception_paths(monkeypatch):
    app = DummyApp()

    def boom_deiconify():
        raise RuntimeError("fail")

    app.deiconify = boom_deiconify  # type: ignore[assignment]
    app._status_monitor = SimpleNamespace(set_cloud_status=lambda status: (_ for _ in ()).throw(RuntimeError("fail")))

    def boom_update_user_status():
        raise RuntimeError("fail")

    app._update_user_status = boom_update_user_status  # type: ignore[assignment]
    monkeypatch.setattr(auth_bootstrap, "_supabase_client", lambda: None)

    auth_bootstrap._mark_app_online(app, logger=None)
