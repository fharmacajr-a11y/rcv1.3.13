# -*- coding: utf-8 -*-
"""Testes adicionais para src/app_core.py - Microfase 3 (Coverage Pack 02).

Foco em:
- Cobertura dos branches de import fallback
- Exception handling em _safe_messagebox
- Exception handling em _ensure_live_folder_ready (subpastas, marker)
- Exception handling em excluir_cliente (razão social)
- Fallback de abrir_lixeira_ui com importlib
- CLOUD_ONLY branches
"""

from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path
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


# ==================== Testes de _safe_messagebox (linhas 48-54) ====================


def test_safe_messagebox_handles_exception_in_messagebox(monkeypatch):
    """Testa que _safe_messagebox captura exceção ao chamar messagebox."""
    # Restaurar comportamento real para testar a exception handling
    monkeypatch.undo()

    def fail_messagebox(*args, **kwargs):
        raise RuntimeError("GUI error")

    # Mock do módulo messagebox
    messagebox_module = SimpleNamespace(showerror=fail_messagebox)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox_module)
    monkeypatch.setattr(app_core.messagebox, "showerror", fail_messagebox)

    # Não deve lançar exceção
    result = app_core._safe_messagebox("showerror", "Title", "Message")
    assert result is None


def test_safe_messagebox_returns_none_when_method_not_callable(monkeypatch):
    """Testa que _safe_messagebox retorna None quando método não existe."""
    # Restaurar comportamento real
    monkeypatch.undo()

    # Mock do messagebox sem o método
    messagebox_module = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox_module)
    monkeypatch.setattr(app_core, "messagebox", messagebox_module)

    result = app_core._safe_messagebox("nonexistent", "Title", "Message")
    assert result is None


# ==================== Testes de excluir_cliente - razão social exception (linhas 120-121) ====================


def test_excluir_cliente_handles_razao_extraction_exception(monkeypatch, reset_messagebox):
    """Testa que excluir_cliente lida com exceção ao extrair razão social."""
    calls = {"move": []}

    # selected_values com objeto que não permite conversão para string
    class BadString:
        def __str__(self):
            raise TypeError("Cannot convert to string")

        def strip(self):
            raise AttributeError("Cannot strip")

    monkeypatch.setattr(app_core, "mover_cliente_para_lixeira", lambda cid: calls["move"].append(cid))
    monkeypatch.setattr(app_core, "_module_refresh_if_open", None)

    app = SimpleNamespace(carregar=lambda: None)
    # ID válido, mas razão social problemática
    app_core.excluir_cliente(app, ["10", BadString()])

    # Deve continuar com label apenas com ID
    assert calls["move"] == [10]
    assert any("showinfo" in call[0] for call in reset_messagebox)


# ==================== Testes de dir_base_cliente_from_pk - exception em db_manager (linhas 173-174, 180-181) ====================


def test_dir_base_cliente_handles_db_manager_exception(monkeypatch, tmp_path):
    """Testa fallback quando db_manager.get_cliente_by_id lança exceção."""
    monkeypatch.setattr(app_core, "NO_FS", False)

    # path_resolver não disponível
    def fail_import(name):
        if name == "src.core.services.path_resolver":
            raise ImportError("Module not found")
        return sys.modules.get(name)

    # db_manager que falha com ImportError
    def fail_get_cliente(pk):
        raise ImportError("Database error")

    db_module = SimpleNamespace(get_cliente_by_id=fail_get_cliente)
    monkeypatch.setitem(sys.modules, "src.core.db_manager", db_module)
    monkeypatch.setattr(app_core, "safe_base_from_fields", lambda *args: "FALLBACK")
    monkeypatch.setattr(app_core, "DOCS_DIR", tmp_path)

    path = app_core.dir_base_cliente_from_pk(42)

    # Deve usar fallback com PK
    assert "FALLBACK" in path or "42" in path


def test_dir_base_cliente_uses_getattr_fallbacks_for_none_fields(monkeypatch, tmp_path):
    """Testa que dir_base_cliente_from_pk usa getattr com fallback correto."""
    monkeypatch.setattr(app_core, "NO_FS", False)

    # Cliente com campos None/vazios
    fake_cliente = SimpleNamespace(numero=None, cnpj=None, razao_social=None)
    db_module = SimpleNamespace(get_cliente_by_id=lambda pk: fake_cliente)
    monkeypatch.setitem(sys.modules, "src.core.db_manager", db_module)

    calls = []

    def track_safe_base(*args):
        calls.append(args)
        return "RESULT"

    monkeypatch.setattr(app_core, "safe_base_from_fields", track_safe_base)
    monkeypatch.setattr(app_core, "DOCS_DIR", tmp_path)

    path = app_core.dir_base_cliente_from_pk(42)

    # Verificar que passou strings vazias
    assert calls[0] == ("", "", "", 42)
    assert path  # Deve retornar um path


# ==================== Testes de _ensure_live_folder_ready - branches complexos (linhas 198-221) ====================


def test_ensure_live_folder_ready_with_cloud_only_skips_makedirs(monkeypatch, tmp_path):
    """Testa que _ensure_live_folder_ready pula makedirs quando CLOUD_ONLY=True."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", True)
    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(tmp_path / "test"))

    makedirs_calls = []
    monkeypatch.setattr(app_core.os, "makedirs", lambda *args, **kwargs: makedirs_calls.append(args))

    result = app_core._ensure_live_folder_ready(42)

    # makedirs não deve ser chamado
    assert makedirs_calls == []
    assert result == str(tmp_path / "test")


def test_ensure_live_folder_ready_handles_ensure_subpastas_exception(monkeypatch, tmp_path):
    """Testa que _ensure_live_folder_ready continua quando ensure_subpastas falha."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", False)
    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(tmp_path / "test"))

    def fail_ensure(*args, **kwargs):
        raise OSError("Subpastas error")

    file_utils_module = SimpleNamespace(ensure_subpastas=fail_ensure, write_marker=lambda p, pk: None)
    monkeypatch.setitem(sys.modules, "src.utils.file_utils", file_utils_module)

    config_module = SimpleNamespace(load_subpastas_config=lambda: (["sub1"], []))
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    # Não deve lançar exceção
    result = app_core._ensure_live_folder_ready(42)
    assert result == str(tmp_path / "test")


def test_ensure_live_folder_ready_handles_marker_read_exception(monkeypatch, tmp_path):
    """Testa que _ensure_live_folder_ready continua quando marker.read_text() falha."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", False)

    test_path = tmp_path / "test"
    test_path.mkdir()
    marker_path = test_path / ".rc_client_id"
    marker_path.write_text("old_content")

    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(test_path))

    # Mock Path.read_text para lançar exceção
    original_path = Path

    class FailingPath(original_path):
        def read_text(self, *args, **kwargs):
            raise OSError("Read error")

    file_utils_module = SimpleNamespace(ensure_subpastas=lambda *args, **kwargs: None, write_marker=lambda p, pk: None)
    monkeypatch.setitem(sys.modules, "src.utils.file_utils", file_utils_module)

    config_module = SimpleNamespace(load_subpastas_config=lambda: ([], []))
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    monkeypatch.setitem(sys.modules, "pathlib", SimpleNamespace(Path=FailingPath))

    # Não deve lançar exceção
    result = app_core._ensure_live_folder_ready(42)
    assert result == str(test_path)


def test_ensure_live_folder_ready_writes_marker_when_content_mismatch(monkeypatch, tmp_path):
    """Testa que _ensure_live_folder_ready escreve marker quando conteúdo não bate."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", False)

    test_path = tmp_path / "test"
    test_path.mkdir()
    marker_path = test_path / ".rc_client_id"
    marker_path.write_text("wrong_id")

    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(test_path))

    write_calls = []

    file_utils_module = SimpleNamespace(
        ensure_subpastas=lambda *args, **kwargs: None, write_marker=lambda p, pk: write_calls.append((p, pk))
    )
    monkeypatch.setitem(sys.modules, "src.utils.file_utils", file_utils_module)

    config_module = SimpleNamespace(load_subpastas_config=lambda: ([], []))
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    app_core._ensure_live_folder_ready(42)

    # write_marker deve ser chamado
    assert write_calls == [(str(test_path), 42)]


def test_ensure_live_folder_ready_skips_write_marker_when_cloud_only(monkeypatch, tmp_path):
    """Testa que _ensure_live_folder_ready não escreve marker quando CLOUD_ONLY=True."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", True)

    test_path = tmp_path / "test"
    test_path.mkdir()
    marker_path = test_path / ".rc_client_id"
    marker_path.write_text("wrong_id")

    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(test_path))

    write_calls = []

    file_utils_module = SimpleNamespace(
        ensure_subpastas=lambda *args, **kwargs: None, write_marker=lambda p, pk: write_calls.append((p, pk))
    )
    monkeypatch.setitem(sys.modules, "src.utils.file_utils", file_utils_module)

    config_module = SimpleNamespace(load_subpastas_config=lambda: ([], []))
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    app_core._ensure_live_folder_ready(42)

    # write_marker não deve ser chamado (branch 217->224 coberto)
    assert write_calls == []


def test_ensure_live_folder_ready_marker_not_file_skips_content_check(monkeypatch, tmp_path):
    """Testa branch quando marker_path não é um arquivo."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", False)

    test_path = tmp_path / "test"
    test_path.mkdir()
    # Não criar o marker, então is_file() retorna False

    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(test_path))

    write_calls = []

    file_utils_module = SimpleNamespace(
        ensure_subpastas=lambda *args, **kwargs: None, write_marker=lambda p, pk: write_calls.append((p, pk))
    )
    monkeypatch.setitem(sys.modules, "src.utils.file_utils", file_utils_module)

    config_module = SimpleNamespace(load_subpastas_config=lambda: ([], []))
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    app_core._ensure_live_folder_ready(42)

    # write_marker deve ser chamado porque marker não existe
    assert write_calls == [(str(test_path), 42)]


def test_ensure_live_folder_ready_with_valid_marker_content(monkeypatch, tmp_path):
    """Testa que não escreve marker quando conteúdo está correto."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", False)

    test_path = tmp_path / "test"
    test_path.mkdir()
    marker_path = test_path / ".rc_client_id"
    marker_path.write_text("42")  # ID correto

    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(test_path))

    write_calls = []

    file_utils_module = SimpleNamespace(
        ensure_subpastas=lambda *args, **kwargs: None, write_marker=lambda p, pk: write_calls.append((p, pk))
    )
    monkeypatch.setitem(sys.modules, "src.utils.file_utils", file_utils_module)

    config_module = SimpleNamespace(load_subpastas_config=lambda: ([], []))
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    app_core._ensure_live_folder_ready(42)

    # write_marker NÃO deve ser chamado porque conteúdo está correto
    assert write_calls == []


def test_ensure_live_folder_ready_handles_load_subpastas_config_exception(monkeypatch, tmp_path):
    """Testa que _ensure_live_folder_ready usa lista vazia quando load_subpastas_config falha."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "CLOUD_ONLY", False)
    monkeypatch.setattr(app_core, "dir_base_cliente_from_pk", lambda pk: str(tmp_path / "test"))

    ensure_calls = []

    file_utils_module = SimpleNamespace(
        ensure_subpastas=lambda p, subpastas: ensure_calls.append(subpastas), write_marker=lambda p, pk: None
    )
    monkeypatch.setitem(sys.modules, "src.utils.file_utils", file_utils_module)

    def raise_oserror():
        raise OSError("Config error")

    config_module = SimpleNamespace(load_subpastas_config=raise_oserror)
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    app_core._ensure_live_folder_ready(42)

    # Deve usar lista vazia
    assert ensure_calls == [[]]


# ==================== Testes de abrir_lixeira_ui - fallbacks com importlib (linhas 297-298, 301-309, 312-313) ====================


def test_abrir_lixeira_ui_fallback_to_importlib_success(monkeypatch):
    """Testa que abrir_lixeira_ui usa importlib quando imports diretos falham."""
    # Limpar cache
    monkeypatch.setattr(app_core, "_module_abrir_lixeira", None)

    called = []

    def fake_open(parent, app_ctx, *args, **kwargs):
        called.append((parent, app_ctx))
        return "window"

    # Mock do módulo via importlib
    lixeira_module = SimpleNamespace(abrir_lixeira=fake_open)

    # Bloquear o import direto dentro da função
    def block_direct_import():
        raise ImportError("Direct import blocked")

    # Precisamos mockar o import no nível do sys.modules
    # Remover módulo do cache para forçar import
    if "src.modules.lixeira.views.lixeira" in sys.modules:
        monkeypatch.delitem(sys.modules, "src.modules.lixeira.views.lixeira")

    original_import = importlib.import_module

    def mock_import_module(name):
        if name == "src.modules.lixeira":
            return lixeira_module
        if name == "src.modules.lixeira.views.lixeira":
            raise ImportError("Module not found")
        return original_import(name)

    monkeypatch.setattr(importlib, "import_module", mock_import_module)

    # Mockar o __import__ para bloquear import direto
    original_import_func = builtins.__import__

    def mock_builtin_import(name, *args, **kwargs):
        if "lixeira.views.lixeira" in name:
            raise ImportError("Blocked")
        return original_import_func(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_builtin_import)

    app = SimpleNamespace(root="ROOT", app="CTX")
    app_core.abrir_lixeira_ui(app)

    assert called == [("ROOT", "CTX")]


def test_abrir_lixeira_ui_tries_all_fallback_modules(monkeypatch):
    """Testa que abrir_lixeira_ui tenta todos os módulos de fallback."""
    # Limpar cache
    monkeypatch.setattr(app_core, "_module_abrir_lixeira", None)

    called = []

    def fake_open(parent, app_ctx, *args, **kwargs):
        called.append(True)
        return "window"

    # Mock para capturar tentativas de import
    import_attempts = []

    def mock_import_module(name):
        import_attempts.append(name)
        if name == "ui.lixeira":
            # Último fallback sucede
            return SimpleNamespace(abrir_lixeira=fake_open)
        # Outros falham
        raise ImportError(f"Module {name} not found")

    monkeypatch.setattr(importlib, "import_module", mock_import_module)

    # Mockar o __import__ para bloquear import direto
    original_import_func = builtins.__import__

    def mock_builtin_import(name, *args, **kwargs):
        if "lixeira.views.lixeira" in name:
            raise ImportError("Blocked")
        return original_import_func(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_builtin_import)

    app = SimpleNamespace(root="ROOT", app="CTX")
    app_core.abrir_lixeira_ui(app)

    # Deve ter tentado os 3 módulos
    assert "src.modules.lixeira" in import_attempts
    assert "src.ui.lixeira" in import_attempts
    assert "ui.lixeira" in import_attempts
    assert called == [True]


def test_abrir_lixeira_ui_raises_when_no_function_found(monkeypatch):
    """Testa que abrir_lixeira_ui lança AttributeError quando nenhuma função encontrada."""
    # Limpar cache
    monkeypatch.setattr(app_core, "_module_abrir_lixeira", None)

    # Simular falha em todos os imports
    original_import = importlib.import_module

    def mock_import_module(name):
        if name in ("src.modules.lixeira", "src.ui.lixeira", "ui.lixeira"):
            raise ImportError(f"Module {name} not found")
        return original_import(name)

    monkeypatch.setattr(importlib, "import_module", mock_import_module)

    # Mockar o __import__ para bloquear import direto
    original_import_func = builtins.__import__

    def mock_builtin_import(name, *args, **kwargs):
        if "lixeira.views.lixeira" in name:
            raise ImportError("Blocked")
        return original_import_func(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_builtin_import)

    app = SimpleNamespace(root="ROOT", app="CTX")

    with pytest.raises(AttributeError, match="Nenhuma funcao de abertura encontrada"):
        app_core.abrir_lixeira_ui(app)


def test_abrir_lixeira_ui_handles_module_without_function(monkeypatch):
    """Testa que abrir_lixeira_ui ignora módulos que não têm abrir_lixeira."""
    # Limpar cache
    monkeypatch.setattr(app_core, "_module_abrir_lixeira", None)

    called = []

    def fake_open(parent, app_ctx, *args, **kwargs):
        called.append(True)
        return "window"

    def mock_import_module(name):
        if name == "src.modules.lixeira":
            # Módulo existe mas não tem a função
            return SimpleNamespace()
        if name == "src.ui.lixeira":
            # Módulo tem a função
            return SimpleNamespace(abrir_lixeira=fake_open)
        raise ImportError(f"Module {name} not found")

    monkeypatch.setattr(importlib, "import_module", mock_import_module)

    # Mockar o __import__ para bloquear import direto
    original_import_func = builtins.__import__

    def mock_builtin_import(name, *args, **kwargs):
        if "lixeira.views.lixeira" in name:
            raise ImportError("Blocked")
        return original_import_func(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_builtin_import)

    app = SimpleNamespace(root="ROOT", app="CTX")
    app_core.abrir_lixeira_ui(app)

    # Deve ter pulado o primeiro e usado o segundo
    assert called == [True]


# ==================== Testes de branches adicionais (linhas 17-19, 32-34) ====================


def test_module_level_import_exception_safe_base_from_fields(monkeypatch):
    """Testa que o import de safe_base_from_fields trata exceção corretamente."""
    # Forçar reimport do módulo com falha no import
    import sys

    # Salvar módulo original
    original_app_core = sys.modules.get("src.app_core")

    try:
        # Remover do cache
        if "src.app_core" in sys.modules:
            del sys.modules["src.app_core"]

        # Mock para falhar imports específicos
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "app_utils" in name:
                raise ImportError("Mocked failure")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # Reimportar
        import src.app_core as reimported

        # Verificar fallback
        assert reimported.safe_base_from_fields is None
        assert reimported.DOCS_DIR is not None  # Deve ter fallback para os.getcwd()

    finally:
        # Restaurar módulo original
        if original_app_core is not None:
            sys.modules["src.app_core"] = original_app_core


# ==================== Testes de dir_base_cliente - exception em import (linha 173-174) ====================


def test_dir_base_cliente_handles_import_exception_for_path_resolver(monkeypatch, tmp_path):
    """Testa que dir_base_cliente_from_pk continua quando import de path_resolver falha."""
    monkeypatch.setattr(app_core, "NO_FS", False)

    # Cliente mock
    fake_cliente = SimpleNamespace(numero="001", cnpj="12345", razao_social="ACME")
    db_module = SimpleNamespace(get_cliente_by_id=lambda pk: fake_cliente)
    monkeypatch.setitem(sys.modules, "src.core.db_manager", db_module)

    # Bloquear import de path_resolver
    if "src.core.services.path_resolver" in sys.modules:
        monkeypatch.delitem(sys.modules, "src.core.services.path_resolver")

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "path_resolver" in name:
            raise ImportError("Module not found")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    monkeypatch.setattr(app_core, "safe_base_from_fields", lambda *args: "RESULT")
    monkeypatch.setattr(app_core, "DOCS_DIR", tmp_path)

    path = app_core.dir_base_cliente_from_pk(42)

    # Deve usar fallback com db_manager
    assert "RESULT" in path


# ==================== Testes de abrir_lixeira_ui - linha 297-298 (import direto fail) ====================


def test_abrir_lixeira_ui_handles_direct_import_exception(monkeypatch):
    """Testa que abrir_lixeira_ui trata exceção no import direto e usa importlib."""
    # Limpar cache
    monkeypatch.setattr(app_core, "_module_abrir_lixeira", None)

    called = []

    def fake_open(parent, app_ctx, *args, **kwargs):
        called.append(True)
        return "window"

    # Mock importlib
    original_import = importlib.import_module

    def mock_import_module(name):
        if name == "src.modules.lixeira":
            return SimpleNamespace(abrir_lixeira=fake_open)
        return original_import(name)

    monkeypatch.setattr(importlib, "import_module", mock_import_module)

    # Bloquear import direto
    original_builtin_import = builtins.__import__

    def mock_builtin_import(name, *args, **kwargs):
        if "lixeira.views.lixeira" in name:
            raise ImportError("Direct import blocked")
        return original_builtin_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_builtin_import)

    app = SimpleNamespace(root="ROOT", app="CTX")
    app_core.abrir_lixeira_ui(app)

    assert called == [True]


# ==================== Testes de open_client_local_subfolders - linha 321-322 (exception) ====================


def test_open_client_local_subfolders_success_flow(monkeypatch, tmp_path):
    """Testa fluxo de sucesso de open_client_local_subfolders."""
    monkeypatch.setattr(app_core, "NO_FS", False)
    monkeypatch.setattr(app_core, "_ensure_live_folder_ready", lambda pk: str(tmp_path))

    dialog_calls = []

    def fake_dialog(app, path, subpastas, extras):
        dialog_calls.append((app, path, subpastas, extras))

    forms_module = SimpleNamespace(open_subpastas_dialog=fake_dialog)
    monkeypatch.setitem(sys.modules, "src.modules.clientes.forms", forms_module)

    config_module = SimpleNamespace(load_subpastas_config=lambda: (["sub1", "sub2"], ["extra1"]))
    monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", config_module)

    app = SimpleNamespace()
    app_core.open_client_local_subfolders(app, 42)

    assert len(dialog_calls) == 1
    assert dialog_calls[0][2] == ["sub1", "sub2"]
    assert dialog_calls[0][3] == ["extra1"]
