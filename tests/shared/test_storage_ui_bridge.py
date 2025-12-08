from __future__ import annotations

import builtins
import importlib

import pytest

import src.shared.storage_ui_bridge as bridge


@pytest.fixture()
def warning_calls(monkeypatch):
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg: calls.append((title, msg)))
    return calls


def test_get_open_files_browser_handles_import_failure(monkeypatch):
    bridge.open_files_browser = None
    monkeypatch.setattr(bridge, "_OPEN_BROWSER_LOAD_FAILED", False)

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "src.modules.uploads":
            raise ImportError("forced failure")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert bridge._get_open_files_browser() is None
    assert bridge._OPEN_BROWSER_LOAD_FAILED is True

    # restaurar import normal para outros testes
    monkeypatch.setattr(builtins, "__import__", original_import)
    importlib.reload(bridge)


def test_get_clients_bucket_default_and_env(monkeypatch):
    monkeypatch.delenv("RC_STORAGE_BUCKET_CLIENTS", raising=False)
    assert bridge.get_clients_bucket() == "rc-docs"

    monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", " custom-bucket ")
    assert bridge.get_clients_bucket() == "custom-bucket"


def test_build_client_prefix_default_and_custom(monkeypatch):
    monkeypatch.delenv("RC_STORAGE_CLIENTS_FOLDER_FMT", raising=False)
    assert bridge.build_client_prefix(org_id="ORG", client_id=10) == "ORG/10"
    assert bridge.build_client_prefix(org_id="", client_id=10) == "10"

    monkeypatch.setenv("RC_STORAGE_CLIENTS_FOLDER_FMT", "{org_id}-x-{client_id}")
    assert bridge.build_client_prefix(org_id="ORG", client_id="abc") == "ORG-x-abc"


def test_client_prefix_for_id_delegates_to_builder(monkeypatch):
    monkeypatch.setenv("RC_STORAGE_CLIENTS_FOLDER_FMT", "{org_id}|{client_id}")
    assert bridge.client_prefix_for_id(5, "ORG") == "ORG|5"


class _Query:
    def __init__(self, data):
        self.data = data

    def select(self, *_, **__):
        return self

    def eq(self, *_, **__):
        return self

    def limit(self, *_, **__):
        return self

    def execute(self):
        return self


class _SB:
    def __init__(self, clients_data=None, users_data=None, user_present=True, raise_on_table=None):
        self._clients_data = clients_data
        self._users_data = users_data
        self._raise_on_table = raise_on_table
        self.auth = type(
            "Auth",
            (),
            {
                "get_user": (lambda self: type("U", (), {"user": type("UU", (), {"id": "uid"})()})())
                if user_present
                else (lambda self: None)
            },
        )()

    def table(self, name):
        if self._raise_on_table:
            raise self._raise_on_table
        if name == "clients":
            return _Query(self._clients_data)
        if name == "users":
            return _Query(self._users_data)
        raise ValueError(name)


def test_get_org_id_from_supabase_variants(monkeypatch):
    # success path
    sb = _SB(users_data=[{"org_id": "ORG123"}])
    assert bridge._get_org_id_from_supabase(sb) == "ORG123"

    # missing user
    sb_no_user = _SB(user_present=False)
    assert bridge._get_org_id_from_supabase(sb_no_user) is None

    # exception path
    sb_error = _SB(raise_on_table=RuntimeError("boom"))
    assert bridge._get_org_id_from_supabase(sb_error) is None


def test_client_title_fallbacks():
    row = {"razao_social": "Razao", "cnpj": "123"}
    assert bridge._client_title(row) == ("Razao", "123")

    fallback_row = {"id": 5, "tax_id": "tx"}
    assert bridge._client_title(fallback_row) == ("Cliente #5", "tx")


def test_open_client_files_window_offline(monkeypatch, warning_calls):
    bridge.open_client_files_window(parent=None, sb=None, client_id=1)
    assert warning_calls == [("Arquivos", "Modo offline.")]


def test_open_client_files_window_no_client(monkeypatch, warning_calls):
    sb = _SB(clients_data=[])
    bridge.open_client_files_window(parent=None, sb=sb, client_id=5)
    assert warning_calls == [("Arquivos", "Cliente #5 não encontrado.")]


def test_open_client_files_window_query_error(monkeypatch, warning_calls):
    sb = _SB(raise_on_table=RuntimeError("fail"))
    bridge.open_client_files_window(parent=None, sb=sb, client_id=7)
    assert "Não foi possível carregar o cliente #7" in warning_calls[0][1]


def test_open_client_files_window_success(monkeypatch, warning_calls):
    called = {}

    def fake_open(parent, org_id, client_id, razao, cnpj):
        called["args"] = (parent, org_id, client_id, razao, cnpj)

    monkeypatch.setattr(bridge, "open_files_browser", fake_open)
    sb = _SB(clients_data=[{"razao_social": "R", "cnpj": "C"}], users_data=[{"org_id": "ORG"}])

    bridge.open_client_files_window(parent="PARENT", sb=sb, client_id=9)

    assert called["args"] == ("PARENT", "ORG", 9, "R", "C")
    assert warning_calls == []


def test_open_client_files_window_open_error(monkeypatch, warning_calls):
    def fake_open(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(bridge, "open_files_browser", fake_open)
    sb = _SB(clients_data=[{"name": "N", "cnpj": ""}], users_data=[{"org_id": ""}])

    bridge.open_client_files_window(parent=None, sb=sb, client_id=2)

    assert warning_calls == [("Arquivos", "Falha ao abrir janela de arquivos.")]


def test_open_client_files_window_when_no_browser(monkeypatch, warning_calls):
    monkeypatch.setattr(bridge, "open_files_browser", None)
    monkeypatch.setattr(bridge, "_OPEN_BROWSER_LOAD_FAILED", True)
    sb = _SB(clients_data=[{"name": "N", "cnpj": ""}], users_data=[{"org_id": ""}])

    bridge.open_client_files_window(parent=None, sb=sb, client_id=3)

    assert warning_calls == [("Arquivos", "Falha ao abrir janela de arquivos.")]
