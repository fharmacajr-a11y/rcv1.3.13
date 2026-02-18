from __future__ import annotations

import importlib
import types

import pytest

_supabase_available = importlib.util.find_spec("supabase") is not None

pytestmark = [
    pytest.mark.integration,
    pytest.mark.supabase,
    pytest.mark.skipif(not _supabase_available, reason="supabase package not installed"),
]

import src.db.supabase_repo as repo


class DummySession:
    def __init__(self, token):
        self.access_token = token


class DummyAuth:
    def __init__(self, session=None, raise_on_get=False):
        self._session = session
        self._raise_on_get = raise_on_get
        self.sign_in_payloads = []

    def get_session(self):
        if self._raise_on_get:
            raise RuntimeError("boom")
        return self._session

    def sign_in_with_password(self, payload):
        self.sign_in_payloads.append(payload)
        return {"ok": True}


class DummyPostgrest:
    def __init__(self):
        self.tokens = []
        self.raise_on_auth = False

    def auth(self, token):
        if self.raise_on_auth:
            raise RuntimeError("fail auth")
        self.tokens.append(token)


class DummyClient:
    def __init__(self, session=None, raise_on_get=False):
        self.auth = DummyAuth(session=session, raise_on_get=raise_on_get)
        self.postgrest = DummyPostgrest()


def test_get_access_token_success():
    client = DummyClient(session=DummySession("tok"))
    assert repo._get_access_token(client) == "tok"


def test_get_access_token_exception_returns_none():
    client = DummyClient(raise_on_get=True)
    assert repo._get_access_token(client) is None


def test_ensure_postgrest_auth_with_token(monkeypatch):
    client = DummyClient(session=DummySession("tok"))
    repo._ensure_postgrest_auth(client)
    assert client.postgrest.tokens == ["tok"]


def test_ensure_postgrest_auth_without_token_required(monkeypatch):
    client = DummyClient(session=None)
    with pytest.raises(RuntimeError, match="Sess"):
        repo._ensure_postgrest_auth(client, required=True)


def test_ensure_postgrest_auth_without_token_logs(monkeypatch, caplog):
    client = DummyClient(session=None)
    with caplog.at_level("WARNING", logger=repo.log.name):
        repo._ensure_postgrest_auth(client, required=False)
    assert any("sem access_token" in rec.getMessage() for rec in caplog.records)


def test_ensure_postgrest_auth_handles_auth_failure(monkeypatch, caplog):
    client = DummyClient(session=DummySession("tok"))
    client.postgrest.raise_on_auth = True
    with caplog.at_level("WARNING", logger=repo.log.name):
        repo._ensure_postgrest_auth(client)
    assert any("postgrest.auth falhou" in rec.getMessage() for rec in caplog.records)


def test_with_retries_success_and_retry(monkeypatch):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise repo.httpx.ReadError("err")
        return "ok"

    monkeypatch.setattr(repo.time, "sleep", lambda _delay: None)
    result = repo.with_retries(fn, tries=2, base_delay=0.0)

    assert result == "ok"
    assert calls["n"] == 2


def test_with_retries_non_retry_error_propagates(monkeypatch):
    def fn():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        repo.with_retries(fn, tries=2, base_delay=0.0)


def test_with_retries_exhausts_and_raises_last_exception(monkeypatch):
    def fn():
        err = OSError()
        err.errno = 1
        raise err

    monkeypatch.setattr(repo.time, "sleep", lambda _d: None)
    with pytest.raises(OSError):
        repo.with_retries(fn, tries=2, base_delay=0.0)


def test_with_retries_handles_5xx_like_exception(monkeypatch):
    def fn():
        raise RuntimeError("502 gateway")

    with pytest.raises(RuntimeError, match="502"):
        repo.with_retries(fn, tries=1, base_delay=0.0)


def test_with_retries_raises_when_no_attempts(monkeypatch):
    with pytest.raises(RuntimeError, match="Unexpected None error"):
        repo.with_retries(lambda: "ok", tries=0, base_delay=0.0)


def test_list_passwords_success(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)

    # Mock retornando estrutura com JOIN de cliente (como vem do Supabase)
    mock_data = [
        {
            "id": 1,
            "org_id": "ORG",
            "client_name": "Test Client",
            "service": "Test Service",
            "username": "test_user",
            "password_enc": "encrypted",
            "notes": "test notes",
            "created_by": "user1",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "client_id": "client123",
            "clients": {
                "id": "ext123",
                "razao_social": "Test Company",
                "cnpj": "12345678000100",
                "nome": "Contact Name",
                "numero": "11999999999",
            },
        }
    ]

    monkeypatch.setattr(repo, "exec_postgrest", lambda obj: types.SimpleNamespace(data=mock_data))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    data = repo.list_passwords("ORG")

    # Verifica que retornou 1 registro
    assert len(data) == 1

    # Verifica que os campos principais existem e foram achatados corretamente
    result = data[0]
    assert result["id"] == 1
    assert result["client_external_id"] == "ext123"
    assert result["razao_social"] == "Test Company"
    assert result["cnpj"] == "12345678000100"
    assert result["nome"] == "Contact Name"
    assert result["whatsapp"] == "11999999999"
    assert result["service"] == "Test Service"
    assert result["username"] == "test_user"


def test_list_passwords_error(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    monkeypatch.setattr(repo, "with_retries", lambda fn: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="Falha ao listar"):
        repo.list_passwords("ORG")


def test_list_passwords_missing_org_raises():
    with pytest.raises(ValueError):
        repo.list_passwords("")


def test_add_password_success(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c, required=False: None)
    monkeypatch.setattr(repo, "_rls_precheck_membership", lambda _c, _o, _u: None)
    monkeypatch.setattr(repo, "encrypt_text", lambda txt: f"enc-{txt}")
    monkeypatch.setattr(repo, "_now_iso", lambda: "NOW")
    captured = {}

    def fake_exec(obj):
        captured["payload"] = obj._payload  # type: ignore[attr-defined]
        return types.SimpleNamespace(data=[{"id": "new"}])

    class FakeTable:
        def __init__(self):
            self._payload = None

        def insert(self, payload):
            self._payload = payload
            return self

    class FakeSupabase:
        def table(self, _name):
            return FakeTable()

    monkeypatch.setattr(repo, "supabase", FakeSupabase())
    monkeypatch.setattr(repo, "exec_postgrest", fake_exec)
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    result = repo.add_password("ORG", "Client", "Service", "user", "pwd", "notes", "creator")

    assert result["id"] == "new"
    assert captured["payload"]["password_enc"] == "enc-pwd"
    assert captured["payload"]["created_at"] == "NOW"


def test_add_password_no_data_raises(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c, required=False: None)
    monkeypatch.setattr(repo, "_rls_precheck_membership", lambda _c, _o, _u: None)
    monkeypatch.setattr(repo, "encrypt_text", lambda txt: txt)

    class FakeTable:
        def insert(self, payload):
            return self

    class FakeSupabase:
        def table(self, _name):
            return FakeTable()

    monkeypatch.setattr(repo, "supabase", FakeSupabase())
    monkeypatch.setattr(repo, "exec_postgrest", lambda obj: types.SimpleNamespace(data=None))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    with pytest.raises(RuntimeError, match="Insert"):
        repo.add_password("ORG", "Client", "Service", "user", "pwd", "notes", "creator")


def test_add_password_missing_required_fields():
    with pytest.raises(ValueError):
        repo.add_password("", "Client", "Service", "u", "p", "n", "c")


def test_update_password_success(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    monkeypatch.setattr(repo, "encrypt_text", lambda txt: f"enc-{txt}")
    monkeypatch.setattr(repo, "_now_iso", lambda: "NOW")

    class FakeTable:
        def __init__(self):
            self._payload = None
            self._id = None

        def update(self, payload):
            self._payload = payload
            return self

        def eq(self, _field, value):
            self._id = value
            return self

    class FakeSupabase:
        def table(self, _name):
            return FakeTable()

    _fake_table = FakeSupabase().table("client_passwords")
    monkeypatch.setattr(repo, "supabase", FakeSupabase())
    monkeypatch.setattr(repo, "exec_postgrest", lambda obj: types.SimpleNamespace(data=[{"id": obj._id}]))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    result = repo.update_password("ID", client_name="C", password_plain="pwd")

    assert result["id"] == "ID"


def test_update_password_sets_optional_fields(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    monkeypatch.setattr(repo, "encrypt_text", lambda txt: f"enc-{txt}")
    monkeypatch.setattr(repo, "_now_iso", lambda: "NOW")

    class FakeTable:
        def __init__(self):
            self.payload = None
            self._id = None

        def update(self, payload):
            self.payload = payload
            return self

        def eq(self, _field, value):
            self._id = value
            return self

    table = FakeTable()

    class FakeSupabase:
        def table(self, _name):
            return table

    monkeypatch.setattr(repo, "supabase", FakeSupabase())
    monkeypatch.setattr(repo, "exec_postgrest", lambda obj: types.SimpleNamespace(data=[{"id": obj._id}]))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    repo.update_password("ID", service="S", username="U", notes="N")

    assert table.payload["service"] == "S"
    assert table.payload["username"] == "U"
    assert table.payload["notes"] == "N"


def test_update_password_no_data(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)

    class FakeTable:
        def update(self, payload):
            return self

        def eq(self, *_args):
            return self

    class FakeSupabase:
        def table(self, _name):
            return FakeTable()

    monkeypatch.setattr(repo, "supabase", FakeSupabase())
    monkeypatch.setattr(repo, "exec_postgrest", lambda obj: types.SimpleNamespace(data=None))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    with pytest.raises(RuntimeError, match="Update"):
        repo.update_password("ID")


def test_update_password_missing_id():
    with pytest.raises(ValueError):
        repo.update_password("")


def test_delete_password_calls_with_retries(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    called = {"n": 0}

    def fake_with(fn):
        called["n"] += 1
        return fn()

    class FakeTable:
        def delete(self):
            return self

        def eq(self, *_args):
            return self

    class FakeSupabase:
        def table(self, _name):
            return FakeTable()

    monkeypatch.setattr(repo, "supabase", FakeSupabase())
    monkeypatch.setattr(repo, "exec_postgrest", lambda obj: None)
    monkeypatch.setattr(repo, "with_retries", fake_with)

    repo.delete_password("123")
    assert called["n"] == 1


def test_delete_password_error(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    monkeypatch.setattr(repo, "with_retries", lambda fn: (_ for _ in ()).throw(RuntimeError("boom")))

    class FakeTable:
        def delete(self):
            return self

        def eq(self, *_args):
            return self

    monkeypatch.setattr(repo, "supabase", types.SimpleNamespace(table=lambda _n: FakeTable()))
    with pytest.raises(RuntimeError, match="Falha ao excluir"):
        repo.delete_password("123")


def test_delete_password_missing_id():
    with pytest.raises(ValueError):
        repo.delete_password("")


def test_decrypt_for_view_success(monkeypatch):
    monkeypatch.setattr(repo, "decrypt_text", lambda token: f"plain-{token}")
    assert repo.decrypt_for_view("abc") == "plain-abc"


def test_decrypt_for_view_error(monkeypatch):
    monkeypatch.setattr(repo, "decrypt_text", lambda token: (_ for _ in ()).throw(RuntimeError("bad")))
    with pytest.raises(RuntimeError, match="Falha ao descriptografar"):
        repo.decrypt_for_view("abc")


class FakeQuery:
    def __init__(self):
        self.operations = []

    def select(self, *_args, **_kwargs):
        self.operations.append("select")
        return self

    def eq(self, *_args, **_kwargs):
        self.operations.append("eq")
        return self

    def is_(self, *_args, **_kwargs):
        self.operations.append("is")
        return self

    def or_(self, *_args, **_kwargs):
        self.operations.append("or")
        return self

    def order(self, *_args, **_kwargs):
        self.operations.append("order")
        return self

    def limit(self, *_args, **_kwargs):
        self.operations.append("limit")
        return self


def test_search_clients_filters_and_or(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    query_obj = FakeQuery()
    monkeypatch.setattr(repo, "supabase", types.SimpleNamespace(table=lambda _name: query_obj))
    monkeypatch.setattr(repo, "exec_postgrest", lambda _sel: types.SimpleNamespace(data=[{"id": 1}]))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    result = repo.search_clients("ORG", "ab", limit=5)

    assert result == [{"id": 1}]
    assert "or" in query_obj.operations
    assert "limit" in query_obj.operations


def test_search_clients_short_query_no_or(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    query_obj = FakeQuery()
    monkeypatch.setattr(repo, "supabase", types.SimpleNamespace(table=lambda _name: query_obj))
    monkeypatch.setattr(repo, "exec_postgrest", lambda _sel: types.SimpleNamespace(data=[]))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    repo.search_clients("ORG", "a", limit=1)

    assert "or" not in query_obj.operations


def test_search_clients_no_org_returns_empty(monkeypatch):
    assert repo.search_clients("", "anything") == []


def test_search_clients_handles_exception(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    monkeypatch.setattr(repo, "supabase", types.SimpleNamespace(table=lambda _name: FakeQuery()))
    monkeypatch.setattr(repo, "with_retries", lambda fn: (_ for _ in ()).throw(RuntimeError("fail")))

    result = repo.search_clients("ORG", "ab")

    assert result == []


def test_list_clients_for_picker_success(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    query_obj = FakeQuery()
    monkeypatch.setattr(repo, "supabase", types.SimpleNamespace(table=lambda _name: query_obj))
    monkeypatch.setattr(repo, "exec_postgrest", lambda _sel: types.SimpleNamespace(data=[{"id": 1}]))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    result = repo.list_clients_for_picker("ORG", limit=1)

    assert result == [{"id": 1}]
    assert "limit" in query_obj.operations


def test_list_clients_for_picker_no_org(monkeypatch):
    assert repo.list_clients_for_picker("", limit=1) == []


def test_list_clients_for_picker_handles_exception(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c: None)
    monkeypatch.setattr(repo, "supabase", types.SimpleNamespace(table=lambda _name: FakeQuery()))
    monkeypatch.setattr(repo, "with_retries", lambda fn: (_ for _ in ()).throw(RuntimeError("fail")))

    result = repo.list_clients_for_picker("ORG")

    assert result == []


def test_rls_precheck_membership_success(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c, required=True: None)

    class FakeTable:
        def select(self, *_, **__):
            return self

        def eq(self, *_, **__):
            return self

        def limit(self, *_args, **_kwargs):
            return self

    fake_client = types.SimpleNamespace(table=lambda _name: FakeTable())
    monkeypatch.setattr(repo, "exec_postgrest", lambda obj: types.SimpleNamespace(data=[{"user_id": "uid"}]))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())

    repo._rls_precheck_membership(client=fake_client, org_id="ORG", user_id="uid")


def test_rls_precheck_membership_raises(monkeypatch):
    monkeypatch.setattr(repo, "_ensure_postgrest_auth", lambda _c, required=True: None)

    class FakeTable:
        def select(self, *_, **__):
            return self

        def eq(self, *_, **__):
            return self

        def limit(self, *_args, **_kwargs):
            return self

    fake_client = types.SimpleNamespace(table=lambda _name: FakeTable())
    monkeypatch.setattr(repo, "exec_postgrest", lambda obj: types.SimpleNamespace(data=None))
    monkeypatch.setattr(repo, "with_retries", lambda fn: fn())
    with pytest.raises(RuntimeError, match="RLS precheck"):
        repo._rls_precheck_membership(client=fake_client, org_id="ORG", user_id="uid")


def test_import_fallback_for_apierror(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("postgrest"):
            raise ImportError("no module")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    import importlib
    import src.db.supabase_repo as module

    importlib.reload(module)
    assert module.APIError is Exception
