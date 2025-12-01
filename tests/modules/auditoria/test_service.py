from __future__ import annotations

from pathlib import Path

import pytest

import src.modules.auditoria.service as service


class DummySupabase:
    def __init__(self, data=None, user_id="uid"):
        self._data = data or []
        self.auth = type(
            "Auth", (), {"get_user": lambda self: type("U", (), {"user": type("Usr", (), {"id": user_id})()})()}
        )()
        self.calls = []

    class Table:
        def __init__(self, data):
            self.data = data
            self.calls = []

        def select(self, *args, **kwargs):
            self.calls.append(("select", args, kwargs))
            return self

        def order(self, *args, **kwargs):
            self.calls.append(("order", args, kwargs))
            return self

        def execute(self):
            return self

        def insert(self, payload):
            self.calls.append(("insert", payload))
            return self

        def update(self, payload):
            self.calls.append(("update", payload))
            return self

        def eq(self, *args, **kwargs):
            self.calls.append(("eq", args, kwargs))
            return self

        def delete(self):
            self.calls.append(("delete",))
            return self

        def in_(self, *args, **kwargs):
            self.calls.append(("in", args, kwargs))
            return self

        def limit(self, *args, **kwargs):
            self.calls.append(("limit", args, kwargs))
            return self

    def table(self, name):
        self.calls.append(("table", name))
        return self.Table(self._data)


def test_require_supabase_and_is_online(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: None)
    with pytest.raises(service.AuditoriaOfflineError):
        service._require_supabase()

    sb = object()
    monkeypatch.setattr(service, "get_supabase", lambda: sb)
    assert service.get_supabase_client() is sb
    assert service.is_online() is True


def test_fetch_clients_success(monkeypatch):
    sb = DummySupabase()
    called = {}
    monkeypatch.setattr(service, "get_supabase", lambda: sb)

    def fetch_stub(s):
        called["sb"] = s
        return [{"id": 1}]

    monkeypatch.setattr(service.repository, "fetch_clients", fetch_stub)
    assert service.fetch_clients() == [{"id": 1}]
    assert called["sb"] is sb


def test_list_clients_minimal(monkeypatch):
    monkeypatch.setattr(service, "fetch_clients", lambda: ["x"])
    assert service.list_clients_minimal() == ["x"]


def test_fetch_clients_error(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(service.repository, "fetch_clients", lambda sb: (_ for _ in ()).throw(RuntimeError("fail")))
    with pytest.raises(service.AuditoriaServiceError, match="Falha ao carregar clientes"):
        service.fetch_clients()


def test_fetch_auditorias_and_list(monkeypatch):
    sb = DummySupabase()
    monkeypatch.setattr(service, "get_supabase", lambda: sb)
    monkeypatch.setattr(service.repository, "fetch_auditorias", lambda s: [{"id": 2}])
    assert service.fetch_auditorias() == [{"id": 2}]
    assert service.list_auditorias() == [{"id": 2}]


def test_fetch_auditorias_error(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(service.repository, "fetch_auditorias", lambda sb: (_ for _ in ()).throw(RuntimeError("err")))
    with pytest.raises(service.AuditoriaServiceError, match="Falha ao carregar auditorias"):
        service.fetch_auditorias()


def test_start_auditoria_success(monkeypatch):
    sb = DummySupabase()
    monkeypatch.setattr(service, "get_supabase", lambda: sb)
    payloads = {}

    def insert(sb_arg, payload):
        payloads["payload"] = payload
        return type("R", (), {"data": [{"id": "new"}]})()

    monkeypatch.setattr(service.repository, "insert_auditoria", insert)
    assert service.start_auditoria(5, status="ok") == {"id": "new"}
    assert payloads["payload"]["cliente_id"] == 5
    assert payloads["payload"]["status"] == "ok"


def test_start_auditoria_no_data(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(service.repository, "insert_auditoria", lambda sb, payload: type("R", (), {"data": []})())
    with pytest.raises(service.AuditoriaServiceError, match="nao retornou dados"):
        service.start_auditoria(1)


def test_start_auditoria_repo_error(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(
        service.repository, "insert_auditoria", lambda sb, payload: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="Nao foi possivel iniciar auditoria"):
        service.start_auditoria(1)


def test_update_auditoria_status_success(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(
        service.repository, "update_auditoria", lambda sb, aid, status: type("R", (), {"data": [{"status": status}]})()
    )
    assert service.update_auditoria_status("aid", "done")["status"] == "done"


def test_update_auditoria_status_no_data(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(service.repository, "update_auditoria", lambda sb, aid, status: type("R", (), {"data": []})())
    with pytest.raises(service.AuditoriaServiceError, match="nao encontrada"):
        service.update_auditoria_status("aid", "done")


def test_update_auditoria_status_repo_error(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(
        service.repository, "update_auditoria", lambda sb, aid, status: (_ for _ in ()).throw(RuntimeError("oops"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="Nao foi possivel atualizar status"):
        service.update_auditoria_status("aid", "done")


def test_delete_auditorias_filters_ids(monkeypatch):
    received = {}
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(service.repository, "delete_auditorias", lambda sb, ids: received.setdefault("ids", ids))
    service.delete_auditorias([None, "", "  ", "1", 2])
    assert received["ids"] == ["1", "2"]


def test_delete_auditorias_empty_no_call(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(
        service.repository, "delete_auditorias", lambda sb, ids: called.__setitem__("n", called["n"] + 1)
    )
    service.delete_auditorias([None, ""])
    assert called["n"] == 0


def test_delete_auditorias_error(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(
        service.repository, "delete_auditorias", lambda sb, ids: (_ for _ in ()).throw(RuntimeError("fail"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="Falha ao excluir"):
        service.delete_auditorias(["1"])


def test_get_current_org_id_cache_and_refresh(monkeypatch):
    service.reset_org_cache()
    sb = DummySupabase()
    monkeypatch.setattr(service, "get_supabase", lambda: sb)
    monkeypatch.setattr(service.repository, "fetch_current_user_id", lambda sb_arg: "user1")
    monkeypatch.setattr(service.repository, "fetch_org_id_for_user", lambda sb_arg, uid: f"ORG-{uid}")
    assert service.get_current_org_id() == "ORG-user1"
    # cached
    monkeypatch.setattr(service.repository, "fetch_org_id_for_user", lambda sb_arg, uid: "DIFF")
    assert service.get_current_org_id() == "ORG-user1"
    assert service.get_current_org_id(force_refresh=True) == "DIFF"


def test_get_current_org_id_lookup_error(monkeypatch):
    service.reset_org_cache()
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(service.repository, "fetch_current_user_id", lambda sb: "u")
    monkeypatch.setattr(
        service.repository, "fetch_org_id_for_user", lambda sb, uid: (_ for _ in ()).throw(LookupError("msg"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="msg"):
        service.get_current_org_id()


def test_get_current_org_id_generic_error(monkeypatch):
    service.reset_org_cache()
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(service.repository, "fetch_current_user_id", lambda sb: "u")
    monkeypatch.setattr(
        service.repository, "fetch_org_id_for_user", lambda sb, uid: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="Nao foi possivel"):
        service.get_current_org_id()


def test_storage_wrappers(monkeypatch):
    sb = DummySupabase()
    monkeypatch.setattr(service, "get_supabase", lambda: sb)
    called = {}
    monkeypatch.setattr(service.storage, "ensure_auditoria_folder", lambda sb_arg, ctx: called.update(ctx=ctx))
    ctx = service.AuditoriaStorageContext(bucket="b", org_id="o", client_root="root", auditoria_prefix="p")
    monkeypatch.setattr(service, "get_storage_context", lambda client_id, org_id=None: ctx)
    service.ensure_auditoria_folder(1, org_id="o")
    assert called["ctx"] == ctx

    monkeypatch.setattr(service.storage, "list_existing_file_names", lambda *args, **kwargs: {"a"})
    assert service.list_existing_file_names("b", "p") == {"a"}

    up_calls = {}
    monkeypatch.setattr(
        service.storage,
        "upload_storage_bytes",
        lambda sb_arg, bucket, dest, data, content_type, upsert, cache_control: up_calls.update(
            bucket=bucket, dest=dest, data=data, content_type=content_type, upsert=upsert, cache_control=cache_control
        ),
    )
    service.upload_storage_bytes("b", "path", b"data", content_type="ct", upsert=True, cache_control="0")
    assert up_calls["bucket"] == "b"

    rm_calls = {}
    monkeypatch.setattr(
        service.storage,
        "remove_storage_objects",
        lambda sb_arg, bucket, paths: rm_calls.update(bucket=bucket, paths=paths),
    )
    service.remove_storage_objects("b", ["x"])
    assert rm_calls["paths"] == ["x"]


def test_storage_wrappers_errors(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: DummySupabase())
    monkeypatch.setattr(
        service.storage, "ensure_auditoria_folder", lambda sb, ctx: (_ for _ in ()).throw(RuntimeError("err"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="Falha ao criar"):
        service.ensure_auditoria_folder(1, org_id="o")

    monkeypatch.setattr(
        service.storage, "list_existing_file_names", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("err"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="Falha ao listar"):
        service.list_existing_file_names("b", "p")

    monkeypatch.setattr(
        service.storage, "upload_storage_bytes", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("err"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="Falha ao enviar"):
        service.upload_storage_bytes("b", "p", b"x", content_type="ct")

    monkeypatch.setattr(
        service.storage, "remove_storage_objects", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("err"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="Falha ao remover"):
        service.remove_storage_objects("b", ["x"])


def test_remove_storage_objects_no_paths(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(
        service.storage, "remove_storage_objects", lambda *args, **kwargs: called.__setitem__("n", called["n"] + 1)
    )
    service.remove_storage_objects("b", [])
    assert called["n"] == 0


def test_ensure_storage_ready(monkeypatch):
    monkeypatch.setattr(service, "is_online", lambda: False)
    with pytest.raises(service.AuditoriaOfflineError):
        service.ensure_storage_ready()
    monkeypatch.setattr(service, "is_online", lambda: True)
    monkeypatch.setattr(service, "get_clients_bucket", lambda: "")
    with pytest.raises(service.AuditoriaServiceError, match="Defina RC_STORAGE_BUCKET_CLIENTS"):
        service.ensure_storage_ready()
    monkeypatch.setattr(service, "get_clients_bucket", lambda: "bucket")
    service.ensure_storage_ready()


def test_prepare_archive_plan_and_execute(monkeypatch):
    plan_obj = object()
    monkeypatch.setattr(service.archives, "prepare_archive_plan", lambda path, extract_func: plan_obj)
    assert service.prepare_archive_plan("file.zip") is plan_obj
    monkeypatch.setattr(
        service.archives, "prepare_archive_plan", lambda path, extract_func: (_ for _ in ()).throw(ValueError("bad"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="bad"):
        service.prepare_archive_plan("x")

    monkeypatch.setattr(service.archives, "cleanup_archive_plan", lambda plan: setattr(plan_holder, "clean", True))
    plan_holder = type("P", (), {})()
    service.cleanup_archive_plan(plan_holder)
    assert getattr(plan_holder, "clean", False) is True


def test_execute_archive_upload(monkeypatch):
    plan = object()
    ctx = service.AuditoriaUploadContext(bucket="b", base_prefix="p", org_id="o", client_id=1)
    monkeypatch.setattr(service.archives, "execute_archive_upload", lambda *args, **kwargs: "ok")
    assert (
        service.execute_archive_upload(
            plan, ctx, strategy="skip", existing_names=set(), duplicates=set(), cancel_check=None
        )
        == "ok"
    )
    monkeypatch.setattr(
        service.archives, "execute_archive_upload", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("dup"))
    )
    with pytest.raises(service.AuditoriaServiceError, match="dup"):
        service.execute_archive_upload(plan, ctx, strategy="skip", existing_names=set(), duplicates=set())


def test_prepare_upload_and_duplicates(monkeypatch):
    storage_ctx = service.AuditoriaStorageContext(bucket="b", org_id="o", client_root="root", auditoria_prefix="p")
    monkeypatch.setattr(service, "get_storage_context", lambda client_id, org_id=None: storage_ctx)
    upload_ctx = service.prepare_upload_context(1, org_id="o")
    assert upload_ctx.bucket == "b"
    assert upload_ctx.base_prefix == "p"
    assert upload_ctx.org_id == "o"
    assert upload_ctx.client_id == 1
    assert service.get_storage_context(1, org_id="o") == storage_ctx
    assert service.list_existing_names_for_context(upload_ctx) == set()

    monkeypatch.setattr(service.storage, "get_clients_bucket", lambda: "bucket")
    assert service.get_clients_bucket() == "bucket"

    monkeypatch.setattr(service.storage, "build_client_prefix", lambda cid, org: f"{org}/{cid}")
    assert service.build_client_prefix(1, "ORG") == "ORG/1"

    monkeypatch.setattr(service.archives, "detect_duplicate_file_names", lambda plan, names: {"dup"})
    assert service.detect_duplicate_file_names(plan=None, existing_names=set()) == {"dup"}

    monkeypatch.setattr(service.archives, "extract_archive_to", lambda src, dst: Path(dst) / "out")
    assert service.extract_archive_to("a", "b") == Path("b") / "out"

    monkeypatch.setattr(service.archives, "is_supported_archive", lambda path: True)
    assert service.is_supported_archive("file.zip") is True


def test_rollback_uploaded_paths(monkeypatch):
    called = {}
    monkeypatch.setattr(
        service, "remove_storage_objects", lambda bucket, paths: called.update(bucket=bucket, paths=paths)
    )
    ctx = service.AuditoriaUploadContext(bucket="b", base_prefix="p", org_id="o", client_id=1)
    service.rollback_uploaded_paths(ctx, ["a", "b"])
    assert called["paths"] == ["a", "b"]


def test_get_supabase_client_error(monkeypatch):
    monkeypatch.setattr(service, "get_supabase", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    assert service._get_supabase_client() is None
