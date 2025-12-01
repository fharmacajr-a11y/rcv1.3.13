import types
from contextlib import nullcontext
from typing import Tuple

from src.core.services import lixeira_service


class DummyTable:
    def __init__(self, name):
        self.name = name

    def update(self, payload):
        return self

    def delete(self):
        return self

    def eq(self, *a, **k):
        return self


def test_ensure_mandatory_subfolders_cria_keep_quando_vazio(monkeypatch):
    mandatory = ("SIFAP", "ANVISA")
    uploads: list[Tuple[str, str, str]] = []

    monkeypatch.setattr(lixeira_service, "get_mandatory_subpastas", lambda: mandatory)
    monkeypatch.setattr(lixeira_service, "using_storage_backend", lambda adapter: nullcontext())
    monkeypatch.setattr(lixeira_service, "SupabaseStorageAdapter", lambda bucket: object())
    monkeypatch.setattr(lixeira_service, "storage_list_files", lambda prefix: [])
    monkeypatch.setattr(
        lixeira_service,
        "storage_upload_file",
        lambda src, remote, content_type=None: uploads.append((src, remote, content_type)),
    )

    lixeira_service._ensure_mandatory_subfolders("ORG/123")  # type: ignore[protected-access]

    assert len(uploads) == len(mandatory)
    remote_keys = {remote for _, remote, _ in uploads}
    assert "ORG/123/SIFAP/.keep" in remote_keys
    assert "ORG/123/ANVISA/.keep" in remote_keys


def test_ensure_mandatory_subfolders_nao_cria_quando_ja_existe(monkeypatch):
    mandatory = ("SIFAP", "ANVISA")
    uploads: list[str] = []

    monkeypatch.setattr(lixeira_service, "get_mandatory_subpastas", lambda: mandatory)
    monkeypatch.setattr(lixeira_service, "using_storage_backend", lambda adapter: nullcontext())
    monkeypatch.setattr(lixeira_service, "SupabaseStorageAdapter", lambda bucket: object())

    def fake_list(prefix: str):
        if prefix.startswith("ORG/123/SIFAP/"):
            return [{"name": "dummy"}]
        return []

    monkeypatch.setattr(lixeira_service, "storage_list_files", fake_list)
    monkeypatch.setattr(
        lixeira_service,
        "storage_upload_file",
        lambda src, remote, content_type=None: uploads.append(remote),
    )

    lixeira_service._ensure_mandatory_subfolders("ORG/123")  # type: ignore[protected-access]

    assert "ORG/123/SIFAP/.keep" not in uploads  # já tinha item
    assert "ORG/123/ANVISA/.keep" in uploads


def test_restore_clients_sucesso_chama_update_e_guardasubpastas(monkeypatch):
    updates: list[Tuple] = []
    guarded_prefixes: list[str] = []

    fake_supabase = types.SimpleNamespace(table=lambda name: DummyTable(name))

    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (fake_supabase, "ORGID"))
    monkeypatch.setattr(lixeira_service, "_ensure_mandatory_subfolders", lambda prefix: guarded_prefixes.append(prefix))
    monkeypatch.setattr(
        lixeira_service,
        "exec_postgrest",
        lambda *a, **k: updates.append((a, k)),
    )
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.restore_clients([10, 11], parent=None)

    assert ok == 2
    assert errs == []
    assert len(updates) == 2
    assert "ORGID/10" in guarded_prefixes
    assert "ORGID/11" in guarded_prefixes


def test_restore_clients_quando_get_supabase_falha_mostra_erro(monkeypatch):
    monkeypatch.setattr(
        lixeira_service, "_get_supabase_and_org", lambda: (_ for _ in ()).throw(RuntimeError("falha qualquer"))
    )
    calls: list[Tuple] = []
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: calls.append(a))

    ok, errs = lixeira_service.restore_clients([10], parent=None)

    assert ok == 0
    assert len(errs) == 1
    assert errs[0][0] == 0
    assert calls and calls[0][0] == "Erro"


def test_hard_delete_clients_remove_storage_e_db(monkeypatch):
    deletions: list[int] = []
    removes: list[Tuple[str, int]] = []
    password_deletes: list[Tuple[str, str]] = []

    monkeypatch.setattr(
        lixeira_service,
        "_get_supabase_and_org",
        lambda: (types.SimpleNamespace(table=lambda name: DummyTable(name)), "ORGID"),
    )
    monkeypatch.setattr(
        lixeira_service, "_remove_storage_prefix", lambda org_id, cid: removes.append((org_id, cid)) or 3
    )
    # FIX-SENHAS-015: Mock delete_passwords_by_client
    monkeypatch.setattr(
        lixeira_service,
        "delete_passwords_by_client",
        lambda org_id, client_id: password_deletes.append((org_id, client_id)) or 2,
    )
    monkeypatch.setattr(lixeira_service, "exec_postgrest", lambda *a, **k: deletions.append(a[0]))
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.hard_delete_clients([20, 21], parent=None)

    assert ok == 2
    assert errs == []
    assert removes == [("ORGID", 20), ("ORGID", 21)]
    # FIX-SENHAS-015: Verifica que senhas foram deletadas
    assert password_deletes == [("ORGID", "20"), ("ORGID", "21")]
    assert len(deletions) == 2


def test_hard_delete_clients_erros_sao_coletados(monkeypatch):
    monkeypatch.setattr(
        lixeira_service,
        "_get_supabase_and_org",
        lambda: (types.SimpleNamespace(table=lambda name: DummyTable(name)), "ORGID"),
    )

    def fake_remove(org_id, cid):
        if cid == 30:
            raise RuntimeError("fail remove")
        return 1

    deletes: list[int] = []

    def fake_exec(expr):
        deletes.append(expr)
        if len(deletes) > 1:
            raise RuntimeError("db fail")

    # FIX-SENHAS-015: Mock delete_passwords_by_client
    monkeypatch.setattr(lixeira_service, "delete_passwords_by_client", lambda org_id, client_id: 0)
    monkeypatch.setattr(lixeira_service, "_remove_storage_prefix", fake_remove)
    monkeypatch.setattr(lixeira_service, "exec_postgrest", fake_exec)
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.hard_delete_clients([30, 31], parent=None)

    # FIX-SENHAS-015: Agora temos erros de Storage e DB
    assert ok == 1  # only second delete succeeded before db fail
    assert len(errs) == 2
    err_ids = {cid for cid, _ in errs}
    assert 30 in err_ids and 31 in err_ids


# ============================================================================
# TESTES ADICIONAIS: Cobertura expandida (TEST-001 Fase 7)
# ============================================================================


def test_restore_clients_lista_vazia_retorna_zero(monkeypatch):
    """Restaurar lista vazia não chama backend."""
    updates: list = []
    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (object(), "ORGID"))
    monkeypatch.setattr(lixeira_service, "exec_postgrest", lambda *a, **k: updates.append(a))

    ok, errs = lixeira_service.restore_clients([])

    assert ok == 0
    assert errs == []
    assert len(updates) == 0


def test_restore_clients_multiplos_com_falha_parcial(monkeypatch):
    """Alguns clientes restauram, outros falham."""
    updates: list[int] = []

    def fake_exec(expr):
        updates.append(expr)
        if len(updates) == 2:  # falha no 2º
            raise RuntimeError("DB timeout")

    fake_supabase = types.SimpleNamespace(table=lambda name: DummyTable(name))
    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (fake_supabase, "ORGID"))
    monkeypatch.setattr(lixeira_service, "exec_postgrest", fake_exec)
    monkeypatch.setattr(lixeira_service, "_ensure_mandatory_subfolders", lambda prefix: None)
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.restore_clients([100, 200, 300])

    assert ok == 2  # 1º e 3º sucesso
    assert len(errs) == 1
    assert errs[0][0] == 200


def test_restore_clients_subfolder_guard_falha_nao_impede_restauracao(monkeypatch):
    """Falha ao criar subpastas não impede restauração do cliente."""
    updates: list = []

    def fake_ensure(prefix: str):
        raise RuntimeError("Storage indisponível")

    fake_supabase = types.SimpleNamespace(table=lambda name: DummyTable(name))
    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (fake_supabase, "ORGID"))
    monkeypatch.setattr(lixeira_service, "exec_postgrest", lambda *a, **k: updates.append(a))
    monkeypatch.setattr(lixeira_service, "_ensure_mandatory_subfolders", fake_ensure)
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.restore_clients([123])

    # Cliente restaurado mesmo com falha no guard
    assert ok == 1
    assert errs == []
    assert len(updates) == 1


def test_hard_delete_clients_lista_vazia_retorna_zero(monkeypatch):
    """Excluir lista vazia não chama backend."""
    deletes: list = []
    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (object(), "ORGID"))
    monkeypatch.setattr(lixeira_service, "exec_postgrest", lambda *a, **k: deletes.append(a))

    ok, errs = lixeira_service.hard_delete_clients([])

    assert ok == 0
    assert errs == []
    assert len(deletes) == 0


def test_hard_delete_clients_storage_vazio_nao_falha(monkeypatch):
    """Exclusão com storage vazio não gera erro."""
    deletes: list = []

    fake_supabase = types.SimpleNamespace(table=lambda name: DummyTable(name))
    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (fake_supabase, "ORGID"))
    monkeypatch.setattr(lixeira_service, "_remove_storage_prefix", lambda org_id, cid: 0)  # 0 removidos
    # FIX-SENHAS-015: Mock delete_passwords_by_client
    monkeypatch.setattr(lixeira_service, "delete_passwords_by_client", lambda org_id, client_id: 0)
    monkeypatch.setattr(lixeira_service, "exec_postgrest", lambda *a, **k: deletes.append(a))
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.hard_delete_clients([456])

    assert ok == 1
    assert errs == []


def test_hard_delete_clients_storage_falha_continua_db_delete(monkeypatch):
    """Falha no Storage não impede delete do DB."""
    deletes: list = []

    def fake_remove(org_id: str, cid: int):
        raise RuntimeError("Storage timeout")

    fake_supabase = types.SimpleNamespace(table=lambda name: DummyTable(name))
    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (fake_supabase, "ORGID"))
    monkeypatch.setattr(lixeira_service, "_remove_storage_prefix", fake_remove)
    # FIX-SENHAS-015: Mock delete_passwords_by_client
    monkeypatch.setattr(lixeira_service, "delete_passwords_by_client", lambda org_id, client_id: 0)
    monkeypatch.setattr(lixeira_service, "exec_postgrest", lambda *a, **k: deletes.append(a))
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.hard_delete_clients([789])

    # DB delete continua mesmo com falha no Storage
    assert ok == 1
    assert len(errs) == 1  # Erro registrado (Storage)
    assert "storage" in errs[0][1].lower()
    assert len(deletes) == 1  # DB delete foi chamado


def test_gather_all_paths_lista_arquivos_recursivamente(monkeypatch):
    """_gather_all_paths percorre recursivamente pastas no Storage."""

    def fake_list_children(bucket: str, prefix: str):
        if prefix == "root":
            return [
                {"name": "file1.pdf", "is_folder": False},
                {"name": "subdir", "is_folder": True},
            ]
        if prefix == "root/subdir":
            return [{"name": "file2.pdf", "is_folder": False}]
        return []

    monkeypatch.setattr(lixeira_service, "_list_storage_children", fake_list_children)

    paths = lixeira_service._gather_all_paths("bucket", "root")  # type: ignore[protected-access]

    assert len(paths) == 2
    assert "root/file1.pdf" in paths
    assert "root/subdir/file2.pdf" in paths


def test_list_storage_children_identifica_pastas_corretamente(monkeypatch):
    """_list_storage_children identifica pastas (metadata=None) vs arquivos."""
    fake_items = [
        {"name": "doc.pdf", "metadata": {"size": 100}},
        {"name": "pasta", "metadata": None},  # pasta
    ]

    monkeypatch.setattr(lixeira_service, "SupabaseStorageAdapter", lambda bucket: object())
    monkeypatch.setattr(lixeira_service, "using_storage_backend", lambda adapter: nullcontext())
    monkeypatch.setattr(lixeira_service, "storage_list_files", lambda prefix: fake_items)

    result = lixeira_service._list_storage_children("bucket", "prefix")  # type: ignore[protected-access]

    assert len(result) == 2
    assert result[0]["name"] == "doc.pdf"
    assert result[0]["is_folder"] is False
    assert result[1]["name"] == "pasta"
    assert result[1]["is_folder"] is True


def test_remove_storage_prefix_remove_multiplos_arquivos(monkeypatch):
    """_remove_storage_prefix remove todos os arquivos do prefixo."""
    deleted_keys: list[str] = []

    monkeypatch.setattr(
        lixeira_service,
        "_gather_all_paths",
        lambda bucket, prefix: [f"{prefix}/file{i}.pdf" for i in range(5)],
    )
    monkeypatch.setattr(lixeira_service, "SupabaseStorageAdapter", lambda bucket: object())
    monkeypatch.setattr(lixeira_service, "using_storage_backend", lambda adapter: nullcontext())
    monkeypatch.setattr(
        lixeira_service,
        "storage_delete_file",
        lambda key: deleted_keys.append(key) or True,
    )

    removed = lixeira_service._remove_storage_prefix("ORGID", 123)  # type: ignore[protected-access]

    assert removed == 5
    assert len(deleted_keys) == 5
    for i in range(5):
        assert f"ORGID/123/file{i}.pdf" in deleted_keys


def test_restore_clients_falha_autenticacao_sem_user_id(monkeypatch):
    """restore_clients captura RuntimeError de _get_supabase_and_org e mostra messagebox (linhas 28-35, 170-172)."""
    import types

    def fake_get_supabase_and_org():
        # Simula o comportamento de user.id=None
        raise RuntimeError("Usuário não autenticado no Supabase.")

    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", fake_get_supabase_and_org)

    mock_showerror = lambda title, msg, parent: None
    monkeypatch.setattr("tkinter.messagebox.showerror", mock_showerror)

    fake_parent = types.SimpleNamespace()

    # Deve retornar 0, [(0, erro)] e NÃO lançar exceção
    ok, errs = lixeira_service.restore_clients([123], fake_parent)
    assert ok == 0
    assert len(errs) == 1
    assert errs[0][0] == 0
    assert "não autenticado" in errs[0][1]


def test_restore_clients_falha_sem_org_id(monkeypatch):
    """restore_clients captura RuntimeError quando organização não encontrada (linhas 36-39, 170-172)."""
    import types

    def fake_get_supabase_and_org():
        raise RuntimeError("Organização não encontrada para o usuário atual.")

    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", fake_get_supabase_and_org)

    mock_showerror = lambda title, msg, parent: None
    monkeypatch.setattr("tkinter.messagebox.showerror", mock_showerror)

    fake_parent = types.SimpleNamespace()

    ok, errs = lixeira_service.restore_clients([456], fake_parent)
    assert ok == 0
    assert len(errs) == 1
    assert "Organização não encontrada" in errs[0][1]


def test_hard_delete_clients_falha_excecao_generica(monkeypatch):
    """hard_delete_clients captura RuntimeError de _get_supabase_and_org e retorna erro (linhas 40-43, 170-172)."""
    import types

    def fake_get_supabase_and_org():
        raise RuntimeError("Falha ao obter usuário/organização: Network error")

    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", fake_get_supabase_and_org)

    mock_showerror = lambda title, msg, parent: None
    monkeypatch.setattr("tkinter.messagebox.showerror", mock_showerror)

    fake_parent = types.SimpleNamespace()

    ok, errs = lixeira_service.hard_delete_clients([789], fake_parent)
    assert ok == 0
    assert len(errs) == 1
    assert "Falha ao obter usuário/organização" in errs[0][1]


# --- Testes diretos de _get_supabase_and_org para cobrir linhas 28-43 ---


def test_get_supabase_and_org_sucesso_com_user_id(monkeypatch):
    """_get_supabase_and_org retorna (supabase, org_id) quando tudo está OK (linhas 28-43 happy path)."""
    import types

    # Mock do exec_postgrest para retornar org_id diretamente
    fake_org_response = types.SimpleNamespace(data=[{"org_id": "ORG456"}])

    # Patching exec_postgrest no módulo lixeira_service
    monkeypatch.setattr("src.core.services.lixeira_service.exec_postgrest", lambda q: fake_org_response)

    # Mock do supabase com user válido
    fake_user = types.SimpleNamespace(id="user123")
    fake_auth_response = types.SimpleNamespace(user=fake_user)
    fake_auth = types.SimpleNamespace(get_user=lambda: fake_auth_response)

    fake_table_builder = types.SimpleNamespace(
        select=lambda *a: types.SimpleNamespace(
            eq=lambda *a: types.SimpleNamespace(limit=lambda n: types.SimpleNamespace())
        ),
    )
    fake_supabase = types.SimpleNamespace(auth=fake_auth, table=lambda name: fake_table_builder)

    # Mock do módulo infra.supabase_client
    import sys

    fake_infra_module = types.ModuleType("infra.supabase_client")
    fake_infra_module.supabase = fake_supabase

    sys.modules["infra.supabase_client"] = fake_infra_module

    try:
        # Import a função depois do mock
        from src.core.services.lixeira_service import _get_supabase_and_org

        sb, org_id = _get_supabase_and_org()
        assert org_id == "ORG456"
    finally:
        # Cleanup
        if "infra.supabase_client" in sys.modules:
            del sys.modules["infra.supabase_client"]


def test_list_storage_children_ignora_items_nao_dict(monkeypatch):
    """_list_storage_children ignora itens que não são dicionários."""
    fake_items = [
        {"name": "file1.pdf", "metadata": {"size": 100}},
        "string_invalido",
        None,
        {"name": "file2.pdf", "metadata": None},
    ]

    monkeypatch.setattr(lixeira_service, "SupabaseStorageAdapter", lambda bucket: object())
    monkeypatch.setattr(lixeira_service, "using_storage_backend", lambda adapter: nullcontext())
    monkeypatch.setattr(lixeira_service, "storage_list_files", lambda prefix: fake_items)

    result = lixeira_service._list_storage_children("bucket", "prefix")  # type: ignore[protected-access]

    # Deve ignorar string e None, processar apenas dicts
    assert len(result) == 2
    assert result[0]["name"] == "file1.pdf"
    assert result[1]["name"] == "file2.pdf"


def test_gather_all_paths_ignora_objetos_sem_nome(monkeypatch):
    """_gather_all_paths ignora objetos sem campo 'name'."""

    def fake_list_children(bucket: str, prefix: str):
        if prefix == "root":
            return [
                {"name": "file1.pdf", "is_folder": False},
                {"is_folder": False},  # sem 'name'
                {"name": None, "is_folder": False},  # name=None
            ]
        return []

    monkeypatch.setattr(lixeira_service, "_list_storage_children", fake_list_children)

    paths = lixeira_service._gather_all_paths("bucket", "root")  # type: ignore[protected-access]

    # Deve processar apenas o primeiro objeto
    assert len(paths) == 1
    assert "root/file1.pdf" in paths


def test_remove_storage_prefix_retorna_zero_quando_vazio(monkeypatch):
    """_remove_storage_prefix retorna 0 quando não há arquivos."""
    monkeypatch.setattr(lixeira_service, "_gather_all_paths", lambda bucket, prefix: [])

    removed = lixeira_service._remove_storage_prefix("ORGID", 999)  # type: ignore[protected-access]

    assert removed == 0


def test_remove_storage_prefix_conta_apenas_deletes_bem_sucedidos(monkeypatch):
    """_remove_storage_prefix conta apenas arquivos deletados com sucesso."""
    monkeypatch.setattr(
        lixeira_service,
        "_gather_all_paths",
        lambda bucket, prefix: [f"{prefix}/file{i}.pdf" for i in range(5)],
    )
    monkeypatch.setattr(lixeira_service, "SupabaseStorageAdapter", lambda bucket: object())
    monkeypatch.setattr(lixeira_service, "using_storage_backend", lambda adapter: nullcontext())

    deleted = 0

    def fake_delete(key: str):
        nonlocal deleted
        # Simula sucesso apenas para arquivos pares
        if "file0" in key or "file2" in key or "file4" in key:
            deleted += 1
            return True
        return False

    monkeypatch.setattr(lixeira_service, "storage_delete_file", fake_delete)

    removed = lixeira_service._remove_storage_prefix("ORGID", 123)  # type: ignore[protected-access]

    assert removed == 3  # apenas file0, file2, file4


def test_ensure_mandatory_subfolders_falha_unlink_nao_quebra(monkeypatch):
    """Falha ao remover arquivo temporário não quebra _ensure_mandatory_subfolders."""
    mandatory = ("SIFAP",)
    uploads: list = []
    unlink_calls: list = []

    monkeypatch.setattr(lixeira_service, "get_mandatory_subpastas", lambda: mandatory)
    monkeypatch.setattr(lixeira_service, "using_storage_backend", lambda adapter: nullcontext())
    monkeypatch.setattr(lixeira_service, "SupabaseStorageAdapter", lambda bucket: object())
    monkeypatch.setattr(lixeira_service, "storage_list_files", lambda prefix: [])
    monkeypatch.setattr(lixeira_service, "storage_upload_file", lambda src, remote, ct=None: uploads.append(remote))

    def fake_unlink(path: str):
        unlink_calls.append(path)
        raise OSError("Arquivo em uso")

    monkeypatch.setattr(lixeira_service.os, "unlink", fake_unlink)

    # Não deve lançar exceção
    lixeira_service._ensure_mandatory_subfolders("ORG/999")  # type: ignore[protected-access]

    assert len(uploads) == 1
    assert len(unlink_calls) == 1  # tentou remover
