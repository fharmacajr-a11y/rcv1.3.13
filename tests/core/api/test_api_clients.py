from __future__ import annotations

import logging

import src.core.api.api_clients as api_clients

import src.core.services.upload_service as upload_service
import src.core.services.clientes_service as clientes_service


def test_switch_theme_calls_apply_theme(monkeypatch):
    calls: list[tuple[object, str]] = []

    def fake_apply_theme(root, *, theme):
        calls.append((root, theme))

    monkeypatch.setattr("src.utils.themes.apply_theme", fake_apply_theme)

    sentinel_root = object()
    api_clients.switch_theme(sentinel_root, "flatly")

    assert calls == [(sentinel_root, "flatly")]


def test_switch_theme_logs_warning_when_apply_theme_fails(monkeypatch, caplog):
    def fake_apply_theme(*_args, **_kwargs):
        raise RuntimeError("tk failed")

    monkeypatch.setattr("src.utils.themes.apply_theme", fake_apply_theme)
    caplog.set_level(logging.WARNING)

    api_clients.switch_theme(object(), "darkly")

    assert "Failed to apply theme 'darkly'" in caplog.text


def test_get_current_theme_returns_value_from_utils(monkeypatch):
    monkeypatch.setattr("src.utils.themes.load_theme", lambda: "darkly")

    assert api_clients.get_current_theme() == "darkly"


def test_get_current_theme_returns_default_on_exception(monkeypatch):
    def fake_load_theme():
        raise RuntimeError("prefs missing")

    monkeypatch.setattr("src.utils.themes.load_theme", fake_load_theme)

    assert api_clients.get_current_theme() == "flatly"


def test_upload_folder_returns_service_result(monkeypatch):
    expected = {"success": True, "uploaded_count": 4, "errors": []}

    def fake_upload(local_dir: str, *, org_id: str, client_id: str, subdir: str):
        assert local_dir == "/tmp/docs"
        assert org_id == "org-1"
        assert client_id == "42"
        assert subdir == "GERAL"
        return expected

    monkeypatch.setattr(upload_service, "upload_folder", fake_upload, raising=False)

    assert api_clients.upload_folder("/tmp/docs", "org-1", "42") == expected


def test_upload_folder_logs_and_returns_default_on_error(monkeypatch, caplog):
    def fake_upload(*_args, **_kwargs):
        raise RuntimeError("storage down")

    monkeypatch.setattr(upload_service, "upload_folder", fake_upload, raising=False)
    caplog.set_level(logging.ERROR)

    result = api_clients.upload_folder("/tmp/docs", "org-1", "42", subdir="DOCS")

    assert result == {"success": False, "uploaded_count": 0, "errors": ["storage down"]}
    assert "Folder upload failed" in caplog.text


def test_create_client_returns_id(monkeypatch):
    monkeypatch.setattr(clientes_service, "create_cliente", lambda data: "123", raising=False)

    assert api_clients.create_client({"nome": "ACME"}) == "123"


def test_create_client_logs_and_returns_none_on_error(monkeypatch, caplog):
    def fake_create(_data):
        raise RuntimeError("dup cnpj")

    monkeypatch.setattr(clientes_service, "create_cliente", fake_create, raising=False)
    caplog.set_level(logging.ERROR)

    assert api_clients.create_client({"nome": "ACME"}) is None
    assert "Create client failed" in caplog.text


def test_update_client_returns_true(monkeypatch):
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_update(client_id: str, data: dict[str, str]):
        calls.append((client_id, data))

    monkeypatch.setattr("src.core.services.clientes_service.update_cliente", fake_update)

    assert api_clients.update_client("42", {"nome": "New"}) is True
    assert calls == [("42", {"nome": "New"})]


def test_update_client_logs_and_returns_false_on_error(monkeypatch, caplog):
    def fake_update(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr("src.core.services.clientes_service.update_cliente", fake_update)
    caplog.set_level(logging.ERROR)

    assert api_clients.update_client("42", {"nome": "New"}) is False
    assert "Update client failed" in caplog.text


def test_delete_client_returns_true(monkeypatch):
    calls: list[tuple[str, bool]] = []

    def fake_delete(client_id: str, *, soft: bool):
        calls.append((client_id, soft))

    monkeypatch.setattr(clientes_service, "delete_cliente", fake_delete, raising=False)

    assert api_clients.delete_client("10", soft=False) is True
    assert calls == [("10", False)]


def test_delete_client_logs_and_returns_false_on_error(monkeypatch, caplog):
    def fake_delete(*_args, **_kwargs):
        raise RuntimeError("permission denied")

    monkeypatch.setattr(clientes_service, "delete_cliente", fake_delete, raising=False)
    caplog.set_level(logging.ERROR)

    assert api_clients.delete_client("10") is False
    assert "Delete client failed" in caplog.text


def test_search_clients_returns_payload(monkeypatch):
    dummy_clients = [object(), object()]
    monkeypatch.setattr("src.core.search.search_clientes", lambda q, *, org_id=None: dummy_clients)

    assert api_clients.search_clients("acme") == dummy_clients


def test_search_clients_logs_and_returns_empty_on_error(monkeypatch, caplog):
    def fake_search(*_args, **_kwargs):
        raise RuntimeError("timeout")

    monkeypatch.setattr("src.core.search.search_clientes", fake_search)
    caplog.set_level(logging.ERROR)

    assert api_clients.search_clients("acme", org_id="org-1") == []
    assert "Client search failed" in caplog.text
