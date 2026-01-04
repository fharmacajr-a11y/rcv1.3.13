from __future__ import annotations

import importlib

import pytest

import src.data.auth_bootstrap as auth_bootstrap


class DummyAuth:
    def __init__(self, session=None, sign_in_result=None):
        self._session = session
        self._sign_in_result = sign_in_result
        self.sign_in_calls = []

    def get_session(self):
        return self._session

    def sign_in_with_password(self, payload):
        self.sign_in_calls.append(payload)
        if isinstance(self._sign_in_result, Exception):
            raise self._sign_in_result
        return self._sign_in_result


class DummyPostgrest:
    def __init__(self):
        self.auth_calls = []

    def auth(self, token):
        if token == "fail":
            raise RuntimeError("auth failed")
        self.auth_calls.append(token)


class DummyClient:
    def __init__(self, session=None, sign_in_result=None):
        self.auth = DummyAuth(session=session, sign_in_result=sign_in_result)
        self.postgrest = DummyPostgrest()


def reload_module(monkeypatch):
    importlib.reload(auth_bootstrap)
    return auth_bootstrap


def test_get_access_token_returns_token(monkeypatch):
    client = DummyClient(session=type("S", (), {"access_token": "abc"})())

    token = auth_bootstrap._get_access_token(client)

    assert token == "abc"


def test_get_access_token_handles_exception(monkeypatch):
    class BadClient:
        def __init__(self):
            self.auth = type("A", (), {"get_session": lambda self: (_ for _ in ()).throw(RuntimeError("boom"))})()

    token = auth_bootstrap._get_access_token(BadClient())

    assert token is None


def test_postgrest_bind_no_token():
    client = DummyClient()

    auth_bootstrap._postgrest_bind(client, None)

    assert client.postgrest.auth_calls == []


def test_postgrest_bind_calls_auth_and_logs(monkeypatch, caplog):
    client = DummyClient()

    auth_bootstrap._postgrest_bind(client, "token123")

    assert client.postgrest.auth_calls == ["token123"]

    with caplog.at_level("WARNING", logger=auth_bootstrap.log.name):
        auth_bootstrap._postgrest_bind(client, "fail")

    assert any("postgrest.auth falhou" in rec.getMessage() for rec in caplog.records)


def test_ensure_signed_in_returns_when_token_exists(monkeypatch):
    client = DummyClient(session=type("S", (), {"access_token": "tok"})())

    auth_bootstrap.ensure_signed_in(client)

    assert client.postgrest.auth_calls == ["tok"]
    assert client.auth.sign_in_calls == []


def test_ensure_signed_in_login_dev_success(monkeypatch):
    client = DummyClient(session=None, sign_in_result={"ok": True})

    monkeypatch.setenv("SUPABASE_EMAIL", "user@example.com")
    monkeypatch.setenv("SUPABASE_PASSWORD", "secret")
    calls = []

    def fake_get_access_token(_client):
        calls.append("called")
        return None if len(calls) == 1 else "token-from-dev"

    monkeypatch.setattr(auth_bootstrap, "_get_access_token", fake_get_access_token)

    auth_bootstrap.ensure_signed_in(client)

    assert client.auth.sign_in_calls == [{"email": "user@example.com", "password": "secret"}]
    assert client.postgrest.auth_calls == ["token-from-dev"]


def test_ensure_signed_in_login_dev_without_token(monkeypatch):
    client = DummyClient(session=None, sign_in_result={"ok": True})

    monkeypatch.setenv("SUPABASE_EMAIL", "user@example.com")
    monkeypatch.setenv("SUPABASE_PASSWORD", "secret")
    # After sign in, session still lacks token
    monkeypatch.setattr(auth_bootstrap, "_get_access_token", lambda _c: None)

    with pytest.raises(RuntimeError, match="Falha no login DEV"):
        auth_bootstrap.ensure_signed_in(client)


def test_ensure_signed_in_missing_envs(monkeypatch):
    client = DummyClient(session=None)
    monkeypatch.delenv("SUPABASE_EMAIL", raising=False)
    monkeypatch.delenv("SUPABASE_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="Sem sessão Supabase"):
        auth_bootstrap.ensure_signed_in(client)
