from __future__ import annotations

import src.core.session.session_guard as session_guard


class StubSession:
    def __init__(self, access_token: str | None, refresh_token: str | None):
        self.access_token = access_token
        self.refresh_token = refresh_token


class StubResponse:
    def __init__(self, session: StubSession | None):
        self.session = session


class StubAuth:
    def __init__(self, get_session_fn, refresh_session_fn):
        self._get_session_fn = get_session_fn
        self._refresh_session_fn = refresh_session_fn

    def get_session(self):
        return self._get_session_fn()

    def refresh_session(self):
        return self._refresh_session_fn()


class StubSupabase:
    def __init__(self, auth: StubAuth):
        self.auth = auth


def make_supabase(get_session_fn, refresh_session_fn):
    return StubSupabase(StubAuth(get_session_fn, refresh_session_fn))


def test_ensure_alive_returns_true_when_get_session_has_valid_tokens(monkeypatch):
    def refresh_should_not_run():
        raise AssertionError("refresh should not run")

    supabase = make_supabase(
        lambda: StubResponse(StubSession("access-token", "refresh-token")),
        refresh_should_not_run,
    )
    monkeypatch.setattr(session_guard, "get_supabase", lambda: supabase)

    set_tokens_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        session_guard.session, "set_tokens", lambda access, refresh: set_tokens_calls.append((access, refresh))
    )

    assert session_guard.SessionGuard.ensure_alive() is True
    assert set_tokens_calls == []


def test_ensure_alive_refreshes_when_initial_session_missing_token(monkeypatch):
    refresh_called: list[bool] = []

    def do_refresh():
        refresh_called.append(True)
        return StubResponse(StubSession("new-access", "new-refresh"))

    supabase = make_supabase(
        lambda: StubResponse(StubSession(None, "refresh-token")),
        do_refresh,
    )
    monkeypatch.setattr(session_guard, "get_supabase", lambda: supabase)

    set_tokens_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        session_guard.session, "set_tokens", lambda access, refresh: set_tokens_calls.append((access, refresh))
    )

    assert session_guard.SessionGuard.ensure_alive() is True
    assert refresh_called == [True]
    assert set_tokens_calls == [("new-access", "new-refresh")]


def test_ensure_alive_returns_false_when_get_and_refresh_fail(monkeypatch):
    def fail_get():
        raise RuntimeError("get failed")

    def fail_refresh():
        raise RuntimeError("refresh failed")

    supabase = make_supabase(
        fail_get,
        fail_refresh,
    )
    monkeypatch.setattr(session_guard, "get_supabase", lambda: supabase)

    set_tokens_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        session_guard.session, "set_tokens", lambda access, refresh: set_tokens_calls.append((access, refresh))
    )

    assert session_guard.SessionGuard.ensure_alive() is False
    assert set_tokens_calls == []
