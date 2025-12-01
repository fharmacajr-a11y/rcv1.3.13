from __future__ import annotations

import types

import httpx
import pytest

from src.core.db_manager import db_manager


class DummyResponse:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class DummyTable:
    def __init__(self, name: str):
        self.name = name
        self.action = "select"
        self.payload = None
        self.filters = []
        self.ordering = None

    @property
    def not_(self):
        return self

    def select(self, *args, **kwargs):
        self.action = "select"
        return self

    def is_(self, *args, **kwargs):
        self.filters.append(("is", args))
        return self

    def eq(self, *args, **kwargs):
        self.filters.append(("eq", args))
        return self

    def order(self, *args, **kwargs):
        self.ordering = args
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def delete(self):
        self.action = "delete"
        return self

    def in_(self, *args, **kwargs):
        self.filters.append(("in", args))
        return self


def stub_supabase(monkeypatch, exec_fn):
    def table(name: str):
        return DummyTable(name)

    monkeypatch.setattr(db_manager, "supabase", types.SimpleNamespace(table=table))
    monkeypatch.setattr(db_manager, "exec_postgrest", exec_fn)


def test_resolve_order_defaults_and_override():
    assert db_manager._resolve_order(None, None) == ("id", True)
    assert db_manager._resolve_order("nome", True) == ("nome", True)
    assert db_manager._resolve_order("unknown", False) == ("id", False)


def test_to_cliente_maps_fields():
    row = {"id": 1, "nome": "Foo", "razao_social": "RS"}
    c = db_manager._to_cliente(row)
    assert c.id == 1
    assert c.nome == "Foo"
    assert c.razao_social == "RS"


def test_current_user_email_handles_exception(monkeypatch):
    monkeypatch.setattr(db_manager, "get_current_user", lambda: (_ for _ in ()).throw(RuntimeError("no user")))
    assert db_manager._current_user_email() == ""


def test_current_user_email_trims(monkeypatch):
    monkeypatch.setattr(db_manager, "get_current_user", lambda: types.SimpleNamespace(email=" user@example.com "))
    assert db_manager._current_user_email() == "user@example.com"


def test_with_retries_retries_on_httpx(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(db_manager.time, "sleep", lambda _: None)

    def fn():
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.ConnectError("fail", request=None)
        return "ok"

    assert db_manager._with_retries(fn, tries=3, base_delay=0) == "ok"
    assert calls["n"] == 2


def test_with_retries_propagates_other_errors(monkeypatch):
    monkeypatch.setattr(db_manager.time, "sleep", lambda _: None)

    def fn():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        db_manager._with_retries(fn, tries=2, base_delay=0)


def test_list_clientes_by_org_requires_id():
    with pytest.raises(ValueError):
        db_manager.list_clientes_by_org(None)  # type: ignore[arg-type]


def test_list_clientes_by_org_returns_rows(monkeypatch):
    stub_supabase(monkeypatch, lambda query: DummyResponse(data=[{"id": 1, "nome": "A"}]))
    res = db_manager.list_clientes_by_org("org1", order_by="nome", descending=False)
    assert len(res) == 1
    assert res[0].nome == "A"


def test_get_cliente_and_get_cliente_by_id(monkeypatch):
    stub_supabase(monkeypatch, lambda query: DummyResponse(data=[{"id": 5, "nome": "X"}]))
    c1 = db_manager.get_cliente(5)
    c2 = db_manager.get_cliente_by_id(5)
    assert c1.id == 5
    assert c2.id == 5


def test_get_cliente_returns_none(monkeypatch):
    stub_supabase(monkeypatch, lambda query: DummyResponse(data=[]))
    assert db_manager.get_cliente(1) is None
    assert db_manager.get_cliente_by_id(1) is None


def test_find_cliente_by_cnpj_norm_empty(monkeypatch):
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "")
    monkeypatch.setattr(db_manager, "exec_postgrest", lambda q: (_ for _ in ()).throw(RuntimeError("should not call")))
    assert db_manager.find_cliente_by_cnpj_norm("   ") is None


def test_find_cliente_by_cnpj_norm_returns_row(monkeypatch):
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "123")
    stub_supabase(monkeypatch, lambda query: DummyResponse(data=[{"id": 9, "cnpj_norm": "123"}]))
    c = db_manager.find_cliente_by_cnpj_norm("123")
    assert c.id == 9


def test_insert_cliente_returns_id_from_response(monkeypatch):
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "u@test")
    monkeypatch.setattr(db_manager, "_with_retries", lambda fn, tries=3, base_delay=db_manager.RETRY_BASE_DELAY: fn())
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "norm")

    def exec_fn(query):
        return DummyResponse(data=[{"id": 7}])

    stub_supabase(monkeypatch, exec_fn)
    new_id = db_manager.insert_cliente("n", "nome", "rs", "cnpj", "obs")
    assert new_id == 7


def test_insert_cliente_fallback_removes_ultima_por(monkeypatch):
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "u@test")
    monkeypatch.setattr(db_manager, "_with_retries", lambda fn, tries=3, base_delay=db_manager.RETRY_BASE_DELAY: fn())
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "norm")
    calls = {"insert": 0, "fallback": 0}

    def exec_fn(query):
        if query.action == "insert":
            calls["insert"] += 1
            if calls["insert"] == 1 and query.payload and query.payload.get("ultima_por"):
                raise RuntimeError("fail with ultima_por")
            return DummyResponse()
        calls["fallback"] += 1
        return DummyResponse(data=[{"id": 11}])

    stub_supabase(monkeypatch, exec_fn)
    assert db_manager.insert_cliente("n", "nome", "rs", "cnpj", "obs") == 11
    assert calls["insert"] == 2
    assert calls["fallback"] == 1


def test_update_cliente_uses_count(monkeypatch):
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "u@test")
    monkeypatch.setattr(db_manager, "_with_retries", lambda fn, tries=3, base_delay=db_manager.RETRY_BASE_DELAY: fn())

    def exec_fn(query):
        return DummyResponse(count=2)

    stub_supabase(monkeypatch, exec_fn)
    assert db_manager.update_cliente(1, "n", "nome", "rs", "c", "obs") == 2


def test_update_status_only_fallback(monkeypatch):
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "user")
    monkeypatch.setattr(db_manager, "_with_retries", lambda fn, tries=3, base_delay=db_manager.RETRY_BASE_DELAY: fn())
    calls = {"update": 0}

    def exec_fn(query):
        calls["update"] += 1
        if calls["update"] == 1 and query.payload and query.payload.get("ultima_por"):
            raise RuntimeError("boom")
        return DummyResponse(count=None, data=[1, 2])

    stub_supabase(monkeypatch, exec_fn)
    assert db_manager.update_status_only(5, "ok") == 2  # len(data)
    assert calls["update"] == 2


def test_delete_and_purge_and_restore(monkeypatch):
    def exec_fn(query):
        if query.action == "delete":
            return DummyResponse(count=None, data=[1])
        if query.action == "update":
            return DummyResponse(count=None, data=[{"id": 1}, {"id": 2}])
        return DummyResponse(count=None, data=[])

    stub_supabase(monkeypatch, exec_fn)
    assert db_manager.delete_cliente(1) == 1
    assert db_manager.purge_clientes([1, 2]) == 1
    assert db_manager.restore_clientes([1, 2]) == 2


def test_soft_delete_handles_empty_and_fallback(monkeypatch):
    assert db_manager.soft_delete_clientes([]) == 0

    calls = {"update": 0}

    def exec_fn(query):
        calls["update"] += 1
        if calls["update"] == 1:
            raise RuntimeError("err")
        return DummyResponse(count=None, data=[{"id": 1}, {"id": 2}, {"id": 3}])

    stub_supabase(monkeypatch, exec_fn)
    assert db_manager.soft_delete_clientes([1, 2, 3]) == 3
    assert calls["update"] == 2


# ============================================================================
# Testes adicionais para aumentar cobertura
# ============================================================================


def test_with_retries_exhausts_and_raises(monkeypatch):
    """Testa que _with_retries levanta exceção após esgotar tentativas."""
    monkeypatch.setattr(db_manager.time, "sleep", lambda _: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise httpx.ReadError("persistent fail", request=None)

    with pytest.raises(httpx.ReadError):
        db_manager._with_retries(fn, tries=2, base_delay=0)
    assert calls["n"] == 2


def test_with_retries_handles_502_error(monkeypatch):
    """Testa retry em erros 502/Bad Gateway."""
    monkeypatch.setattr(db_manager.time, "sleep", lambda _: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 2:
            raise Exception("502 bad gateway")
        return "success"

    result = db_manager._with_retries(fn, tries=3, base_delay=0)
    assert result == "success"
    assert calls["n"] == 2


def test_with_retries_handles_503_error(monkeypatch):
    """Testa retry em erros 503/Service Unavailable."""
    monkeypatch.setattr(db_manager.time, "sleep", lambda _: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 2:
            raise Exception("503 Service Unavailable")
        return "ok"

    result = db_manager._with_retries(fn, tries=3, base_delay=0)
    assert result == "ok"


def test_with_retries_handles_5xx_generic(monkeypatch):
    """Testa retry em erros 5xx genéricos."""
    monkeypatch.setattr(db_manager.time, "sleep", lambda _: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise Exception("5xx server error")
        return "recovered"

    result = db_manager._with_retries(fn, tries=2, base_delay=0)
    assert result == "recovered"


def test_list_clientes_returns_active_only(monkeypatch):
    """Testa que list_clientes retorna apenas clientes ativos."""
    stub_supabase(
        monkeypatch,
        lambda query: DummyResponse(data=[{"id": 1, "nome": "Active"}, {"id": 2, "nome": "Also Active"}]),
    )
    result = db_manager.list_clientes(order_by="id", descending=True)
    assert len(result) == 2
    assert result[0].nome == "Active"


def test_list_clientes_with_default_ordering(monkeypatch):
    """Testa list_clientes com ordenação padrão."""
    stub_supabase(monkeypatch, lambda query: DummyResponse(data=[{"id": 5, "nome": "Test"}]))
    result = db_manager.list_clientes()
    assert len(result) == 1
    assert result[0].id == 5


def test_list_clientes_deletados_returns_deleted(monkeypatch):
    """Testa que list_clientes_deletados retorna apenas clientes deletados."""
    stub_supabase(
        monkeypatch, lambda query: DummyResponse(data=[{"id": 3, "nome": "Deleted", "deleted_at": "2025-01-01"}])
    )
    result = db_manager.list_clientes_deletados(order_by="nome", descending=False)
    assert len(result) == 1
    assert result[0].id == 3


def test_list_clientes_deletados_with_custom_order(monkeypatch):
    """Testa list_clientes_deletados com ordenação customizada."""
    stub_supabase(
        monkeypatch,
        lambda query: DummyResponse(data=[{"id": 10, "nome": "Del1"}, {"id": 11, "nome": "Del2"}]),
    )
    result = db_manager.list_clientes_deletados(order_by="ultima_alteracao", descending=True)
    assert len(result) == 2


def test_find_cliente_by_cnpj_norm_with_exclude_id(monkeypatch):
    """Testa find_cliente_by_cnpj_norm com exclude_id."""
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "normalized123")

    # Mock para DummyTable com suporte a neq
    class ExtendedDummyTable(DummyTable):
        def neq(self, *args, **kwargs):
            self.filters.append(("neq", args))
            return self

    def table(name: str):
        return ExtendedDummyTable(name)

    monkeypatch.setattr(db_manager, "supabase", types.SimpleNamespace(table=table))
    monkeypatch.setattr(
        db_manager, "exec_postgrest", lambda query: DummyResponse(data=[{"id": 99, "cnpj_norm": "normalized123"}])
    )

    result = db_manager.find_cliente_by_cnpj_norm("12345678000199", exclude_id=50)
    assert result is not None
    assert result.id == 99


def test_find_cliente_by_cnpj_norm_no_match(monkeypatch):
    """Testa find_cliente_by_cnpj_norm quando não encontra nenhum registro."""
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "norm456")
    stub_supabase(monkeypatch, lambda query: DummyResponse(data=[]))
    result = db_manager.find_cliente_by_cnpj_norm("98765432000188")
    assert result is None


def test_insert_cliente_fails_to_extract_id_from_response(monkeypatch):
    """Testa insert_cliente quando falha ao extrair ID da resposta."""
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "test@example.com")
    monkeypatch.setattr(db_manager, "_with_retries", lambda fn, tries=3, base_delay=db_manager.RETRY_BASE_DELAY: fn())
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "norm789")

    calls = {"insert": 0, "fallback": 0}

    def exec_fn(query):
        if query.action == "insert":
            calls["insert"] += 1
            # Retorna resposta sem id válido
            return DummyResponse(data=[{"no_id_field": "value"}])
        # Fallback query
        calls["fallback"] += 1
        return DummyResponse(data=[{"id": 42}])

    stub_supabase(monkeypatch, exec_fn)
    new_id = db_manager.insert_cliente("NUM001", "Cliente Teste", "Razão Social Teste", "12345678000199", "Observação")
    assert new_id == 42
    assert calls["insert"] == 1
    assert calls["fallback"] == 1


def test_insert_cliente_fallback_fails_raises_error(monkeypatch):
    """Testa insert_cliente quando tanto insert quanto fallback falham."""
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "user@test.com")
    monkeypatch.setattr(db_manager, "_with_retries", lambda fn, tries=3, base_delay=db_manager.RETRY_BASE_DELAY: fn())
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "norm")

    def exec_fn(query):
        if query.action == "insert":
            return DummyResponse(data=[{}])  # sem id
        # Fallback também falha
        return DummyResponse(data=[])

    stub_supabase(monkeypatch, exec_fn)

    with pytest.raises(RuntimeError, match="Falha ao obter ID do cliente inserido"):
        db_manager.insert_cliente("N", "Nome", "RS", "CNPJ", "Obs")


def test_insert_cliente_with_retries_fails(monkeypatch):
    """Testa insert_cliente quando _with_retries falha após todas tentativas."""
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "user@fail.com")
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "norm")

    def failing_retries(fn, tries=3, base_delay=0):
        raise httpx.ConnectError("Connection failed", request=None)

    monkeypatch.setattr(db_manager, "_with_retries", failing_retries)

    with pytest.raises(httpx.ConnectError):
        db_manager.insert_cliente("N", "Nome", "RS", "CNPJ", "Obs")


def test_update_cliente_fallback_without_count(monkeypatch):
    """Testa update_cliente quando response não tem count."""
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "user@update.com")
    monkeypatch.setattr(db_manager, "_with_retries", lambda fn, tries=3, base_delay=db_manager.RETRY_BASE_DELAY: fn())
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "updated_norm")

    def exec_fn(query):
        return DummyResponse(count=None, data=[{"id": 1}, {"id": 2}])

    stub_supabase(monkeypatch, exec_fn)
    affected = db_manager.update_cliente(1, "NUM", "Nome Updated", "RS Updated", "CNPJ", "Obs Updated")
    assert affected == 2


def test_update_cliente_with_retries_fails(monkeypatch):
    """Testa update_cliente quando _with_retries falha."""
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "user@fail.com")
    monkeypatch.setattr(db_manager, "normalize_cnpj_norm", lambda c: "norm")

    def failing_retries(fn, tries=3, base_delay=0):
        raise httpx.WriteError("Write failed", request=None)

    monkeypatch.setattr(db_manager, "_with_retries", failing_retries)

    with pytest.raises(httpx.WriteError):
        db_manager.update_cliente(1, "N", "Nome", "RS", "CNPJ", "Obs")


def test_update_status_only_with_count(monkeypatch):
    """Testa update_status_only quando response tem count."""
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "status@user.com")
    monkeypatch.setattr(db_manager, "_with_retries", lambda fn, tries=3, base_delay=db_manager.RETRY_BASE_DELAY: fn())

    def exec_fn(query):
        return DummyResponse(count=1, data=[{"id": 5}])

    stub_supabase(monkeypatch, exec_fn)
    affected = db_manager.update_status_only(5, "Status atualizado")
    assert affected == 1


def test_update_status_only_with_retries_fails(monkeypatch):
    """Testa update_status_only quando _with_retries falha."""
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "user@test.com")

    def failing_retries(fn, tries=3, base_delay=0):
        raise OSError("OS error")

    monkeypatch.setattr(db_manager, "_with_retries", failing_retries)

    with pytest.raises(OSError):
        db_manager.update_status_only(1, "Obs")


def test_delete_cliente_with_count(monkeypatch):
    """Testa delete_cliente quando response tem count."""
    stub_supabase(monkeypatch, lambda query: DummyResponse(count=1))
    affected = db_manager.delete_cliente(10)
    assert affected == 1


def test_purge_clientes_empty_list(monkeypatch):
    """Testa purge_clientes com lista vazia."""
    assert db_manager.purge_clientes([]) == 0


def test_purge_clientes_with_count(monkeypatch):
    """Testa purge_clientes quando response tem count."""
    stub_supabase(monkeypatch, lambda query: DummyResponse(count=3))
    affected = db_manager.purge_clientes([1, 2, 3])
    assert affected == 3


def test_restore_clientes_empty_list(monkeypatch):
    """Testa restore_clientes com lista vazia."""
    assert db_manager.restore_clientes([]) == 0


def test_restore_clientes_with_count(monkeypatch):
    """Testa restore_clientes quando response tem count."""
    stub_supabase(monkeypatch, lambda query: DummyResponse(count=2))
    affected = db_manager.restore_clientes([5, 6])
    assert affected == 2


def test_soft_delete_clientes_with_count(monkeypatch):
    """Testa soft_delete_clientes quando response tem count."""
    monkeypatch.setattr(db_manager, "_current_user_email", lambda: "del@user.com")
    stub_supabase(monkeypatch, lambda query: DummyResponse(count=4))
    affected = db_manager.soft_delete_clientes([1, 2, 3, 4])
    assert affected == 4


def test_init_db_with_rc_no_local_fs(monkeypatch):
    """Testa init_db com RC_NO_LOCAL_FS=1."""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
    db_manager.init_db()  # Não deve lançar exceção


def test_init_db_without_rc_no_local_fs(monkeypatch):
    """Testa init_db sem RC_NO_LOCAL_FS."""
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)
    db_manager.init_db()  # Não deve lançar exceção


def test_init_or_upgrade_does_nothing():
    """Testa que init_or_upgrade não faz nada no modo Supabase."""
    db_manager.init_or_upgrade()  # Não deve lançar exceção


def test_now_iso_returns_valid_timestamp():
    """Testa que _now_iso retorna timestamp ISO válido."""
    result = db_manager._now_iso()
    assert isinstance(result, str)
    assert "T" in result  # Formato ISO inclui T entre data e hora
