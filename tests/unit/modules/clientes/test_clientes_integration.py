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

from src.modules.clientes.forms import pipeline as clientes_pipeline
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


def test_fluxo_salvar_cliente_com_upload_integra_pipeline_e_service(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Testa o fluxo completo: validação → preparação → upload → finalização.

    Este teste foca em verificar que o pipeline completo executa sem erros,
    mockando todas as dependências externas (Supabase, Storage, Auth, etc.).
    """
    app = DummyApp()
    arquivo = tmp_path / "doc1.pdf"
    arquivo.write_bytes(b"arquivo-teste-conteudo")

    ents = {
        "Razão Social": EntryStub("Cliente Teste Integração"),
        "CNPJ": EntryStub("12345678000199"),
        "Nome": EntryStub("Fulano Teste"),
        "WhatsApp": EntryStub("11987654321"),
        "Observações": TextStub("Observação de teste"),
    }
    arquivos = [str(arquivo)]

    # Mock infra.supabase_client - precisa mockar onde é USADO, não onde é definido
    import src.modules.clientes.forms._prepare as prepare_module

    monkeypatch.setattr(
        prepare_module,
        "get_supabase_state",
        lambda: ("online", "Conectado ao Supabase e dentro do limiar de estabilidade."),
    )
    monkeypatch.setattr(prepare_module, "_ask_subpasta", lambda parent: "SUBPASTA")

    # Mock salvar_cliente no módulo onde é importado (_prepare)
    monkeypatch.setattr(
        prepare_module, "salvar_cliente", lambda row, valores: (123, str(tmp_path / "cliente123"))
    )  # Mock db_manager
    import src.core.db_manager as db_manager_module

    monkeypatch.setattr(db_manager_module, "find_cliente_by_cnpj_norm", lambda *a, **k: None)

    # Mock core services
    import src.core.services.clientes_service as core_clientes_service

    monkeypatch.setattr(core_clientes_service, "checar_duplicatas_info", lambda **k: {})

    # Mock auth utils
    import src.helpers.auth_utils as auth_utils_module

    monkeypatch.setattr(auth_utils_module, "current_user_id", lambda: "user-test-123")
    monkeypatch.setattr(auth_utils_module, "resolve_org_id", lambda: "org-test-456")

    # Mock messagebox e filedialog
    from tkinter import messagebox, filedialog

    monkeypatch.setattr(messagebox, "showwarning", lambda *a, **k: None)
    monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(filedialog, "askdirectory", lambda **_k: "")

    # Mock storage operations + UploadProgressDialog - precisa mockar onde é USADO (upload_module)
    import src.modules.clientes.forms._upload as upload_module

    uploads_log = []

    def fake_upload(data: bytes, path: str, content_type: str) -> None:
        uploads_log.append({"path": path, "type": content_type, "size": len(data)})

    monkeypatch.setattr(upload_module, "storage_upload_file", fake_upload)
    monkeypatch.setattr(upload_module, "storage_delete_file", lambda *a, **k: None)

    # Mock using_storage_backend como context manager
    class DummyStorageCtx:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(upload_module, "using_storage_backend", lambda adapter: DummyStorageCtx())

    class DummyProgressDialog:
        def __init__(self, parent, total_files, total_bytes):
            pass

        def update_progress(self, bytes_sent):
            pass

        def increment_file(self):
            pass

        def update_for_file(self, filename, size_bytes):
            pass

        def close(self):
            pass

    monkeypatch.setattr(upload_module, "UploadProgressDialog", DummyProgressDialog)

    # Mock Supabase client
    class DummyTableQuery:
        def __init__(self, table_name: str = ""):
            self.table_name = table_name

        def table(self, name: str):
            return DummyTableQuery(name)

        def insert(self, payload):
            return self

        def select(self, *args):
            return self

        def eq(self, col, val):
            return self

        def is_(self, col, val):
            return self

        def limit(self, n):
            return self

    # Mock get_supabase para evitar conexão real
    import infra.supabase.db_client as db_client_module

    mock_supabase = DummyTableQuery()
    monkeypatch.setattr(db_client_module, "get_supabase", lambda: mock_supabase)

    # Mock threading para execução síncrona
    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None, name=None):
            self._target = target
            self._args = args
            self._kwargs = kwargs or {}

        def start(self):
            if self._target:
                self._target(*self._args, **self._kwargs)

    import threading

    monkeypatch.setattr(threading, "Thread", ImmediateThread)

    # Executar pipeline completo
    args = (app, None, ents, arquivos, None)
    kwargs = {}

    clientes_pipeline.validate_inputs(*args, **kwargs)
    clientes_pipeline.prepare_payload(*args, **kwargs)
    clientes_pipeline.perform_uploads(*args, **kwargs)
    clientes_pipeline.finalize_state(*args, **kwargs)

    # Validações
    assert app.carregar_called is True, "App não chamou carregar() ao finalizar"
    assert len(uploads_log) > 0, "Nenhum upload foi registrado"

    # Verificar que os uploads contêm cliente_id e subpasta corretas
    for upload in uploads_log:
        path = upload["path"]
        assert "123" in path, f"Upload path não contém cliente_id 123: {path}"
        assert "SUBPASTA" in path, f"Upload path não contém subpasta: {path}"


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
    import adapters.storage.api as storage_api_module

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
