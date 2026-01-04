from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.core.app_core as app_core
import src.modules.clientes.forms.client_form as cf


@pytest.fixture(autouse=True)
def reset_messagebox(monkeypatch):
    calls: list[tuple[str, tuple, dict]] = []

    def fake_safe(method: str, *args, **kwargs):
        calls.append((method, args, kwargs))
        # default behaviour for confirmation prompts: return True
        if method == "askyesno":
            return True
        return None

    monkeypatch.setattr(app_core, "_safe_messagebox", fake_safe)
    return calls


def test_novo_cliente_calls_form(monkeypatch):
    # Blindagem: verificar que estamos usando o módulo do repo atual
    cwd = Path(os.getcwd()).resolve()
    assert str(Path(cf.__file__).resolve()).startswith(str(cwd)), f"Módulo de versão errada: {cf.__file__}"

    called = []

    def fake_form_cliente(app, row=None):
        called.append((app, row))

    # Patch no objeto real importado (where to patch: onde app_core vai buscar em runtime)
    monkeypatch.setattr(cf, "form_cliente", fake_form_cliente, raising=True)

    app_core.novo_cliente("APP")

    assert called == [("APP", None)]


def test_editar_cliente_calls_form_when_row_found(monkeypatch):
    # Blindagem: verificar que estamos usando o módulo do repo atual
    cwd = Path(os.getcwd()).resolve()
    assert str(Path(cf.__file__).resolve()).startswith(str(cwd)), f"Módulo de versão errada: {cf.__file__}"

    called = []

    def fake_form_cliente(app, row=None):
        called.append((app, row))

    # Patch no objeto real importado (where to patch: onde app_core vai buscar em runtime)
    monkeypatch.setattr(cf, "form_cliente", fake_form_cliente, raising=True)
    monkeypatch.setattr(app_core, "_resolve_cliente_row", lambda pk: ("row", pk))

    app_core.editar_cliente("APP", 123)

    assert called == [("APP", ("row", 123))]


def test_editar_cliente_shows_error_when_row_missing(monkeypatch):
    monkeypatch.setattr(app_core, "_resolve_cliente_row", lambda pk: None)
    messages: list[str] = []

    def fake_safe(method: str, *args, **kwargs):
        messages.append(method)
        return None

    monkeypatch.setattr(app_core, "_safe_messagebox", fake_safe)
    app_core.editar_cliente("APP", 1)

    assert "showerror" in messages


def test_excluir_cliente_without_selection_shows_warning(monkeypatch):
    messages: list[str] = []

    def fake_safe(method: str, *args, **kwargs):
        messages.append(method)
        return None

    monkeypatch.setattr(app_core, "_safe_messagebox", fake_safe)
    app_core.excluir_cliente(SimpleNamespace(), [])

    assert messages == ["showwarning"]


def test_excluir_cliente_success_flow(monkeypatch):
    calls = {"move": [], "refresh": []}

    def fake_safe(method: str, *args, **kwargs):
        if method == "askyesno":
            return True
        calls.setdefault("messages", []).append(method)
        return None

    monkeypatch.setattr(app_core, "_safe_messagebox", fake_safe)
    monkeypatch.setattr(app_core, "mover_cliente_para_lixeira", lambda cid: calls["move"].append(cid))
    monkeypatch.setattr(app_core, "_module_refresh_if_open", lambda: calls["refresh"].append(True))

    app = SimpleNamespace(carregar=lambda: calls.setdefault("reload", []).append(True))
    app_core.excluir_cliente(app, ["10", "ACME"])

    assert calls["move"] == [10]
    assert calls["refresh"] == [True]
    assert calls["reload"] == [True]
    assert "showinfo" in calls.get("messages", [])


def test_excluir_cliente_aborts_when_user_declines(monkeypatch):
    moves = []

    def fake_safe(method: str, *args, **kwargs):
        if method == "askyesno":
            return False
        return None

    monkeypatch.setattr(app_core, "_safe_messagebox", fake_safe)
    monkeypatch.setattr(app_core, "mover_cliente_para_lixeira", lambda cid: moves.append(cid))

    app_core.excluir_cliente(SimpleNamespace(carregar=lambda: None), ["11", "ACME"])
    assert moves == []


def test_dir_base_cliente_returns_empty_when_no_fs(monkeypatch):
    monkeypatch.setattr(app_core, "NO_FS", True)
    assert app_core.dir_base_cliente_from_pk(1) == ""


def test_dir_base_cliente_uses_path_resolver(monkeypatch, tmp_path):
    monkeypatch.setattr(app_core, "NO_FS", False)
    module = SimpleNamespace(resolve_unique_path=lambda pk: (str(tmp_path / "client"), "local"))
    monkeypatch.setitem(sys.modules, "src.core.services.path_resolver", module)
    monkeypatch.setitem(sys.modules, "src.core.db_manager", SimpleNamespace(get_cliente_by_id=lambda pk: None))
    monkeypatch.setattr(app_core, "safe_base_from_fields", lambda *args, **kwargs: "base")
    monkeypatch.setattr(app_core, "DOCS_DIR", tmp_path)

    path = app_core.dir_base_cliente_from_pk(42)
    assert path == str(tmp_path / "client")


def test_abrir_lixeira_ui_utiliza_funcao_cacheada(monkeypatch):
    called = []

    def fake_open(parent, app_ctx, *args, **kwargs):
        called.append((parent, app_ctx, args, kwargs))
        return "window"

    monkeypatch.setattr(app_core, "_module_abrir_lixeira", fake_open, raising=False)
    app = SimpleNamespace(root="ROOT", app="CTX")

    app_core.abrir_lixeira_ui(app, 1, foo="bar")

    assert called == [("ROOT", "CTX", (1,), {"foo": "bar"})]
    assert getattr(app, "lixeira_win") == "window"
