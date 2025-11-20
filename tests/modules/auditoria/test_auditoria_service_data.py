from types import SimpleNamespace

import pytest

from src.modules.auditoria import service as auditoria_service


class _ClientsQueryStub:
    def __init__(self, data):
        self._data = data

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


def test_fetch_clients_filters_non_dict_rows(monkeypatch):
    supabase = SimpleNamespace(table=lambda name: _ClientsQueryStub([{"id": 1}, "bad", {"id": 2}]))
    monkeypatch.setattr(auditoria_service, "_require_supabase", lambda: supabase)

    result = auditoria_service.fetch_clients()

    assert result == [{"id": 1}, {"id": 2}]


def test_fetch_auditorias_returns_rows_sorted(monkeypatch):
    query = _ClientsQueryStub(
        [
            {"id": "a1", "updated_at": "2024-01-02"},
            {"id": "a2", "updated_at": "2024-01-03"},
        ]
    )

    class Supabase:
        def table(self, name):  # noqa: D401 - simple stub
            assert name == "auditorias"
            return query

    monkeypatch.setattr(auditoria_service, "_require_supabase", Supabase)

    assert auditoria_service.fetch_auditorias() == query._data


def test_start_auditoria_inserts_with_payload(monkeypatch):
    class AuditoriasTable:
        def __init__(self):
            self.payload = None

        def insert(self, payload):
            self.payload = payload
            return self

        def execute(self):
            return SimpleNamespace(data=[{"id": "new", "status": "pendente"}])

    table = AuditoriasTable()

    class Supabase:
        def table(self, name):
            assert name == "auditorias"
            return table

    monkeypatch.setattr(auditoria_service, "_require_supabase", Supabase)

    result = auditoria_service.start_auditoria(123, status="pendente")

    assert table.payload == {"cliente_id": 123, "status": "pendente"}
    assert result["id"] == "new"


def test_start_auditoria_raises_when_supabase_returns_empty(monkeypatch):
    class EmptyTable:
        def insert(self, _payload):
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    monkeypatch.setattr(
        auditoria_service,
        "_require_supabase",
        lambda: SimpleNamespace(table=lambda name: EmptyTable()),
    )

    with pytest.raises(auditoria_service.AuditoriaServiceError):
        auditoria_service.start_auditoria(99)


def test_update_auditoria_status_updates_selected_id(monkeypatch):
    class UpdateTable:
        def __init__(self):
            self.updated_payload = None
            self.target_id = None

        def update(self, payload):
            self.updated_payload = payload
            return self

        def eq(self, column, value):
            if column == "id":
                self.target_id = value
            return self

        def select(self, *_args, **_kwargs):
            return self

        def execute(self):
            return SimpleNamespace(data=[{"status": "finalizado"}])

    table = UpdateTable()

    class Supabase:
        def table(self, name):
            assert name == "auditorias"
            return table

    monkeypatch.setattr(auditoria_service, "_require_supabase", Supabase)

    result = auditoria_service.update_auditoria_status("aud-1", "finalizado")

    assert table.updated_payload == {"status": "finalizado"}
    assert table.target_id == "aud-1"
    assert result["status"] == "finalizado"


def test_delete_auditorias_filters_ids_and_calls_supabase(monkeypatch):
    class DeleteTable:
        def __init__(self):
            self.received_ids = None

        def delete(self):
            return self

        def in_(self, column, values):
            assert column == "id"
            self.received_ids = values
            return self

        def execute(self):
            return SimpleNamespace()

    table = DeleteTable()

    class Supabase:
        def table(self, name):
            assert name == "auditorias"
            return table

    monkeypatch.setattr(auditoria_service, "_require_supabase", Supabase)

    auditoria_service.delete_auditorias(["", None, "  ", "123", 456])

    assert table.received_ids == ["123", "456"]


def test_delete_auditorias_skips_when_no_valid_ids(monkeypatch):
    def fail_require():
        raise AssertionError("Supabase should not be required when there are no ids")

    monkeypatch.setattr(auditoria_service, "_require_supabase", fail_require)

    auditoria_service.delete_auditorias([None, "  "])
