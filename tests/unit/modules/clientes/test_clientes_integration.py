# -*- coding: utf-8 -*-
"""Testes de integração para fluxos completos de clientes.

Atualizado na FASE 28 para refletir a arquitetura atual:
- Pipeline modularizado (_prepare, _upload, _finalize)
- get_supabase_state vem de infra.supabase_client
- Funções de lixeira não usam _get_lixeira_service
- Assinaturas atualizadas (sem parâmetro parent)
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.modules.clientes import service as clientes_service


class EntryStub:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def insert(self, index: int | str, value: str) -> None:  # pragma: no cover - not used here
        self.value = value

    def delete(self, start: int | str, end: int | str | None = None) -> None:
        self.value = ""


class TextStub:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self, start: str, end: str) -> str:
        return self.value

    def insert(self, index: str, value: str) -> None:  # pragma: no cover - not used here
        self.value = value

    def delete(self, start: str, end: str) -> None:  # pragma: no cover - not used here
        self.value = ""


class DummyApp:
    def __init__(self) -> None:
        self.carregar_called = False

    def carregar(self) -> None:
        self.carregar_called = True

    def after(self, _delay: int, callback, *cb_args, **cb_kwargs) -> None:
        callback(*cb_args, **cb_kwargs)


def test_fluxo_lixeira_cliente_move_lista_restaura(monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa fluxo completo de lixeira: mover → listar → restaurar → excluir definitivamente.

    Atualizado na FASE 28:
    - Funções de lixeira não usam _get_lixeira_service
    - restaurar_clientes_da_lixeira e excluir_clientes_definitivamente não aceitam parâmetro parent
    - São chamadas diretas que operam via exec_postgrest
    """
    recorded = {}

    class DummyTableQuery:
        def __init__(self, table_name: str):
            self.table_name = table_name
            self.payload = None
            self.eq_value = None
            self.in_value = None

        def update(self, payload):
            self.payload = payload
            return self

        def eq(self, column, value):
            self.eq_value = (column, value)
            return self

        def in_(self, column, values):
            self.in_value = (column, values)
            return self

        def delete(self):
            return self

        def select(self, *args):
            return self

        def limit(self, n):
            return self

    class DummySupabase:
        def table(self, name: str):
            query = DummyTableQuery(name)
            recorded["query"] = query
            return query

    # Mockar supabase e exec_postgrest onde são USADOS (clientes_service)
    def fake_exec_postgrest(query):
        recorded["query"] = query
        return SimpleNamespace(data=[])

    monkeypatch.setattr(clientes_service, "supabase", DummySupabase())
    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec_postgrest)
    monkeypatch.setattr(clientes_service, "_current_utc_iso", lambda: "2025-01-01T00:00:00Z")

    # Teste 1: mover para lixeira
    clientes_service.mover_cliente_para_lixeira(77)
    query = recorded["query"]
    assert query.table_name == "clients"
    assert query.payload["deleted_at"].startswith("2025-01-01")
    assert query.eq_value == ("id", 77)

    # Teste 2: listar clientes na lixeira
    monkeypatch.setattr(
        clientes_service,
        "_list_clientes_deletados_core",
        lambda **_k: [SimpleNamespace(id=77, razao_social="Cliente 77")],
    )
    registros = clientes_service.listar_clientes_na_lixeira()
    assert registros and registros[0].id == 77

    # Teste 3: restaurar da lixeira (SEM parâmetro parent - API atual)
    # Resetar recorded para capturar a nova query
    recorded.clear()
    clientes_service.restaurar_clientes_da_lixeira([77])
    query = recorded.get("query")
    assert query is not None, "Query de restauração não foi capturada"
    assert query.table_name == "clients"
    assert query.payload["deleted_at"] is None
    assert query.in_value == ("id", [77])

    # Teste 4: excluir definitivamente (SEM parâmetro parent - API atual)
    # Mock para evitar operações de storage reais
    import src.core.db_manager as db_manager_module

    monkeypatch.setattr(
        db_manager_module,
        "get_cliente_by_id",
        lambda cid: SimpleNamespace(id=cid, razao_social=f"Cliente {cid}", numero="001"),
    )

    # Mock de funções de storage que seriam usadas
    import src.adapters.storage.api as storage_api_module

    monkeypatch.setattr(storage_api_module, "list_files", lambda *a, **k: [])
    monkeypatch.setattr(storage_api_module, "delete_file", lambda *a, **k: None)

    # Mockar auth para resolver org_id
    class DummyUser:
        id = "user-123"

    class DummyAuthResponse:
        user = DummyUser()

    class DummyAuth:
        def get_user(self):
            return DummyAuthResponse()

    class DummySupabaseWithAuth:
        auth = DummyAuth()

        def table(self, name: str):
            query = DummyTableQuery(name)
            recorded["query"] = query
            return query

    monkeypatch.setattr(clientes_service, "supabase", DummySupabaseWithAuth())

    # Mockar query de membership para resolver org_id
    def fake_exec_for_org(query):
        # Se for query de memberships, retornar org_id
        if hasattr(query, "table_name") and query.table_name == "memberships":
            return SimpleNamespace(data=[{"org_id": "org-1"}])
        # Para outras queries (delete de clients)
        return SimpleNamespace(data=[])

    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec_for_org)

    # Agora testar exclusão definitiva
    qtd_ok, erros = clientes_service.excluir_clientes_definitivamente([77])
    assert qtd_ok == 1
    assert len(erros) == 0
