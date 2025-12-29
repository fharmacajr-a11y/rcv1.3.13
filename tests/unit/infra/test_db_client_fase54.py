"""
TESTE_1 - infra/supabase/db_client

Objetivo: aumentar a cobertura de infra/supabase/db_client.py na fase 54,
cobrindo selects, inserts, updates e tratamento de erros do client Supabase/Postgrest.
"""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import infra.supabase.db_client as db_client


def test_health_check_rpc_retorna_ok(monkeypatch):
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_USE_RPC", True)
    monkeypatch.setattr(
        db_client,
        "exec_postgrest",
        lambda builder: SimpleNamespace(data="ok", builder=builder),
    )
    client = SimpleNamespace(rpc=lambda name: f"rpc:{name}")

    assert db_client._health_check_once(client) is True


def test_health_check_rpc_404_fallback_auth(monkeypatch):
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_USE_RPC", True)
    monkeypatch.setattr(db_client, "exec_postgrest", lambda builder: (_ for _ in ()).throw(Exception("404 Not Found")))

    class FakeHTTPX:
        def __init__(self):
            self.calls = []

        def get(self, url, timeout):
            self.calls.append((url, timeout))
            return SimpleNamespace(status_code=200, json=lambda: {"version": "1.0"})

    fake_httpx = FakeHTTPX()
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    client = SimpleNamespace(rpc=lambda name: f"rpc:{name}")

    assert db_client._health_check_once(client) is True
    assert fake_httpx.calls


def test_health_check_fallback_table(monkeypatch):
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_USE_RPC", False)
    recorded = {}

    class Builder:
        def select(self, *a, **k):
            return self

        def limit(self, value):
            recorded["limit"] = value
            return self

    def fake_exec(builder):
        recorded["builder"] = builder
        return SimpleNamespace(data=[])

    monkeypatch.setattr(db_client, "exec_postgrest", fake_exec)
    client = SimpleNamespace(table=lambda name: Builder())

    assert db_client._health_check_once(client) is True
    assert recorded["builder"] is not None
    assert recorded["limit"] == 1


def test_health_check_fallback_error(monkeypatch):
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_USE_RPC", False)
    monkeypatch.setattr(db_client, "exec_postgrest", lambda builder: (_ for _ in ()).throw(Exception("fail")))
    client = SimpleNamespace(table=lambda name: SimpleNamespace(select=lambda *a, **k: "builder"))

    assert db_client._health_check_once(client) is False


def test_is_supabase_online_threshold(monkeypatch):
    now = time.time()
    monkeypatch.setattr(db_client, "_IS_ONLINE", True)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now)
    assert db_client.is_supabase_online() is True

    monkeypatch.setattr(
        db_client, "_LAST_SUCCESS_TIMESTAMP", now - (db_client.supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD + 5)
    )
    assert db_client.is_supabase_online() is False


def test_get_supabase_state_e_cloud_status(monkeypatch):
    # Definir threshold explícito para evitar falhas intermitentes
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_UNSTABLE_THRESHOLD", 60.0)

    monkeypatch.setattr(db_client, "_IS_ONLINE", False)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", 0.0)
    state, desc = db_client.get_supabase_state()
    assert state == "offline"
    text, style, _ = db_client.get_cloud_status_for_ui()
    assert text == "Offline" and style == "danger"

    now = time.time()
    monkeypatch.setattr(db_client, "_IS_ONLINE", True)
    # Usar timestamp bem dentro do threshold (5s atrás, com threshold de 60s)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now - 5.0)
    state, _ = db_client.get_supabase_state()
    assert state == "online"


def test_get_supabase_cria_singleton(monkeypatch):
    # reset singleton
    monkeypatch.setattr(db_client, "_SUPABASE_SINGLETON", None)
    monkeypatch.setattr(db_client, "_SINGLETON_REUSE_LOGGED", False)
    monkeypatch.setenv("SUPABASE_URL", "http://example.com")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setattr(db_client.supa_types, "SUPABASE_URL", "")
    monkeypatch.setattr(db_client.supa_types, "SUPABASE_ANON_KEY", "")

    created = SimpleNamespace()

    def fake_create(url, key, options=None):
        created.url = url
        created.key = key
        created.options = options
        return "CLIENT"

    monkeypatch.setattr(db_client, "create_client", fake_create)
    monkeypatch.setattr(db_client, "_start_health_checker", lambda: None)

    first = db_client.get_supabase()
    second = db_client.get_supabase()

    assert first == "CLIENT" and second == "CLIENT"
    # URL é normalizada com trailing slash
    assert created.url == "http://example.com/"
    assert isinstance(created.options, db_client.ClientOptions)
    assert created.options.httpx_client is db_client.HTTPX_CLIENT
    assert created.options.postgrest_client_timeout == db_client.HTTPX_TIMEOUT_LIGHT


def test_exec_postgrest_usa_retry_call(monkeypatch):
    builder = SimpleNamespace()
    builder.execute = MagicMock(return_value="ok")
    recorded = {}

    def fake_retry(fn, tries, backoff, jitter):
        recorded["args"] = (fn, tries, backoff, jitter)
        return fn()

    monkeypatch.setattr(db_client, "retry_call", fake_retry)

    result = db_client.exec_postgrest(builder)

    assert result == "ok"
    fn, tries, backoff, jitter = recorded["args"]
    assert tries == 3 and backoff == 0.7 and jitter == 0.3
    assert fn is builder.execute
