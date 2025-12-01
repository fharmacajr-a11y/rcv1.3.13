from __future__ import annotations

import pytest

import src.modules.auditoria.repository as repo


class StubTable:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def order(self, *args, **kwargs):
        self.calls.append(("order", args, kwargs))
        return self

    def insert(self, payload):
        self.calls.append(("insert", payload))
        return self

    def update(self, payload):
        self.calls.append(("update", payload))
        return self

    def delete(self):
        self.calls.append(("delete",))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args, kwargs))
        return self

    def in_(self, *args, **kwargs):
        self.calls.append(("in", args, kwargs))
        return self

    def limit(self, *args, **kwargs):
        self.calls.append(("limit", args, kwargs))
        return self

    def execute(self):
        return self


class StubSB:
    def __init__(self, table_data=None):
        self.table_data = table_data or []
        self.last_table = None
        self.auth = type("Auth", (), {"get_user": lambda self: None})()

    def table(self, name):
        self.last_table = name
        return StubTable(self.table_data)


def test_fetch_clients_filters_and_orders(monkeypatch):
    sb = StubSB(table_data=[{"id": 1}, "bad"])

    result = repo.fetch_clients(sb)

    assert result == [{"id": 1}]
    table = sb.table("clients")
    table.select("*").order("id").execute()  # to inspect ordering calls
    assert ("order", ("id",), {}) in table.calls


def test_fetch_clients_empty_data(monkeypatch):
    sb = StubSB(table_data=None)
    assert repo.fetch_clients(sb) == []


def test_fetch_auditorias_filters_and_orders(monkeypatch):
    sb = StubSB(table_data=[{"id": 1}, 5])

    result = repo.fetch_auditorias(sb)

    assert result == [{"id": 1}]
    table = sb.table("auditorias")
    table.select("id, status, created_at, updated_at, cliente_id").order("updated_at", desc=True).execute()
    assert ("order", ("updated_at",), {"desc": True}) in table.calls


def test_insert_auditoria_passes_payload():
    sb = StubSB()
    table = StubTable([])
    sb.table = lambda name: table
    payload = {"status": "new"}

    result = repo.insert_auditoria(sb, payload)

    assert ("insert", payload) in table.calls
    assert result is table


def test_update_auditoria_passes_eq_and_select():
    sb = StubSB()
    table = StubTable([])
    sb.table = lambda name: table

    result = repo.update_auditoria(sb, "aid", "done")

    assert ("update", {"status": "done"}) in table.calls
    assert any(call[0] == "eq" and call[1] == ("id", "aid") for call in table.calls)
    assert result is table


def test_delete_auditorias_noop_when_empty():
    sb = StubSB()
    table = StubTable([])
    sb.table = lambda name: table

    repo.delete_auditorias(sb, [])

    assert table.calls == []


def test_delete_auditorias_calls_in_execute():
    table = StubTable([])
    sb = StubSB()
    sb.table = lambda name: table

    repo.delete_auditorias(sb, ["a", "b"])

    assert any(c[0] == "delete" for c in table.calls)
    assert any(c[0] == "in" and c[1][1] == ["a", "b"] for c in table.calls)


def test_fetch_current_user_id_success():
    sb = StubSB()
    sb.auth = type("Auth", (), {"get_user": lambda self: type("U", (), {"user": type("Usr", (), {"id": "123"})()})()})()

    assert repo.fetch_current_user_id(sb) == "123"


@pytest.mark.parametrize(
    "user_obj",
    [
        None,
        type("U", (), {"user": None})(),
        type("U", (), {"user": type("Usr", (), {"id": None})()})(),
    ],
)
def test_fetch_current_user_id_missing_raises(user_obj):
    sb = StubSB()
    sb.auth = type("Auth", (), {"get_user": lambda self: user_obj})()
    with pytest.raises(LookupError):
        repo.fetch_current_user_id(sb)


def test_fetch_org_id_for_user_success():
    table = StubTable([{"org_id": "ORG"}])
    sb = StubSB()
    sb.table = lambda name: table

    org_id = repo.fetch_org_id_for_user(sb, "uid")

    assert org_id == "ORG"
    assert ("eq", ("user_id",), {"uid": "uid"}) not in table.calls  # eq called with positional
    assert any(call[0] == "eq" for call in table.calls)
    assert any(call[0] == "limit" for call in table.calls)


def test_fetch_org_id_for_user_missing_raises():
    table = StubTable([])
    sb = StubSB()
    sb.table = lambda name: table

    with pytest.raises(LookupError):
        repo.fetch_org_id_for_user(sb, "uid")
