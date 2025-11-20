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
