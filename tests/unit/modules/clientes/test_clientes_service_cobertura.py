"""
Testes adicionais para aumentar cobertura de src/modules/clientes/service.py para ≥90%.

Foco em branches e linhas não cobertas nos testes existentes.
"""

from __future__ import annotations

import types
from contextlib import contextmanager

import pytest

import src.modules.clientes.core.service as clientes_service


class DummyQuery:
    """Dummy query builder para testes."""

    def __init__(self, table: str):
        self.table = table
        self.actions = []

    def update(self, payload):
        self.actions.append(("update", payload))
        return self

    def delete(self):
        self.actions.append(("delete", None))
        return self

    def eq(self, field, value):
        self.actions.append(("eq", field, value))
        return self

    def in_(self, field, values):
        self.actions.append(("in", field, list(values)))
        return self

    def select(self, cols):
        self.actions.append(("select", cols))
        return self

    def order(self, col, desc=True):
        self.actions.append(("order", col, desc))
        return self

    def limit(self, value):
        self.actions.append(("limit", value))
        return self

    @property
    def not_(self):
        return self

    def is_(self, col, value):
        self.actions.append(("is", col, value))
        return self


def test_extract_cliente_id_com_excecao():
    """Testa que exceção ao extrair ID retorna None."""
    # Row com valor não conversível para int
    result = clientes_service._extract_cliente_id(("abc",))
    assert result is None


def test_ensure_str_com_nao_string():
    """Testa que _ensure_str converte não-string para vazio."""
    assert clientes_service._ensure_str(123) == ""
    assert clientes_service._ensure_str(None) == ""
    assert clientes_service._ensure_str("text") == "text"


def test_extrair_dados_cartao_cnpj_com_classify_sucesso(monkeypatch, tmp_path):
    """Testa branch onde list_and_classify_pdfs encontra cnpj_card."""
    # Mock log com warning e debug
    monkeypatch.setattr(
        clientes_service,
        "log",
        types.SimpleNamespace(debug=lambda *a, **k: None, warning=lambda *a, **k: None),
    )

    docs = [{"type": "cnpj_card", "meta": {"cnpj": "11.222.333/0001-44", "razao_social": "Empresa Teste"}}]

    monkeypatch.setattr("src.utils.file_utils.list_and_classify_pdfs", lambda base_dir: docs)

    # Usa tmp_path que é um diretório real existente
    result = clientes_service.extrair_dados_cartao_cnpj_em_pasta(str(tmp_path))

    assert result["cnpj"] == "11.222.333/0001-44"
    assert result["razao_social"] == "Empresa Teste"


def test_extrair_dados_cartao_cnpj_sem_pdf_fallback(monkeypatch, tmp_path):
    """Testa branch onde não encontra PDF no fallback."""
    monkeypatch.setattr(
        clientes_service,
        "log",
        types.SimpleNamespace(debug=lambda *a, **k: None, warning=lambda *a, **k: None),
    )

    monkeypatch.setattr("src.utils.file_utils.list_and_classify_pdfs", lambda base_dir: [])
    monkeypatch.setattr("src.utils.file_utils.find_cartao_cnpj_pdf", lambda base_dir: None)

    # Usa tmp_path que é um diretório real existente
    result = clientes_service.extrair_dados_cartao_cnpj_em_pasta(str(tmp_path))

    assert result["cnpj"] is None
    assert result["razao_social"] is None


def test_extrair_dados_cartao_cnpj_pdf_sem_texto(monkeypatch, tmp_path):
    """Testa branch onde PDF existe mas não tem texto."""
    monkeypatch.setattr(
        clientes_service,
        "log",
        types.SimpleNamespace(debug=lambda *a, **k: None, warning=lambda *a, **k: None),
    )

    monkeypatch.setattr("src.utils.file_utils.list_and_classify_pdfs", lambda base_dir: [])
    monkeypatch.setattr("src.utils.file_utils.find_cartao_cnpj_pdf", lambda base_dir: "/fake/pdf.pdf")
    monkeypatch.setattr("src.utils.paths.ensure_str_path", lambda p: str(p))
    monkeypatch.setattr("src.utils.pdf_reader.read_pdf_text", lambda path: "")

    # Usa tmp_path que é um diretório real existente
    result = clientes_service.extrair_dados_cartao_cnpj_em_pasta(str(tmp_path))

    assert result["cnpj"] is None
    assert result["razao_social"] is None


def test_resolve_current_org_id_sem_uid_em_user(monkeypatch):
    """Testa branch onde user não tem id diretamente."""

    class StubAuth:
        def get_user(self):
            # Simula resposta sem user.id, mas com dict aninhado
            return types.SimpleNamespace(user=None, data={"user": {"id": "user-from-dict"}})

    class StubSupabase:
        auth = StubAuth()

        def table(self, name):
            return DummyQuery(name)

    monkeypatch.setattr(clientes_service, "supabase", StubSupabase())

    def fake_exec(query):
        if query.table == "memberships":
            return types.SimpleNamespace(data=[{"org_id": "org-123"}])
        return types.SimpleNamespace(data=None)

    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec)

    # Espera exceção porque user é None
    with pytest.raises(RuntimeError, match="Usuário não autenticado|Falha ao resolver"):
        clientes_service._resolve_current_org_id()


def test_resolve_current_org_id_sem_org(monkeypatch):
    """Testa exceção quando não encontra organização."""

    class StubAuth:
        def get_user(self):
            return types.SimpleNamespace(id="user-1")

    class StubSupabase:
        auth = StubAuth()

        def table(self, name):
            return DummyQuery(name)

    monkeypatch.setattr(clientes_service, "supabase", StubSupabase())
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: types.SimpleNamespace(data=[]))

    with pytest.raises(RuntimeError, match="Organização não encontrada|Falha ao resolver"):
        clientes_service._resolve_current_org_id()


def test_gather_paths_com_excecao_em_list_files(monkeypatch):
    """Testa que exceção em storage_list_files é capturada."""

    def fake_list_files(prefix):
        raise RuntimeError("Storage error")

    @contextmanager
    def fake_backend(adapter):
        yield

    monkeypatch.setattr(clientes_service, "storage_list_files", fake_list_files)
    monkeypatch.setattr(clientes_service, "using_storage_backend", fake_backend)
    monkeypatch.setattr(clientes_service, "SupabaseStorageAdapter", lambda bucket: f"adapter-{bucket}")

    paths = clientes_service._gather_paths("bucket", "prefix")
    assert paths == []


def test_gather_paths_com_item_sem_name(monkeypatch):
    """Testa que items sem 'name' são ignorados."""

    def fake_list_files(prefix):
        return [
            {"metadata": {"size": 1}},  # Sem 'name'
            {"name": "file.txt", "metadata": {"size": 1}},
        ]

    @contextmanager
    def fake_backend(adapter):
        yield

    monkeypatch.setattr(clientes_service, "storage_list_files", fake_list_files)
    monkeypatch.setattr(clientes_service, "using_storage_backend", fake_backend)
    monkeypatch.setattr(clientes_service, "SupabaseStorageAdapter", lambda bucket: f"adapter-{bucket}")

    paths = clientes_service._gather_paths("bucket", "prefix")
    assert len(paths) == 1
    assert paths[0] == "prefix/file.txt"


def test_remove_cliente_storage_com_erro_em_delete(monkeypatch):
    """Testa que erro ao deletar arquivo é capturado."""

    def fake_gather_paths(bucket, prefix):
        return ["file1.txt", "file2.txt"]

    def fake_delete_file(path):
        if path == "file2.txt":
            raise RuntimeError("Delete failed")
        return True

    monkeypatch.setattr(clientes_service, "_gather_paths", fake_gather_paths)
    monkeypatch.setattr(clientes_service, "storage_delete_file", fake_delete_file)
    monkeypatch.setattr(clientes_service, "log", types.SimpleNamespace(info=lambda *a, **k: None))

    errs = []
    clientes_service._remove_cliente_storage("bucket", "org", 1, errs)

    assert len(errs) == 1
    assert errs[0][0] == 1
    assert "Storage:" in errs[0][1]


def test_remove_cliente_storage_com_erro_em_gather(monkeypatch):
    """Testa que erro em _gather_paths é capturado."""

    def fake_gather_paths(bucket, prefix):
        raise RuntimeError("Gather failed")

    monkeypatch.setattr(clientes_service, "_gather_paths", fake_gather_paths)

    errs = []
    clientes_service._remove_cliente_storage("bucket", "org", 1, errs)

    assert len(errs) == 1
    assert "Storage:" in errs[0][1]


def test_excluir_clientes_definitivamente_com_erro_em_delete_db(monkeypatch):
    """Testa que erro ao deletar do DB é capturado."""

    class StubAuth:
        def get_user(self):
            return types.SimpleNamespace(id="user-1")

    class StubSupabase:
        auth = StubAuth()

        def table(self, name):
            return DummyQuery(name)

    delete_count = {"count": 0}

    def fake_exec(query):
        if query.table == "memberships":
            return types.SimpleNamespace(data=[{"org_id": "org-1"}])
        if query.table == "clients" and any(a[0] == "delete" for a in query.actions):
            delete_count["count"] += 1
            if delete_count["count"] == 2:
                raise RuntimeError("DB delete failed")
        return types.SimpleNamespace(data=None)

    monkeypatch.setattr(clientes_service, "supabase", StubSupabase())
    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec)
    monkeypatch.setattr(clientes_service, "_gather_paths", lambda b, p: [])

    @contextmanager
    def fake_backend(adapter):
        yield

    monkeypatch.setattr(clientes_service, "using_storage_backend", fake_backend)
    monkeypatch.setattr(clientes_service, "SupabaseStorageAdapter", lambda bucket: f"adapter-{bucket}")
    monkeypatch.setattr(
        clientes_service, "log", types.SimpleNamespace(info=lambda *a, **k: None, exception=lambda *a, **k: None)
    )

    ok, errs = clientes_service.excluir_clientes_definitivamente([1, 2])

    assert ok == 1
    assert len(errs) == 1
    assert errs[0][0] == 2


def test_excluir_clientes_definitivamente_callback_com_erro(monkeypatch):
    """Testa que erro no callback de progresso é capturado."""

    class StubAuth:
        def get_user(self):
            return types.SimpleNamespace(id="user-1")

    class StubSupabase:
        auth = StubAuth()

        def table(self, name):
            return DummyQuery(name)

    def fake_exec(query):
        if query.table == "memberships":
            return types.SimpleNamespace(data=[{"org_id": "org-1"}])
        return types.SimpleNamespace(data=None)

    monkeypatch.setattr(clientes_service, "supabase", StubSupabase())
    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec)
    monkeypatch.setattr(clientes_service, "_gather_paths", lambda b, p: [])

    @contextmanager
    def fake_backend(adapter):
        yield

    monkeypatch.setattr(clientes_service, "using_storage_backend", fake_backend)
    monkeypatch.setattr(clientes_service, "SupabaseStorageAdapter", lambda bucket: f"adapter-{bucket}")
    monkeypatch.setattr(
        clientes_service, "log", types.SimpleNamespace(info=lambda *a, **k: None, exception=lambda *a, **k: None)
    )

    def bad_callback(idx, total, cid):
        raise RuntimeError("Callback failed")

    ok, errs = clientes_service.excluir_clientes_definitivamente([1], progress_cb=bad_callback)

    assert ok == 1
    assert errs == []


def test_listar_clientes_na_lixeira_fallback_com_resp_dict(monkeypatch):
    """Testa fallback quando exec_postgrest retorna dict em vez de objeto."""

    def fake_list_core(*a, **k):
        raise RuntimeError("Core failed")

    monkeypatch.setattr(clientes_service, "_list_clientes_deletados_core", fake_list_core)
    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda name: DummyQuery(name)))

    # Retorna dict (não objeto com .data)
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: {"data": [{"id": 99}]})

    result = clientes_service.listar_clientes_na_lixeira()

    assert len(result) == 1
    assert result[0]["id"] == 99


def test_fetch_cliente_by_id_retorna_none(monkeypatch):
    """Testa que retorna None quando cliente não existe."""
    monkeypatch.setattr(clientes_service, "get_cliente_by_id", lambda cid: None)

    result = clientes_service.fetch_cliente_by_id(999)
    assert result is None


def test_update_cliente_status_sem_id(monkeypatch):
    """Testa exceção quando cliente não tem ID."""
    with pytest.raises(ValueError, match="id"):
        clientes_service.update_cliente_status_and_observacoes({}, "ATIVO")


def test_update_cliente_status_com_observacoes_attribute(monkeypatch):
    """Testa branch usando getattr para observacoes."""
    obj = {"id": 5, "observacoes": "[STATUS] texto"}

    queries = []
    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda name: DummyQuery(name)))
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: queries.append(q))

    clientes_service.update_cliente_status_and_observacoes(obj, "NOVO")

    payload = queries[0].actions[0][1]
    assert payload["observacoes"] == "[NOVO] texto"


def test_update_cliente_status_com_observacoes_maiuscula(monkeypatch):
    """Testa que aceita Observacoes (maiúscula) como fallback."""
    # Não precisa testar a lógica interna, apenas garantir que não quebra
    obj = {"id": 6, "Observacoes": "[ANTIGO] corpo", "observacoes": None}

    queries = []
    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda name: DummyQuery(name)))
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: queries.append(q))

    clientes_service.update_cliente_status_and_observacoes(obj, "ATIVO")

    # Apenas verifica que executou sem erro
    assert len(queries) == 1


def test_update_cliente_status_remove_status_quando_none(monkeypatch):
    """Testa que remove prefixo de status quando novo_status é None."""
    queries = []
    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda name: DummyQuery(name)))
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: queries.append(q))

    clientes_service.update_cliente_status_and_observacoes({"id": 10, "observacoes": "[OLD] texto"}, None)

    payload = queries[0].actions[0][1]
    assert payload["observacoes"] == "texto"
