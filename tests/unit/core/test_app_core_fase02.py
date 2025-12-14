# -*- coding: utf-8 -*-
"""Testes adicionais para src/app_core.py - Coverage Pack 01."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

import src.app_core as app_core


@pytest.fixture(autouse=True)
def reset_messagebox(monkeypatch):
    """Fixture para capturar chamadas de messagebox."""
    calls: list[tuple[str, tuple, dict]] = []

    def fake_safe(method: str, *args, **kwargs):
        calls.append((method, args, kwargs))
        if method == "askyesno":
            return True
        return None

    monkeypatch.setattr(app_core, "_safe_messagebox", fake_safe)
    return calls


# ==================== Testes de _resolve_cliente_row ====================


def test_resolve_cliente_row_returns_none_when_exception(monkeypatch):
    """Testa que _resolve_cliente_row retorna None quando get_cliente_by_id lança exceção."""
    monkeypatch.setattr(app_core, "get_cliente_by_id", lambda pk: (_ for _ in ()).throw(Exception("DB error")))

    result = app_core._resolve_cliente_row(123)

    assert result is None


def test_resolve_cliente_row_returns_none_when_cliente_none(monkeypatch):
    """Testa que _resolve_cliente_row retorna None quando cliente não encontrado."""
    monkeypatch.setattr(app_core, "get_cliente_by_id", lambda pk: None)

    result = app_core._resolve_cliente_row(123)

    assert result is None


def test_resolve_cliente_row_returns_tuple_when_cliente_found(monkeypatch):
    """Testa que _resolve_cliente_row retorna tupla correta quando cliente existe."""
    fake_cliente = SimpleNamespace(
        id=42,
        razao_social="ACME Corp",
        cnpj="12345678000190",
        nome="João Silva",
        numero="001",
        obs="Observações",
        ultima_alteracao="2025-01-01",
    )
    monkeypatch.setattr(app_core, "get_cliente_by_id", lambda pk: fake_cliente)

    result = app_core._resolve_cliente_row(42)

    assert result == (42, "ACME Corp", "12345678000190", "João Silva", "001", "Observações", "2025-01-01")


# ==================== Testes de excluir_cliente ====================


def test_excluir_cliente_handles_invalid_id_gracefully(monkeypatch, reset_messagebox):
    """Testa que excluir_cliente mostra erro quando ID é inválido."""
    app_core.excluir_cliente(SimpleNamespace(), ["invalid", "ACME"])

    assert any("showerror" in call[0] for call in reset_messagebox)


def test_excluir_cliente_handles_move_exception(monkeypatch, reset_messagebox):
    """Testa que excluir_cliente mostra erro quando mover_cliente_para_lixeira falha."""

    def fail_move(cid):
        raise Exception("Database error")

    monkeypatch.setattr(app_core, "mover_cliente_para_lixeira", fail_move)

    app = SimpleNamespace(carregar=lambda: None)
    app_core.excluir_cliente(app, ["10", "ACME"])

    assert any("showerror" in call[0] for call in reset_messagebox)


def test_excluir_cliente_handles_carregar_exception(monkeypatch, reset_messagebox):
    """Testa que excluir_cliente continua mesmo quando app.carregar() falha."""
    calls = {"move": []}

    def fail_reload():
        raise Exception("Reload error")

    monkeypatch.setattr(app_core, "mover_cliente_para_lixeira", lambda cid: calls["move"].append(cid))

    app = SimpleNamespace(carregar=fail_reload)
    app_core.excluir_cliente(app, ["10", "ACME"])

    assert calls["move"] == [10]
    assert any("showinfo" in call[0] for call in reset_messagebox)


def test_excluir_cliente_handles_refresh_exception(monkeypatch, reset_messagebox):
    """Testa que excluir_cliente continua mesmo quando refresh_if_open falha."""
    calls = {"move": []}

    def fail_refresh():
        raise Exception("Refresh error")

    monkeypatch.setattr(app_core, "mover_cliente_para_lixeira", lambda cid: calls["move"].append(cid))
    monkeypatch.setattr(app_core, "_module_refresh_if_open", fail_refresh)

    app = SimpleNamespace(carregar=lambda: None)
    app_core.excluir_cliente(app, ["10", "ACME"])

    assert calls["move"] == [10]


def test_excluir_cliente_with_empty_razao(monkeypatch, reset_messagebox):
    """Testa que excluir_cliente funciona quando razão social está vazia."""
    calls = {"move": []}

    monkeypatch.setattr(app_core, "mover_cliente_para_lixeira", lambda cid: calls["move"].append(cid))
    monkeypatch.setattr(app_core, "_module_refresh_if_open", None)

    app = SimpleNamespace(carregar=lambda: None)
    app_core.excluir_cliente(app, ["10"])

    assert calls["move"] == [10]


# ==================== Testes de dir_base_cliente_from_pk ====================


def test_dir_base_cliente_fallback_to_db_manager(monkeypatch, tmp_path):
    """Testa fallback para db_manager quando path_resolver não disponível."""
    monkeypatch.setattr(app_core, "NO_FS", False)

    # Simular path_resolver não disponível
    def fail_import(name):
        if name == "src.core.services.path_resolver":
            raise ImportError("Module not found")
        return sys.modules.get(name)

    fake_cliente = SimpleNamespace(numero="001", cnpj="12345678000190", razao_social="ACME")
    db_module = SimpleNamespace(get_cliente_by_id=lambda pk: fake_cliente)
    monkeypatch.setitem(sys.modules, "src.core.db_manager", db_module)
    monkeypatch.setattr(app_core, "safe_base_from_fields", lambda *args: "ACME-001")
    monkeypatch.setattr(app_core, "DOCS_DIR", tmp_path)

    path = app_core.dir_base_cliente_from_pk(42)

    assert path == str(tmp_path / "ACME-001")


def test_dir_base_cliente_fallback_to_pk_when_no_safe_base(monkeypatch, tmp_path):
    """Testa fallback para PK quando safe_base_from_fields não disponível."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "safe_base_from_fields", None)
    monkeypatch.setattr(app_core, "DOCS_DIR", tmp_path)

    db_module = SimpleNamespace(get_cliente_by_id=lambda pk: None)
    monkeypatch.setitem(sys.modules, "src.core.db_manager", db_module)

    path = app_core.dir_base_cliente_from_pk(42)

    assert path == str(tmp_path / "42")


# ==================== Testes de _ensure_live_folder_ready ====================


def test_ensure_live_folder_ready_returns_empty_when_no_fs(monkeypatch):
    """Testa que _ensure_live_folder_ready retorna vazio quando NO_FS ativo."""
    monkeypatch.setattr(app_core, "NO_FS", True)

    result = app_core._ensure_live_folder_ready(42)

    assert result == ""


def test_ensure_live_folder_ready_handles_makedirs_exception(monkeypatch, tmp_path):
    """Testa que _ensure_live_folder_ready continua mesmo quando makedirs falha."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", False)
    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(tmp_path / "test"))

    def fail_makedirs(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(app_core.os, "makedirs", fail_makedirs)

    # Não deve lançar exceção
    result = app_core._ensure_live_folder_ready(42)
    assert result == str(tmp_path / "test")


# ==================== Testes de abrir_pasta ====================


def test_abrir_pasta_shows_info_when_no_fs(monkeypatch, reset_messagebox):
    """Testa que abrir_pasta mostra info quando NO_FS está ativo."""
    monkeypatch.setattr(app_core, "NO_FS", True)

    app_core.abrir_pasta(SimpleNamespace(), 42)

    assert any("showinfo" in call[0] for call in reset_messagebox)


def test_abrir_pasta_handles_startfile_exception(monkeypatch, tmp_path):
    """Testa que abrir_pasta lida com exceção de os.startfile."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "_ensure_live_folder_ready", lambda pk: str(tmp_path))

    helpers_module = SimpleNamespace(check_cloud_only_block=lambda msg: False)
    monkeypatch.setitem(sys.modules, "src.utils.helpers", helpers_module)

    def fail_startfile(path):
        raise OSError("No application found")

    monkeypatch.setattr(app_core.os, "startfile", fail_startfile, raising=False)

    # Não deve lançar exceção
    app_core.abrir_pasta(SimpleNamespace(), 42)


def test_abrir_pasta_respects_cloud_only_block(monkeypatch, tmp_path):
    """Testa que abrir_pasta respeita check_cloud_only_block."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "_ensure_live_folder_ready", lambda pk: str(tmp_path))

    helpers_module = SimpleNamespace(check_cloud_only_block=lambda msg: True)
    monkeypatch.setitem(sys.modules, "src.utils.helpers", helpers_module)

    startfile_calls = []
    monkeypatch.setattr(app_core.os, "startfile", lambda p: startfile_calls.append(p), raising=False)

    app_core.abrir_pasta(SimpleNamespace(), 42)

    # startfile não deve ser chamado
    assert startfile_calls == []


# ==================== Testes de open_client_local_subfolders ====================


def test_open_client_local_subfolders_shows_info_when_no_fs(monkeypatch, reset_messagebox):
    """Testa que open_client_local_subfolders mostra info quando NO_FS está ativo."""
    monkeypatch.setattr(app_core, "NO_FS", True)

    app_core.open_client_local_subfolders(SimpleNamespace(), 42)

    assert any("showinfo" in call[0] for call in reset_messagebox)


def test_open_client_local_subfolders_handles_config_load_exception(monkeypatch, tmp_path):
    """Testa que open_client_local_subfolders usa listas vazias quando load_subpastas_config falha."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "_ensure_live_folder_ready", lambda pk: str(tmp_path))

    dialog_calls = []

    def fake_dialog(app, path, subpastas, extras):
        dialog_calls.append((app, path, subpastas, extras))

    # O código real importa de src.modules.clientes.forms, não de src.ui.subpastas.dialog
    forms_module = SimpleNamespace(open_subpastas_dialog=fake_dialog)
    monkeypatch.setitem(sys.modules, "src.modules.clientes.forms", forms_module)

    config_module = SimpleNamespace(load_subpastas_config=lambda: (_ for _ in ()).throw(Exception("Config error")))
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    app_core.open_client_local_subfolders(SimpleNamespace(), 42)

    # Deve usar listas vazias
    assert dialog_calls[0][2] == []
    assert dialog_calls[0][3] == []


def test_ver_subpastas_alias_calls_new_function(monkeypatch):
    """Garante que o wrapper legacy delega para open_client_local_subfolders."""
    called = {}

    def fake_open(app, pk):
        called["args"] = (app, pk)

    monkeypatch.setattr(app_core, "open_client_local_subfolders", fake_open)

    app_core.ver_subpastas("APP", 7)

    assert called["args"] == ("APP", 7)


# ==================== Testes de abrir_lixeira_ui ====================


def test_abrir_lixeira_ui_with_primary_import(monkeypatch):
    """Testa abrir_lixeira_ui com import primário de src.modules.lixeira.views.lixeira."""
    # Limpar o _module_abrir_lixeira cache para forçar import dinâmico
    monkeypatch.setattr(app_core, "_module_abrir_lixeira", None)

    called = []

    def fake_open(parent, app_ctx, *args, **kwargs):
        called.append((parent, app_ctx))
        return "window"

    # O código primeiro tenta src.modules.lixeira.views.lixeira.abrir_lixeira
    lixeira_views_module = SimpleNamespace(abrir_lixeira=fake_open)
    monkeypatch.setitem(sys.modules, "src.modules.lixeira.views.lixeira", lixeira_views_module)

    app = SimpleNamespace(root="ROOT", app="CTX")
    app_core.abrir_lixeira_ui(app)

    assert called == [("ROOT", "CTX")]


def test_abrir_lixeira_ui_handles_setattr_exception(monkeypatch):
    """Testa que abrir_lixeira_ui continua mesmo quando setattr falha."""
    called = []

    def fake_open(parent, app_ctx, *args, **kwargs):
        called.append(True)
        return "window"

    monkeypatch.setattr(app_core, "_module_abrir_lixeira", fake_open)

    # App que lança exceção ao tentar setattr
    class BadApp:
        root = "ROOT"
        app = "CTX"

        def __setattr__(self, name, value):
            if name == "lixeira_win":
                raise RuntimeError("Cannot set attribute")
            super().__setattr__(name, value)

    app = BadApp()

    # Não deve lançar exceção
    app_core.abrir_lixeira_ui(app)
    assert called == [True]
    assert called == [True]


# ==================== Testes de abrir_pasta_cliente ====================


def test_abrir_pasta_cliente_returns_none_when_no_fs(monkeypatch):
    """Testa que abrir_pasta_cliente retorna None quando NO_FS está ativo."""
    monkeypatch.setattr(app_core, "NO_FS", True)

    result = app_core.abrir_pasta_cliente(42)

    assert result is None


def test_abrir_pasta_cliente_returns_path_when_fs_enabled(monkeypatch, tmp_path):
    """Testa que abrir_pasta_cliente retorna path quando NO_FS está desativado."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "_ensure_live_folder_ready", lambda pk: str(tmp_path / "client"))

    result = app_core.abrir_pasta_cliente(42)

    assert result == str(tmp_path / "client")
