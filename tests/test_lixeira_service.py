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
    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (_ for _ in ()).throw(RuntimeError("falha qualquer")))
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

    monkeypatch.setattr(
        lixeira_service,
        "_get_supabase_and_org",
        lambda: (types.SimpleNamespace(table=lambda name: DummyTable(name)), "ORGID"),
    )
    monkeypatch.setattr(lixeira_service, "_remove_storage_prefix", lambda org_id, cid: removes.append((org_id, cid)) or 3)
    monkeypatch.setattr(lixeira_service, "exec_postgrest", lambda *a, **k: deletions.append(a[0]))
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.hard_delete_clients([20, 21], parent=None)

    assert ok == 2
    assert errs == []
    assert removes == [("ORGID", 20), ("ORGID", 21)]
    assert len(deletions) == 2


def test_hard_delete_clients_erros_sao_coletados(monkeypatch):
    monkeypatch.setattr(lixeira_service, "_get_supabase_and_org", lambda: (types.SimpleNamespace(table=lambda name: DummyTable(name)), "ORGID"))

    def fake_remove(org_id, cid):
        if cid == 30:
            raise RuntimeError("fail remove")
        return 1

    deletes: list[int] = []

    def fake_exec(expr):
        deletes.append(expr)
        if len(deletes) > 1:
            raise RuntimeError("db fail")

    monkeypatch.setattr(lixeira_service, "_remove_storage_prefix", fake_remove)
    monkeypatch.setattr(lixeira_service, "exec_postgrest", fake_exec)
    monkeypatch.setattr(lixeira_service.messagebox, "showerror", lambda *a, **k: None)

    ok, errs = lixeira_service.hard_delete_clients([30, 31], parent=None)

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
