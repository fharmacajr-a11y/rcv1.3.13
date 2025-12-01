from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.modules.uploads import repository


class FakeQuery:
    def __init__(self):
        self.eq_args: tuple[str, Any] | None = None
        self.update_payload: dict[str, Any] | None = None
        self.insert_payload: dict[str, Any] | None = None
        self.returning: str | None = None

    def select(self, *_: Any) -> "FakeQuery":
        return self

    def eq(self, field: str, value: Any) -> "FakeQuery":
        self.eq_args = (field, value)
        return self

    def limit(self, *_: Any) -> "FakeQuery":
        return self

    def insert(self, payload: dict[str, Any], *, returning: str | None = None) -> "FakeQuery":
        self.insert_payload = payload
        self.returning = returning
        return self

    def update(self, payload: dict[str, Any]) -> "FakeQuery":
        self.update_payload = payload
        return self


class FakeResponse:
    def __init__(self, data: list[dict[str, Any]] | None):
        self.data = data


def test_current_user_id_returns_from_object(monkeypatch):
    user = SimpleNamespace(id="user-123")
    fake_auth = SimpleNamespace(get_user=lambda: SimpleNamespace(user=user))
    fake_supabase = SimpleNamespace(auth=fake_auth)
    monkeypatch.setattr(repository, "supabase", fake_supabase)

    assert repository.current_user_id() == "user-123"


def test_current_user_id_returns_from_dict(monkeypatch):
    fake_auth = SimpleNamespace(get_user=lambda: {"user": {"id": "dict-user"}})
    fake_supabase = SimpleNamespace(auth=fake_auth)
    monkeypatch.setattr(repository, "supabase", fake_supabase)

    assert repository.current_user_id() == "dict-user"


def test_current_user_id_handles_exception(monkeypatch):
    class BrokenAuth:
        def get_user(self) -> None:
            raise RuntimeError("boom")

    fake_supabase = SimpleNamespace(auth=BrokenAuth())
    monkeypatch.setattr(repository, "supabase", fake_supabase)

    assert repository.current_user_id() is None


def test_current_user_id_returns_none_when_missing(monkeypatch):
    fake_auth = SimpleNamespace(get_user=lambda: SimpleNamespace(user=None))
    fake_supabase = SimpleNamespace(auth=fake_auth)
    monkeypatch.setattr(repository, "supabase", fake_supabase)

    assert repository.current_user_id() is None


def test_resolve_org_id_returns_membership(monkeypatch):
    fake_query = FakeQuery()
    fake_supabase = SimpleNamespace(table=lambda name: fake_query)
    monkeypatch.setattr(repository, "supabase", fake_supabase)
    monkeypatch.setattr(repository, "current_user_id", lambda: "user-1")

    def fake_exec(query: FakeQuery) -> FakeResponse:
        # Deve ter chamado eq("user_id", "user-1")
        assert query.eq_args == ("user_id", "user-1")
        return FakeResponse([{"org_id": "org-123"}])

    monkeypatch.setattr(repository, "exec_postgrest", fake_exec)
    assert repository.resolve_org_id() == "org-123"


def test_resolve_org_id_fallback_on_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "fallback-org")
    fake_supabase = SimpleNamespace(table=lambda name: FakeQuery())
    monkeypatch.setattr(repository, "supabase", fake_supabase)
    monkeypatch.setattr(repository, "current_user_id", lambda: "user-err")

    def raise_exec(*_: Any) -> None:
        raise RuntimeError("failure")

    monkeypatch.setattr(repository, "exec_postgrest", raise_exec)
    assert repository.resolve_org_id() == "fallback-org"


def test_resolve_org_id_without_user(monkeypatch):
    monkeypatch.delenv("SUPABASE_DEFAULT_ORG", raising=False)
    monkeypatch.setattr(repository, "current_user_id", lambda: None)
    assert repository.resolve_org_id() == "unknown-org"


def test_ensure_storage_object_absent_raises_on_dict_match(monkeypatch):
    monkeypatch.setattr(repository, "_storage_list_files", lambda prefix: [{"name": "file.txt", "full_path": ""}])
    with pytest.raises(RuntimeError):
        repository.ensure_storage_object_absent("folder/file.txt")


def test_ensure_storage_object_absent_raises_on_str_match(monkeypatch):
    monkeypatch.setattr(repository, "_storage_list_files", lambda prefix: ["folder/file.txt"])
    with pytest.raises(RuntimeError):
        repository.ensure_storage_object_absent("folder/file.txt")


def test_ensure_storage_object_absent_passes_when_no_conflict(monkeypatch):
    monkeypatch.setattr(repository, "_storage_list_files", lambda prefix: [{"name": "other.txt"}])
    repository.ensure_storage_object_absent("folder/file.txt")  # não deve levantar exceção


def test_upload_local_file_calls_adapter(monkeypatch):
    called = {}

    def fake_upload(local: str, path: str, mime: str) -> None:
        called["local"] = local
        called["path"] = path
        called["mime"] = mime

    monkeypatch.setattr(repository, "_storage_upload_file", fake_upload)

    repository.upload_local_file(Path("/tmp/a.txt"), "remote/a.txt", "text/plain")
    assert called == {
        "local": str(Path("/tmp/a.txt")),
        "path": "remote/a.txt",
        "mime": "text/plain",
    }


def test_insert_document_record_success(monkeypatch):
    fake_query = FakeQuery()
    fake_supabase = SimpleNamespace(table=lambda name: fake_query)
    monkeypatch.setattr(repository, "supabase", fake_supabase)

    def fake_exec(query: FakeQuery) -> FakeResponse:
        assert query.insert_payload["client_id"] == 10
        assert query.returning == "representation"
        return FakeResponse([{"ok": True, "id": 1}])

    monkeypatch.setattr(repository, "exec_postgrest", fake_exec)
    result = repository.insert_document_record(client_id=10, title="t", mime_type="application/pdf", user_id="u")
    assert result == {"ok": True, "id": 1}


def test_insert_document_record_raises_when_empty(monkeypatch):
    fake_query = FakeQuery()
    fake_supabase = SimpleNamespace(table=lambda name: fake_query)
    monkeypatch.setattr(repository, "supabase", fake_supabase)
    monkeypatch.setattr(repository, "exec_postgrest", lambda query: FakeResponse([]))

    with pytest.raises(RuntimeError):
        repository.insert_document_record(client_id=1, title="x", mime_type="pdf", user_id="u")


def test_insert_document_version_record_success(monkeypatch):
    fake_query = FakeQuery()
    fake_supabase = SimpleNamespace(table=lambda name: fake_query)
    monkeypatch.setattr(repository, "supabase", fake_supabase)

    def fake_exec(query: FakeQuery) -> FakeResponse:
        assert query.insert_payload["document_id"] == 5
        assert query.insert_payload["storage_path"] == "path"
        return FakeResponse([{"version": 1}])

    monkeypatch.setattr(repository, "exec_postgrest", fake_exec)
    result = repository.insert_document_version_record(
        document_id=5,
        storage_path="path",
        size_bytes=100,
        sha_value="abc",
        uploaded_by="user",
    )
    assert result == {"version": 1}


def test_insert_document_version_record_raises_when_empty(monkeypatch):
    fake_query = FakeQuery()
    fake_supabase = SimpleNamespace(table=lambda name: fake_query)
    monkeypatch.setattr(repository, "supabase", fake_supabase)
    monkeypatch.setattr(repository, "exec_postgrest", lambda query: FakeResponse([]))

    with pytest.raises(RuntimeError):
        repository.insert_document_version_record(
            document_id=1,
            storage_path="p",
            size_bytes=1,
            sha_value="s",
            uploaded_by="u",
        )


def test_update_document_current_version(monkeypatch):
    fake_query = FakeQuery()
    fake_supabase = SimpleNamespace(table=lambda name: fake_query)
    monkeypatch.setattr(repository, "supabase", fake_supabase)
    calls: list[FakeQuery] = []
    monkeypatch.setattr(repository, "exec_postgrest", lambda query: calls.append(query))

    repository.update_document_current_version(9, 3)

    assert calls and calls[0].update_payload == {"current_version": 3}
    assert calls[0].eq_args == ("id", 9)


def test_normalize_bucket_variations(monkeypatch):
    monkeypatch.setenv("SUPABASE_BUCKET", "  CUSTOM-BUCKET  ")
    assert repository.normalize_bucket(None) == "CUSTOM-BUCKET"
    assert repository.normalize_bucket("   other   ") == "other"
    monkeypatch.delenv("SUPABASE_BUCKET", raising=False)
    assert repository.normalize_bucket("") == "rc-docs"


def test_build_storage_adapter_uses_defaults(monkeypatch):
    created = {}

    class FakeAdapter:
        def __init__(self, *, client: Any, bucket: str, overwrite: bool) -> None:
            created["client"] = client
            created["bucket"] = bucket
            created["overwrite"] = overwrite

    monkeypatch.setattr(repository, "SupabaseStorageAdapter", FakeAdapter)
    monkeypatch.setattr(repository, "supabase", SimpleNamespace(name="default-sb"))

    adapter = repository.build_storage_adapter(bucket="my-bucket")
    assert created == {"client": SimpleNamespace(name="default-sb"), "bucket": "my-bucket", "overwrite": False}
    assert isinstance(adapter, FakeAdapter)


def test_build_storage_adapter_uses_custom_client(monkeypatch):
    created = {}

    class FakeAdapter:
        def __init__(self, *, client: Any, bucket: str, overwrite: bool) -> None:
            created["client"] = client
            created["bucket"] = bucket
            created["overwrite"] = overwrite

    custom_client = SimpleNamespace(name="custom")
    monkeypatch.setattr(repository, "SupabaseStorageAdapter", FakeAdapter)
    adapter = repository.build_storage_adapter(bucket="bucket", supabase_client=custom_client)
    assert created == {"client": custom_client, "bucket": "bucket", "overwrite": False}
    assert isinstance(adapter, FakeAdapter)


def test_upload_items_with_adapter_empty_list(monkeypatch):
    class DummyAdapter:
        def upload_file(self, *_: Any, **__: Any) -> None:
            raise AssertionError("Should not be called")

    ok, failures = repository.upload_items_with_adapter(
        adapter=DummyAdapter(),
        items=[],
        cnpj_digits="123",
        subfolder=None,
        progress_callback=None,
        remote_path_builder=lambda *args, **kwargs: "unused",
    )
    assert ok == 0
    assert failures == []


def test_upload_items_with_adapter_duplicate_error(monkeypatch):
    calls = []

    class DuplicateAdapter:
        def upload_file(self, local_path: str, remote_path: str, **kwargs: Any) -> None:
            calls.append((local_path, remote_path))
            raise RuntimeError("409 Conflict already exists")

    class FakeItem:
        def __init__(self, rel: str) -> None:
            self.relative_path = rel
            self.path = f"/tmp/{rel}"

    ok, failures = repository.upload_items_with_adapter(
        adapter=DuplicateAdapter(),
        items=[FakeItem("dup.txt")],
        cnpj_digits="999",
        subfolder="folder",
        progress_callback=None,
        remote_path_builder=lambda cnpj, rel, sub, **kwargs: f"{cnpj}/{sub}/{rel}",
    )

    assert ok == 0
    assert failures == []
    assert calls  # confirm upload was attempted
