"""
TESTE_1 - clientes/service

Objetivo: aumentar a cobertura de src/modules/clientes/service.py na fase 48,
cobrindo criacao/duplicatas, lixeira, exclusoes e manipulacao de observacoes.
"""

from __future__ import annotations

import types
from contextlib import contextmanager

import pytest

import src.modules.clientes.core.service as clientes_service


class DummyQuery:
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


def test_current_utc_iso_tem_timezone():
    value = clientes_service._current_utc_iso()
    assert "T" in value and value.endswith("+00:00")


def test_checar_duplicatas_para_form_filtra_o_proprio_id(monkeypatch):
    def fake_checar_duplicatas_info(**kwargs):
        return {
            "cnpj_conflict": {"id": 5},
            "razao_conflicts": [{"id": 5}, {"id": 7}],
            "numero_conflicts": [{"id": 8}, None],
        }

    monkeypatch.setattr(clientes_service, "checar_duplicatas_info", fake_checar_duplicatas_info)
    valores = {"CNPJ": "1", "Razao Social": "ACME", "WhatsApp": "999", "Nome": "Nome"}

    result = clientes_service.checar_duplicatas_para_form(valores, row=(5, "foo"))

    assert result["blocking_fields"]["cnpj"] is False
    assert result["blocking_fields"]["razao"] is True
    assert result["conflict_ids"]["cnpj"] == []
    assert result["conflict_ids"]["razao"] == [7]
    assert result["conflict_ids"]["numero"] == [8]


def test_salvar_cliente_a_partir_do_form_duplica_levanta_erro(monkeypatch):
    monkeypatch.setattr(clientes_service, "normalize_cnpj_norm", lambda cnpj: "123")
    fake_cli = types.SimpleNamespace(id=99, razao_social="Dup")
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda norm, exclude_id=None: fake_cli)

    with pytest.raises(clientes_service.ClienteCNPJDuplicadoError):
        clientes_service.salvar_cliente_a_partir_do_form((1,), {"CNPJ": "12"})


def test_salvar_cliente_a_partir_do_form_caminho_feliz(monkeypatch):
    calls = {}
    monkeypatch.setattr(clientes_service, "normalize_cnpj_norm", lambda cnpj: "")
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda norm, exclude_id=None: None)

    def fake_salvar(row, valores):
        calls["args"] = (row, valores)
        return ("ok", {})

    monkeypatch.setattr(clientes_service, "salvar_cliente", fake_salvar)

    result = clientes_service.salvar_cliente_a_partir_do_form((4,), {"CNPJ": "12", "x": 1})

    assert result == ("ok", {})
    assert calls["args"][0] == (4,)
    assert calls["args"][1]["x"] == 1


def test_mover_cliente_para_lixeira_atualiza_campos(monkeypatch):
    queries = []

    class StubSupabase:
        def table(self, name):
            return DummyQuery(name)

    monkeypatch.setattr(clientes_service, "supabase", StubSupabase())

    def fake_exec(query):
        queries.append(query)
        return query

    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec)

    clientes_service.mover_cliente_para_lixeira(10)

    assert queries
    query = queries[0]
    assert query.table == "clients"
    action, payload = query.actions[0]
    assert action == "update" and "deleted_at" in payload and "ultima_alteracao" in payload
    assert ("eq", "id", 10) in query.actions


def test_restaurar_clientes_da_lixeira_lista_vazia(monkeypatch):
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: pytest.fail("nao deveria chamar"))
    clientes_service.restaurar_clientes_da_lixeira([])


def test_restaurar_clientes_da_lixeira_caminho_feliz(monkeypatch):
    queries = []

    class StubSupabase:
        def table(self, name):
            return DummyQuery(name)

    monkeypatch.setattr(clientes_service, "supabase", StubSupabase())
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: queries.append(q))

    clientes_service.restaurar_clientes_da_lixeira([1, 2])

    query = queries[0]
    update = next(item for item in query.actions if item[0] == "update")[1]
    assert update["deleted_at"] is None
    assert "ultima_alteracao" in update and "T" in update["ultima_alteracao"]
    assert ("in", "id", [1, 2]) in query.actions


def test_excluir_clientes_definitivamente_sem_ids():
    ok, errs = clientes_service.excluir_clientes_definitivamente([])
    assert (ok, errs) == (0, [])


def test_excluir_clientes_definitivamente_sem_org(monkeypatch):
    class StubAuth:
        def get_user(self):
            return types.SimpleNamespace(id=None)

    class StubSupabase:
        auth = StubAuth()

        def table(self, name):
            return DummyQuery(name)

    monkeypatch.setattr(clientes_service, "supabase", StubSupabase())
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: pytest.fail("exec nao deveria ser chamado"))

    ok, errs = clientes_service.excluir_clientes_definitivamente([1])

    assert ok == 0
    assert errs and "Falha ao resolver" in errs[0][1]


def test_excluir_clientes_definitivamente_caminho_feliz(monkeypatch):
    class StubAuth:
        def get_user(self):
            return types.SimpleNamespace(id="user-1")

    class StubSupabase:
        auth = StubAuth()

        def table(self, name):
            return DummyQuery(name)

    supabase_stub = StubSupabase()
    queries = []

    def fake_exec(query):
        queries.append(query)
        if query.table == "memberships":
            return types.SimpleNamespace(data=[{"org_id": "org-1"}])
        return types.SimpleNamespace(data=None)

    monkeypatch.setattr(clientes_service, "supabase", supabase_stub)
    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec)

    storage_calls = {"list": [], "delete": []}

    def fake_list_files(prefix):
        storage_calls["list"].append(prefix)
        if prefix.endswith("/sub"):
            return [{"name": "file2", "metadata": {"size": 1}}]
        return [{"name": "file1", "metadata": {"size": 1}}, {"name": "sub", "metadata": None}]

    def fake_delete_file(path):
        storage_calls["delete"].append(path)
        return True

    @contextmanager
    def fake_backend(adapter):
        yield

    monkeypatch.setattr(clientes_service, "storage_list_files", fake_list_files)
    monkeypatch.setattr(clientes_service, "storage_delete_file", fake_delete_file)
    monkeypatch.setattr(clientes_service, "using_storage_backend", fake_backend)
    monkeypatch.setattr(clientes_service, "SupabaseStorageAdapter", lambda bucket: f"adapter-{bucket}")

    progress = []

    ok, errs = clientes_service.excluir_clientes_definitivamente(
        [3, 4], progress_cb=lambda idx, total, cid: progress.append((idx, total, cid))
    )

    assert ok == 2 and errs == []
    assert storage_calls["delete"] == [
        "org-1/3/file1",
        "org-1/3/sub/file2",
        "org-1/4/file1",
        "org-1/4/sub/file2",
    ]
    assert progress == [(1, 2, 3), (2, 2, 4)]
    # Confirm exec_postgrest was called for memberships and deletes
    tables = [q.table for q in queries]
    assert "memberships" in tables and tables.count("clients") >= 2


def test_excluir_cliente_simples(monkeypatch):
    queries = []
    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda name: DummyQuery(name)))
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: queries.append(q))

    clientes_service.excluir_cliente_simples(7)

    query = queries[0]
    assert ("delete", None) in query.actions
    assert ("eq", "id", 7) in query.actions


def test_listar_clientes_na_lixeira_core(monkeypatch):
    monkeypatch.setattr(clientes_service, "_list_clientes_deletados_core", lambda order_by, descending: ["x"])
    assert clientes_service.listar_clientes_na_lixeira() == ["x"]


def test_listar_clientes_na_lixeira_fallback(monkeypatch):
    monkeypatch.setattr(
        clientes_service, "_list_clientes_deletados_core", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail"))
    )
    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda name: DummyQuery(name)))
    data = [{"id": 1}]
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: {"data": data})

    result = clientes_service.listar_clientes_na_lixeira(order_by="id", descending=False)

    assert result == data


def test_fetch_cliente_by_id_dict(monkeypatch):
    monkeypatch.setattr(clientes_service, "get_cliente_by_id", lambda cid: {"id": cid, "razao_social": "Raz"})
    assert clientes_service.fetch_cliente_by_id(5)["id"] == 5


def test_fetch_cliente_by_id_obj(monkeypatch):
    obj = types.SimpleNamespace(id=2, razao_social="R", cnpj="C", numero="N", observacoes="O")
    monkeypatch.setattr(clientes_service, "get_cliente_by_id", lambda cid: obj)

    result = clientes_service.fetch_cliente_by_id(2)

    assert result["cnpj"] == "C" and result["numero"] == "N" and result["observacoes"] == "O"


def test_update_cliente_status_and_observacoes_dict(monkeypatch):
    queries = []
    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda name: DummyQuery(name)))
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: queries.append(q))
    clientes_service.update_cliente_status_and_observacoes({"id": 11, "observacoes": "[OLD] texto"}, "ATIVO")

    payload = queries[0].actions[0][1]
    assert payload["observacoes"] == "[ATIVO] texto"
    assert ("eq", "id", 11) in queries[0].actions


def test_update_cliente_status_and_observacoes_com_id_int(monkeypatch):
    monkeypatch.setattr(
        clientes_service, "fetch_cliente_by_id", lambda cid: {"id": cid, "observacoes": "[INATIVO] corpo"}
    )
    queries = []
    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda name: DummyQuery(name)))
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: queries.append(q))

    clientes_service.update_cliente_status_and_observacoes(13, "NOVO")

    payload = queries[0].actions[0][1]
    assert payload["observacoes"] == "[NOVO] corpo"


def test_extrair_dados_cartao_cnpj_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(clientes_service, "log", types.SimpleNamespace(debug=lambda *a, **k: None))
    monkeypatch.setattr("src.utils.paths.ensure_str_path", lambda p: str(p))
    monkeypatch.setattr("src.utils.file_utils.list_and_classify_pdfs", lambda base_dir: [])
    monkeypatch.setattr("src.utils.file_utils.find_cartao_cnpj_pdf", lambda base_dir: tmp_path / "cartao.pdf")
    monkeypatch.setattr("src.utils.pdf_reader.read_pdf_text", lambda path: "cnpj 12.345.678/0001-99 razao ACME")
    monkeypatch.setattr(
        "src.utils.text_utils.extract_company_fields",
        lambda text: {"cnpj": "12.345.678/0001-99", "razao_social": "ACME"},
    )

    result = clientes_service.extrair_dados_cartao_cnpj_em_pasta(str(tmp_path))

    assert result["cnpj"] == "12.345.678/0001-99"
    assert result["razao_social"] == "ACME"
