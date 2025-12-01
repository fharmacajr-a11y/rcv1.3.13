from __future__ import annotations

import types

import pytest

from src.core.search import search
from src.core.models import Cliente


class DummyUser:
    def __init__(self, org_id):
        self.org_id = org_id


class DummySupabaseTable:
    def __init__(self, rows):
        self.rows = rows
        self.ops = []

    def select(self, *_args):
        self.ops.append("select")
        return self

    def is_(self, *_args):
        self.ops.append("is")
        return self

    def eq(self, *_args):
        self.ops.append("eq")
        return self

    def or_(self, *args):
        self.ops.append(("or", args))
        return self

    def order(self, col, desc=False):
        self.ops.append(("order", col, desc))
        return self


class DummyResp:
    def __init__(self, data):
        self.data = data


def make_cliente(id, nome=None, razao=None, cnpj=None, numero=None, obs=None):
    return Cliente(
        id=id,
        numero=numero,
        nome=nome,
        razao_social=razao,
        cnpj=cnpj,
        cnpj_norm=cnpj,
        ultima_alteracao=None,
        obs=obs,
        ultima_por=None,
        created_at=None,
    )


def test_normalize_order_variants():
    assert search._normalize_order(None) == (None, False)
    assert search._normalize_order("CNPJ") == ("cnpj", False)
    assert search._normalize_order("ultima alteracao") == ("ultima_alteracao", True)
    assert search._normalize_order("unknown") == (None, False)


def test_filter_rows_with_norm_and_cache():
    rows = [{"id": 1, "razao_social": "Alpha", "cnpj": "11"}, {"id": 2, "razao_social": "Beta"}]
    result = search._filter_rows_with_norm(rows, "alp")
    assert [r["id"] for r in result] == [1]
    # second call uses cached _search_norm
    result2 = search._filter_rows_with_norm(rows, "eta")
    assert [r["id"] for r in result2] == [2]


def test_filter_rows_with_norm_empty_term_returns_all():
    rows = [{"id": 1}, {"id": 2}]
    result = search._filter_rows_with_norm(rows, "")
    assert result == rows


def test_filter_clientes_and_blob():
    clientes = [make_cliente(1, nome="Joao"), make_cliente(2, razao="Maria"), make_cliente(3, obs="Test")]
    assert search._cliente_search_blob(clientes[0]) != ""
    filtered = search._filter_clientes(clientes, "jo")
    assert [c.id for c in filtered] == [1]
    # empty term returns all
    assert len(search._filter_clientes(clientes, "")) == 3


def test_search_clientes_supabase_path(monkeypatch):
    table = DummySupabaseTable(rows=[{"id": 1, "nome": "Joao", "razao_social": "Silva"}])
    monkeypatch.setattr(search, "is_supabase_online", lambda: True)
    monkeypatch.setattr(search, "supabase", types.SimpleNamespace(table=lambda name: table))
    monkeypatch.setattr(search, "exec_postgrest", lambda qb: DummyResp(table.rows))
    monkeypatch.setattr(search, "get_current_user", lambda: DummyUser("ORG"))
    result = search.search_clientes("jo", order_by="nome")
    assert [c.id for c in result] == [1]
    assert any(op[0] == "or" for op in table.ops if isinstance(op, tuple))


def test_search_clientes_supabase_no_results_then_fallback(monkeypatch):
    table = DummySupabaseTable(rows=[])
    monkeypatch.setattr(search, "is_supabase_online", lambda: True)
    monkeypatch.setattr(search, "supabase", types.SimpleNamespace(table=lambda name: table))
    monkeypatch.setattr(search, "get_current_user", lambda: DummyUser("ORG"))
    # second fetch returns match
    calls = {"n": 0}

    def fetch(qb):
        calls["n"] += 1
        if calls["n"] == 1:
            return DummyResp([])
        return DummyResp([{"id": 2, "nome": "Ana", "razao_social": ""}])

    monkeypatch.setattr(search, "exec_postgrest", fetch)
    result = search.search_clientes("an", order_by=None)
    assert [c.id for c in result] == [2]


def test_search_clientes_supabase_error_logs_and_fallback(monkeypatch, caplog):
    monkeypatch.setattr(search, "is_supabase_online", lambda: True)
    monkeypatch.setattr(search, "supabase", None)
    monkeypatch.setattr(search, "get_current_user", lambda: DummyUser("ORG"))
    monkeypatch.setattr(search, "exec_postgrest", lambda qb: (_ for _ in ()).throw(RuntimeError("boom")))
    clientes_local = [make_cliente(1, nome="Local"), make_cliente(2, nome="Other")]
    monkeypatch.setattr(
        "src.core.db_manager.db_manager.list_clientes_by_org",
        lambda org_id, order_by=None, descending=None: clientes_local,
    )
    with caplog.at_level("WARNING", logger=search.log.name):
        result = search.search_clientes("loc", order_by=None)
    assert [c.id for c in result] == [1]
    assert any("falha no Supabase" in rec.getMessage() for rec in caplog.records)


def test_search_clientes_offline_raises_without_org(monkeypatch):
    monkeypatch.setattr(search, "is_supabase_online", lambda: False)
    monkeypatch.setattr(search, "get_current_user", lambda: None)
    with pytest.raises(ValueError):
        search.search_clientes("x")


def test_search_clientes_offline_filters_local(monkeypatch):
    clientes_local = [make_cliente(1, nome="Alpha"), make_cliente(2, nome="Beta")]
    monkeypatch.setattr(search, "is_supabase_online", lambda: False)
    monkeypatch.setattr(search, "get_current_user", lambda: DummyUser("ORG"))
    monkeypatch.setattr(
        "src.core.db_manager.db_manager.list_clientes_by_org",
        lambda org_id, order_by=None, descending=None: clientes_local,
    )
    result = search.search_clientes("be", order_by="id", org_id=None)
    assert [c.id for c in result] == [2]


def test_search_clientes_offline_no_term_returns_all(monkeypatch):
    clientes_local = [make_cliente(1, nome="Alpha")]
    monkeypatch.setattr(search, "is_supabase_online", lambda: False)
    monkeypatch.setattr(search, "get_current_user", lambda: DummyUser("ORG"))
    monkeypatch.setattr(
        "src.core.db_manager.db_manager.list_clientes_by_org",
        lambda org_id, order_by=None, descending=None: clientes_local,
    )
    assert search.search_clientes("", org_id=None) == clientes_local


def test_search_clientes_offline_with_org_param(monkeypatch):
    clientes_local = [make_cliente(1, nome="Alpha")]
    monkeypatch.setattr(search, "is_supabase_online", lambda: False)
    monkeypatch.setattr(
        "src.core.db_manager.db_manager.list_clientes_by_org",
        lambda org_id, order_by=None, descending=None: clientes_local,
    )
    assert search.search_clientes("", org_id="ORG") == clientes_local


def test_search_clientes_order_normalization(monkeypatch):
    table = DummySupabaseTable(rows=[{"id": 1, "nome": "Joao"}])
    monkeypatch.setattr(search, "is_supabase_online", lambda: True)
    monkeypatch.setattr(search, "supabase", types.SimpleNamespace(table=lambda name: table))
    monkeypatch.setattr(search, "exec_postgrest", lambda qb: DummyResp(table.rows))
    monkeypatch.setattr(search, "get_current_user", lambda: DummyUser("ORG"))
    result = search.search_clientes("", order_by="ultima_alteracao")
    assert [c.id for c in result] == [1]
    assert ("order", "ultima_alteracao", True) in table.ops


def test_search_clientes_supabase_missing_org_raises(monkeypatch):
    monkeypatch.setattr(search, "is_supabase_online", lambda: True)
    monkeypatch.setattr(search, "supabase", types.SimpleNamespace(table=lambda name: DummySupabaseTable(rows=[])))
    monkeypatch.setattr(search, "get_current_user", lambda: None)
    with pytest.raises(ValueError, match="org_id obrigatorio"):
        search.search_clientes("x", org_id=None)
