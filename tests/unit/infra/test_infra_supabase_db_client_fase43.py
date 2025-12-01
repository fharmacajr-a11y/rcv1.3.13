# tests/test_infra_supabase_db_client_fase43.py
"""
Testes para infra/supabase/db_client.py (COV-INFRA-SUPABASE-DB).
Cobrem singleton, health check, estados e exec_postgrest.
"""

from __future__ import annotations

import importlib
import itertools
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def db_client(monkeypatch):
    """Isola import com stubs para dependencias externas."""
    supa_types = ModuleType("infra.supabase.types")
    supa_types.SUPABASE_URL = "https://stub.supabase.co"
    supa_types.SUPABASE_ANON_KEY = "anon"
    supa_types.HEALTHCHECK_USE_RPC = True
    supa_types.HEALTHCHECK_RPC_NAME = "ping"
    supa_types.HEALTHCHECK_FALLBACK_TABLE = "profiles"
    supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD = 5.0
    supa_types.HEALTHCHECK_INTERVAL_SECONDS = 0.01
    supa_types.HEALTHCHECK_DISABLED = False
    monkeypatch.setitem(sys.modules, "infra.supabase.types", supa_types)

    http_client = ModuleType("infra.supabase.http_client")
    http_client.HTTPX_CLIENT = "httpx-client"
    http_client.HTTPX_TIMEOUT_LIGHT = 1.0
    monkeypatch.setitem(sys.modules, "infra.supabase.http_client", http_client)

    http_retry = ModuleType("infra.http.retry")

    def fake_retry(fn, tries, backoff, jitter):
        return fn()

    http_retry.retry_call = fake_retry
    monkeypatch.setitem(sys.modules, "infra.http.retry", http_retry)
    monkeypatch.setitem(sys.modules, "infra.http", ModuleType("infra.http"))

    supabase_mod = ModuleType("supabase")

    class ClientOptions:
        def __init__(self, **kwargs):
            self.httpx_client = kwargs.get("httpx_client")
            self.postgrest_client_timeout = kwargs.get("postgrest_client_timeout")

    def create_client(url, key, options=None):
        return SimpleNamespace(url=url, key=key, options=options, storage=SimpleNamespace())

    supabase_mod.ClientOptions = ClientOptions
    supabase_mod.Client = SimpleNamespace  # type: ignore[assignment]
    supabase_mod.create_client = create_client
    monkeypatch.setitem(sys.modules, "supabase", supabase_mod)

    sys.modules.pop("infra.supabase.db_client", None)
    module = importlib.import_module("infra.supabase.db_client")
    module._SUPABASE_SINGLETON = None
    module._SINGLETON_REUSE_LOGGED = False
    module._IS_ONLINE = False
    module._LAST_SUCCESS_TIMESTAMP = 0.0
    module._HEALTH_CHECKER_STARTED = False
    return module


def test_exec_postgrest_uses_retry(db_client, monkeypatch):
    calls = {}

    def fake_retry(fn, tries, backoff, jitter):
        calls["args"] = (tries, backoff, jitter)
        return fn()

    monkeypatch.setattr(db_client, "retry_call", fake_retry)
    builder = MagicMock()
    builder.execute.return_value = "ok"

    result = db_client.exec_postgrest(builder)

    assert result == "ok"
    assert calls["args"] == (3, 0.7, 0.3)
    builder.execute.assert_called_once()


def test_health_check_rpc_success(db_client, monkeypatch):
    resp = SimpleNamespace(data="ok")
    monkeypatch.setattr(db_client, "exec_postgrest", lambda rb: resp)
    client = SimpleNamespace(rpc=lambda _: SimpleNamespace())

    ok = db_client._health_check_once(client)

    assert ok is True


def test_health_check_rpc_404_fallback_http(db_client, monkeypatch):
    db_client.supa_types.HEALTHCHECK_USE_RPC = True

    class FakeRPC:
        def __call__(self, _):
            raise Exception("404 not found")

    http_called = {}

    class FakeHTTPResp:
        status_code = 200

        def json(self):
            return {"name": "GoTrue"}

    def fake_http_get(url, timeout):
        http_called["url"] = url
        return FakeHTTPResp()

    monkeypatch.setattr(db_client, "exec_postgrest", MagicMock())
    monkeypatch.setitem(sys.modules, "httpx", ModuleType("httpx"))
    monkeypatch.setattr(sys.modules["httpx"], "get", fake_http_get, raising=False)
    client = SimpleNamespace(rpc=FakeRPC())

    ok = db_client._health_check_once(client)

    assert ok is True
    assert "auth/v1/health" in http_called["url"]


def test_health_check_fallback_table_success(db_client, monkeypatch):
    db_client.supa_types.HEALTHCHECK_USE_RPC = False

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def limit(self, *_):
            return self

    client = SimpleNamespace(table=lambda name: FakeTable())
    monkeypatch.setattr(db_client, "exec_postgrest", lambda rb: SimpleNamespace(data="any"))

    ok = db_client._health_check_once(client)

    assert ok is True


def test_health_check_fallback_table_error(db_client, monkeypatch):
    db_client.supa_types.HEALTHCHECK_USE_RPC = False
    monkeypatch.setattr(db_client, "exec_postgrest", lambda rb: (_ for _ in ()).throw(Exception("net")))

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def limit(self, *_):
            return self

    client = SimpleNamespace(table=lambda name: FakeTable())

    ok = db_client._health_check_once(client)

    assert ok is False


def test_health_check_rpc_error_then_table(db_client, monkeypatch):
    db_client.supa_types.HEALTHCHECK_USE_RPC = True
    table_called = {}

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def limit(self, *_):
            table_called["done"] = True
            return self

    client = SimpleNamespace(rpc=lambda _: (_ for _ in ()).throw(Exception("other")), table=lambda name: FakeTable())
    monkeypatch.setattr(db_client, "exec_postgrest", lambda rb: SimpleNamespace(data="ok"))

    ok = db_client._health_check_once(client)

    assert ok is True
    assert table_called.get("done") is True


def test_health_check_rpc_data_not_ok_uses_table(db_client, monkeypatch):
    db_client.supa_types.HEALTHCHECK_USE_RPC = True
    calls = {"count": 0}

    def exec_pg(builder):
        calls["count"] += 1
        if calls["count"] == 1:
            return SimpleNamespace(data="not-ok")
        return SimpleNamespace(data="from-table")

    db_client.exec_postgrest = exec_pg

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def limit(self, *_):
            return self

    client = SimpleNamespace(rpc=lambda _: SimpleNamespace(), table=lambda name: FakeTable())
    ok = db_client._health_check_once(client)
    assert ok is True
    assert calls["count"] == 2


def test_health_check_http_fallback_then_table(db_client, monkeypatch):
    db_client.supa_types.HEALTHCHECK_USE_RPC = True

    class FakeRPC:
        def __call__(self, _):
            raise Exception("404 fail")

    class BadHTTPResp:
        status_code = 500

        def json(self):
            return {"status": "down"}

    monkeypatch.setitem(sys.modules, "httpx", ModuleType("httpx"))
    monkeypatch.setattr(sys.modules["httpx"], "get", lambda *a, **k: BadHTTPResp(), raising=False)

    table_called = {}

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def limit(self, *_):
            table_called["hit"] = True
            return self

    client = SimpleNamespace(rpc=FakeRPC(), table=lambda name: FakeTable())
    monkeypatch.setattr(db_client, "exec_postgrest", lambda rb: SimpleNamespace(data="ok"))

    ok = db_client._health_check_once(client)

    assert ok is True
    assert table_called.get("hit") is True


def test_health_check_http_fallback_missing_fields(db_client, monkeypatch):
    db_client.supa_types.HEALTHCHECK_USE_RPC = True

    class FakeRPC:
        def __call__(self, _):
            raise Exception("404 fail")

    class EmptyHTTPResp:
        status_code = 200

        def json(self):
            return {}

    monkeypatch.setitem(sys.modules, "httpx", ModuleType("httpx"))
    monkeypatch.setattr(sys.modules["httpx"], "get", lambda *a, **k: EmptyHTTPResp(), raising=False)

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def limit(self, *_):
            return self

    client = SimpleNamespace(rpc=FakeRPC(), table=lambda name: FakeTable())
    monkeypatch.setattr(db_client, "exec_postgrest", lambda rb: SimpleNamespace(data="ok"))

    ok = db_client._health_check_once(client)

    assert ok is True


def test_health_check_http_fallback_exception(db_client, monkeypatch):
    db_client.supa_types.HEALTHCHECK_USE_RPC = True

    class FakeRPC:
        def __call__(self, _):
            raise Exception("404 fail")

    monkeypatch.setitem(sys.modules, "httpx", ModuleType("httpx"))

    def raising_get(*args, **kwargs):
        raise RuntimeError("http fail")

    monkeypatch.setattr(sys.modules["httpx"], "get", raising_get, raising=False)

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def limit(self, *_):
            return self

    client = SimpleNamespace(rpc=FakeRPC(), table=lambda name: FakeTable())
    monkeypatch.setattr(db_client, "exec_postgrest", lambda rb: SimpleNamespace(data="ok"))

    ok = db_client._health_check_once(client)

    assert ok is True


def test_get_supabase_creates_singleton(db_client, monkeypatch):
    created = {}

    def fake_create_client(url, key, options=None):
        created["args"] = (url, key, options)
        return SimpleNamespace(url=url, key=key, options=options)

    monkeypatch.setattr(db_client, "create_client", fake_create_client)
    monkeypatch.setattr(db_client, "_start_health_checker", lambda: None)
    db_client._SUPABASE_SINGLETON = None

    supa = db_client.get_supabase()

    assert supa.url == db_client.supa_types.SUPABASE_URL
    assert supa.key == db_client.supa_types.SUPABASE_ANON_KEY
    assert created["args"][2].httpx_client == db_client.HTTPX_CLIENT
    assert db_client._SUPABASE_SINGLETON is supa


def test_get_supabase_missing_env_raises(db_client, monkeypatch):
    monkeypatch.setattr(db_client.supa_types, "SUPABASE_URL", None)
    monkeypatch.setattr(db_client.supa_types, "SUPABASE_ANON_KEY", None)
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")
    db_client._SUPABASE_SINGLETON = None

    with pytest.raises(RuntimeError):
        db_client.get_supabase()


def test_get_supabase_reuse_logs_once(db_client, monkeypatch):
    supa = SimpleNamespace()
    db_client._SUPABASE_SINGLETON = supa
    db_client._SINGLETON_REUSE_LOGGED = False
    messages = []
    monkeypatch.setattr(db_client.log, "info", lambda msg: messages.append(msg))

    first = db_client.get_supabase()
    second = db_client.get_supabase()

    assert first is supa and second is supa
    assert messages.count("Cliente Supabase reutilizado.") == 1
    assert db_client._SINGLETON_REUSE_LOGGED is True


def test_is_supabase_online_variations(db_client):
    db_client._IS_ONLINE = False
    db_client._LAST_SUCCESS_TIMESTAMP = time.time()
    assert db_client.is_supabase_online() is False

    db_client._IS_ONLINE = True
    db_client._LAST_SUCCESS_TIMESTAMP = time.time() - (db_client.supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD + 1)
    assert db_client.is_supabase_online() is False

    db_client._LAST_SUCCESS_TIMESTAMP = time.time()
    assert db_client.is_supabase_online() is True


def test_is_really_online(db_client):
    db_client._IS_ONLINE = False
    db_client._LAST_SUCCESS_TIMESTAMP = time.time()
    assert db_client.is_really_online() is False

    db_client._IS_ONLINE = True
    db_client._LAST_SUCCESS_TIMESTAMP = time.time()
    assert db_client.is_really_online() is True


def test_get_supabase_state(db_client):
    db_client._IS_ONLINE = False
    state, _ = db_client.get_supabase_state()
    assert state == "offline"

    db_client._IS_ONLINE = True
    db_client._LAST_SUCCESS_TIMESTAMP = time.time() - (db_client.supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD + 1)
    state, _ = db_client.get_supabase_state()
    assert state == "unstable"

    db_client._LAST_SUCCESS_TIMESTAMP = time.time()
    state, _ = db_client.get_supabase_state()
    assert state == "online"


def test_get_cloud_status_for_ui(db_client, monkeypatch):
    monkeypatch.setattr(db_client, "get_supabase_state", lambda: ("online", "desc"))
    assert db_client.get_cloud_status_for_ui()[0] == "Online"

    monkeypatch.setattr(db_client, "get_supabase_state", lambda: ("unstable", "desc"))
    assert db_client.get_cloud_status_for_ui()[0] == "Inst\u00e1vel"

    monkeypatch.setattr(db_client, "get_supabase_state", lambda: ("offline", "desc"))
    assert db_client.get_cloud_status_for_ui()[0] == "Offline"


def test_start_health_checker_runs_once(db_client, monkeypatch):
    db_client._HEALTH_CHECKER_STARTED = False
    db_client.supa_types.HEALTHCHECK_DISABLED = True
    db_client._start_health_checker()
    assert db_client._HEALTH_CHECKER_STARTED is True
    # Segunda chamada deve sair cedo
    db_client._start_health_checker()
    assert db_client._HEALTH_CHECKER_STARTED is True


def test_start_health_checker_online_iteration(db_client, monkeypatch):
    db_client._HEALTH_CHECKER_STARTED = False
    db_client.supa_types.HEALTHCHECK_DISABLED = False
    db_client.supa_types.HEALTHCHECK_INTERVAL_SECONDS = 0.0
    monkeypatch.setattr(db_client, "_health_check_once", lambda client: True)
    monkeypatch.setattr(db_client, "get_supabase", lambda: SimpleNamespace())

    class FakeThread:
        def __init__(self, target, daemon=None, name=None):
            self.target = target

        def start(self):
            # Executa apenas uma vez; time.sleep levantara para sair
            return self.target()

    monkeypatch.setattr(db_client.threading, "Thread", FakeThread)
    monkeypatch.setattr(db_client.time, "sleep", lambda *_: (_ for _ in ()).throw(StopIteration()))

    with pytest.raises(StopIteration):
        db_client._start_health_checker()


def test_start_health_checker_offline_iteration(db_client, monkeypatch):
    db_client._HEALTH_CHECKER_STARTED = False
    db_client.supa_types.HEALTHCHECK_DISABLED = False
    db_client.supa_types.HEALTHCHECK_INTERVAL_SECONDS = 0.0
    monkeypatch.setattr(db_client, "_health_check_once", lambda client: False)
    monkeypatch.setattr(db_client, "get_supabase", lambda: SimpleNamespace())

    class FakeThread:
        def __init__(self, target, daemon=None, name=None):
            self.target = target

        def start(self):
            return self.target()

    monkeypatch.setattr(db_client.threading, "Thread", FakeThread)
    monkeypatch.setattr(db_client.time, "sleep", lambda *_: (_ for _ in ()).throw(StopIteration()))

    with pytest.raises(StopIteration):
        db_client._start_health_checker()


def test_start_health_checker_exception_branch(db_client, monkeypatch):
    db_client._HEALTH_CHECKER_STARTED = False
    db_client.supa_types.HEALTHCHECK_DISABLED = False
    db_client.supa_types.HEALTHCHECK_INTERVAL_SECONDS = 0.0

    def boom(client):
        raise RuntimeError("fail")

    monkeypatch.setattr(db_client, "_health_check_once", boom)
    monkeypatch.setattr(db_client, "get_supabase", lambda: SimpleNamespace())

    class FakeThread:
        def __init__(self, target, daemon=None, name=None):
            self.target = target

        def start(self):
            return self.target()

    times = iter([0.0, 0.0])
    monkeypatch.setattr(db_client.threading, "Thread", FakeThread)
    monkeypatch.setattr(db_client.time, "time", lambda: next(times))
    monkeypatch.setattr(db_client.time, "sleep", lambda *_: (_ for _ in ()).throw(StopIteration()))

    with pytest.raises(StopIteration):
        db_client._start_health_checker()


def test_start_health_checker_unstable_warning(db_client, monkeypatch):
    db_client._HEALTH_CHECKER_STARTED = False
    db_client.supa_types.HEALTHCHECK_DISABLED = False
    db_client.supa_types.HEALTHCHECK_INTERVAL_SECONDS = 0.0
    db_client.supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD = 1.0
    monkeypatch.setattr(db_client, "_health_check_once", lambda client: False)
    monkeypatch.setattr(db_client, "get_supabase", lambda: SimpleNamespace())
    warnings = []
    monkeypatch.setattr(db_client.log, "warning", lambda *a, **k: warnings.append(a[0]))

    class FakeThread:
        def __init__(self, target, daemon=None, name=None):
            self.target = target

        def start(self):
            return self.target()

    base_times = [0.0, 2.0]
    time_seq = itertools.chain(base_times, itertools.repeat(base_times[-1]))
    monkeypatch.setattr(db_client.threading, "Thread", FakeThread)
    monkeypatch.setattr(db_client.time, "time", lambda: next(time_seq))
    sleep_calls = {"n": 0}

    def fake_sleep(*args, **kwargs):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise StopIteration()

    monkeypatch.setattr(db_client.time, "sleep", fake_sleep)

    with pytest.raises(StopIteration):
        db_client._start_health_checker()
    assert any("inst" in msg.lower() for msg in warnings)


def test_start_health_checker_unstable_no_threshold_hit(db_client, monkeypatch):
    db_client._HEALTH_CHECKER_STARTED = False
    db_client.supa_types.HEALTHCHECK_DISABLED = False
    db_client.supa_types.HEALTHCHECK_INTERVAL_SECONDS = 0.0
    db_client.supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD = 5.0
    monkeypatch.setattr(db_client, "_health_check_once", lambda client: False)
    monkeypatch.setattr(db_client, "get_supabase", lambda: SimpleNamespace())

    class FakeThread:
        def __init__(self, target, daemon=None, name=None):
            self.target = target

        def start(self):
            return self.target()

    times = iter([0.0, 0.1])
    sleep_calls = {"n": 0}

    def fake_sleep(*args, **kwargs):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise StopIteration()

    monkeypatch.setattr(db_client.threading, "Thread", FakeThread)
    monkeypatch.setattr(db_client.time, "time", lambda: next(times))
    monkeypatch.setattr(db_client.time, "sleep", fake_sleep)

    with pytest.raises(StopIteration):
        db_client._start_health_checker()


def test_start_health_checker_exception_after_last_bad(db_client, monkeypatch):
    db_client._HEALTH_CHECKER_STARTED = False
    db_client.supa_types.HEALTHCHECK_DISABLED = False
    db_client.supa_types.HEALTHCHECK_INTERVAL_SECONDS = 0.0
    call_count = {"n": 0}

    def health_once(client):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return False  # seta last_bad
        raise RuntimeError("fail later")

    monkeypatch.setattr(db_client, "_health_check_once", health_once)
    monkeypatch.setattr(db_client, "get_supabase", lambda: SimpleNamespace())

    class FakeThread:
        def __init__(self, target, daemon=None, name=None):
            self.target = target

        def start(self):
            return self.target()

    base_times = [0.0, 0.0, 0.0]
    time_seq = itertools.chain(base_times, itertools.repeat(base_times[-1]))
    sleep_count = {"n": 0}

    def fake_sleep(*args, **kwargs):
        sleep_count["n"] += 1
        if sleep_count["n"] >= 2:
            raise StopIteration()

    monkeypatch.setattr(db_client.threading, "Thread", FakeThread)
    monkeypatch.setattr(db_client.time, "time", lambda: next(time_seq))
    monkeypatch.setattr(db_client.time, "sleep", fake_sleep)

    with pytest.raises(StopIteration):
        db_client._start_health_checker()


def test_get_supabase_double_check_branch(db_client, monkeypatch):
    sentinel = SimpleNamespace(name="existing")
    db_client._SUPABASE_SINGLETON = None

    class FakeLock:
        def __enter__(self):
            db_client._SUPABASE_SINGLETON = sentinel

        def __exit__(self, exc_type, exc, tb):
            return False

    db_client._SINGLETON_LOCK = FakeLock()
    result = db_client.get_supabase()
    assert result is sentinel


def test_supabase_lazy_getattr(db_client, monkeypatch):
    target = SimpleNamespace(foo="bar")
    db_client._SUPABASE_SINGLETON = target
    db_client._SINGLETON_REUSE_LOGGED = True
    assert db_client.supabase.foo == "bar"


def test_get_supabase_reuse_without_logging(db_client, monkeypatch):
    supa = SimpleNamespace()
    db_client._SUPABASE_SINGLETON = supa
    db_client._SINGLETON_REUSE_LOGGED = True
    called = []
    monkeypatch.setattr(db_client.log, "info", lambda *a, **k: called.append("log"))

    result = db_client.get_supabase()

    assert result is supa
    assert called == []


def test_get_supabase_reuse_double_check_false(db_client, monkeypatch):
    supa = SimpleNamespace()
    db_client._SUPABASE_SINGLETON = supa
    db_client._SINGLETON_REUSE_LOGGED = False

    class FakeLock:
        def __enter__(self):
            db_client._SINGLETON_REUSE_LOGGED = True

        def __exit__(self, exc_type, exc, tb):
            return False

    db_client._SINGLETON_LOCK = FakeLock()
    called = []
    monkeypatch.setattr(db_client.log, "info", lambda *a, **k: called.append("log"))

    result = db_client.get_supabase()

    assert result is supa
    assert called == []
