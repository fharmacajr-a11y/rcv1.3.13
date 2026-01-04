from __future__ import annotations

import logging

import src.core.api.api_notes as api_notes
import src.core.services.lixeira_service as lixeira_service


def test_list_storage_files_returns_backend_payload(monkeypatch):
    captured: list[tuple[str, str]] = []

    def fake_list(bucket: str, prefix: str):
        captured.append((bucket, prefix))
        return [{"name": "client-file.pdf", "size": 1024}]

    monkeypatch.setattr("src.adapters.storage.api.list_files", fake_list)

    result = api_notes.list_storage_files("clients", "org-123/")

    assert result == [{"name": "client-file.pdf", "size": 1024}]
    assert captured == [("clients", "org-123/")]


def test_list_storage_files_logs_and_returns_empty_on_failure(monkeypatch, caplog):
    def fake_list(*_args, **_kwargs):
        raise RuntimeError("storage offline")

    monkeypatch.setattr("src.adapters.storage.api.list_files", fake_list)
    caplog.set_level(logging.ERROR)

    assert api_notes.list_storage_files("clients", "org-404/") == []
    assert "List files failed for org-404/" in caplog.text


def test_list_trash_clients_returns_payload(monkeypatch):
    expected = [{"id": "c1"}, {"id": "c2"}]

    def fake_list(org_id: str):
        assert org_id == "org-abc"
        return expected

    monkeypatch.setattr(lixeira_service, "list_trash_clients", fake_list, raising=False)

    assert api_notes.list_trash_clients("org-abc") == expected


def test_list_trash_clients_logs_and_returns_empty_on_error(monkeypatch, caplog):
    def fake_list(org_id: str):
        raise ValueError(f"unknown org {org_id}")

    monkeypatch.setattr(lixeira_service, "list_trash_clients", fake_list, raising=False)
    caplog.set_level(logging.ERROR)

    assert api_notes.list_trash_clients("org-def") == []
    assert "List trash clients failed" in caplog.text


def test_restore_from_trash_returns_true_when_service_succeeds(monkeypatch):
    captured: list[tuple[str, list[str]]] = []

    def fake_restore(org_id: str, client_ids: list[str]):
        captured.append((org_id, list(client_ids)))

    monkeypatch.setattr("src.core.services.lixeira_service.restore_clients", fake_restore)

    assert api_notes.restore_from_trash("org-1", ["c1", "c2"]) is True
    assert captured == [("org-1", ["c1", "c2"])]


def test_restore_from_trash_logs_and_returns_false_on_error(monkeypatch, caplog):
    def fake_restore(*_args, **_kwargs):
        raise RuntimeError("db offline")

    monkeypatch.setattr("src.core.services.lixeira_service.restore_clients", fake_restore)
    caplog.set_level(logging.ERROR)

    assert api_notes.restore_from_trash("org-1", ["c1"]) is False
    assert "Restore from trash failed" in caplog.text


def test_purge_from_trash_returns_true_when_service_succeeds(monkeypatch):
    captured: list[tuple[str, list[str]]] = []

    def fake_purge(org_id: str, client_ids: list[str]):
        captured.append((org_id, list(client_ids)))

    monkeypatch.setattr(lixeira_service, "purge_clients", fake_purge, raising=False)

    assert api_notes.purge_from_trash("org-1", ["c1"]) is True
    assert captured == [("org-1", ["c1"])]


def test_purge_from_trash_logs_and_returns_false_on_error(monkeypatch, caplog):
    def fake_purge(*_args, **_kwargs):
        raise RuntimeError("deletion blocked")

    monkeypatch.setattr(lixeira_service, "purge_clients", fake_purge, raising=False)
    caplog.set_level(logging.ERROR)

    assert api_notes.purge_from_trash("org-1", ["c1"]) is False
    assert "Purge from trash failed" in caplog.text


def test_resolve_asset_returns_value_from_resource_path(monkeypatch):
    def fake_resource_path(asset_name: str) -> str:
        return f"/tmp/assets/{asset_name}"

    monkeypatch.setattr("src.utils.resource_path.resource_path", fake_resource_path)

    assert api_notes.resolve_asset("rc.ico") == "/tmp/assets/rc.ico"


def test_resolve_asset_falls_back_to_asset_name_on_exception(monkeypatch):
    def fake_resource_path(_asset_name: str) -> str:
        raise FileNotFoundError("missing")

    monkeypatch.setattr("src.utils.resource_path.resource_path", fake_resource_path)

    assert api_notes.resolve_asset("logo.png") == "logo.png"
