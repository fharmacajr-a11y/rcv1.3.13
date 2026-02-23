# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes unitários de cleanup do ClientFilesDialog (sem Tk real).

Estratégia: pré-mockar todos os módulos pesados em sys.modules ANTES de
importar o dialog, depois usar __new__ para criar instâncias sem chamar
__init__ (que exige janela Tk real).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import types
import unittest
from unittest.mock import MagicMock, call, patch

# ---------------------------------------------------------------------------
# 1. Pre-mock de módulos pesados (tkinter, ctk, supabase, etc.)
# ---------------------------------------------------------------------------
from typing import Any, cast

# ---------------------------------------------------------------------------
# 1. Stubs — construídos em _build_stubs(), aplicados em setUpModule
#    NÃO modificam sys.modules em tempo de importação/discover
# ---------------------------------------------------------------------------

_DIALOG_MOD_NAME = "src.modules.clientes.ui.views.client_files_dialog"
_DIALOG_MOD_PATH = (
    pathlib.Path(__file__).parent.parent
    / "src" / "modules" / "clientes" / "ui" / "views" / "client_files_dialog.py"
)


def _build_stubs() -> dict:
    """Retorna dict de stubs para patch.dict(sys.modules). Sem side-effects."""
    _TclError = type("TclError", (Exception,), {})
    _tk = types.ModuleType("tkinter")
    _tk.TclError = _TclError  # type: ignore[attr-defined]
    _tk.Misc = object          # type: ignore[attr-defined]

    _ctk_toplevel_base = type("CTkToplevel", (object,), {"winfo_exists": lambda self: True})
    _ctk_inner = MagicMock()
    _ctk_inner.CTkToplevel = _ctk_toplevel_base
    _ctk_config = MagicMock()
    _ctk_config.ctk = _ctk_inner

    stubs: dict = {
        "tkinter":                                         _tk,
        "tkinter.messagebox":                              MagicMock(),
        "tkinter.filedialog":                              MagicMock(),
        "customtkinter":                                   MagicMock(),
        "PIL":                                             MagicMock(),
        "PIL.Image":                                       MagicMock(),
        "PIL.ImageDraw":                                   MagicMock(),
        "PIL.ImageTk":                                     MagicMock(),
        "yaml":                                            MagicMock(),
        "src.ui.ctk_config":                               _ctk_config,
        "src.ui.widgets.button_factory":                   MagicMock(),
        "src.ui.ui_tokens":                                MagicMock(),
        "src.ui.ttk_treeview_theme":                       MagicMock(),
        "src.ui.widgets.ctk_treeview_container":           MagicMock(),
        "src.ui.dark_window_helper":                       MagicMock(),
        "src.ui.window_utils":                             MagicMock(),
        "src.adapters.storage.supabase_storage":           MagicMock(),
        "src.modules.uploads.components.helpers":          MagicMock(),
        "src.modules.clientes.forms.client_subfolder_prompt": MagicMock(),
        "src.infra.supabase_client":                       MagicMock(),
        "src.infra.supabase.db_client":                    MagicMock(),
        "src.infra.supabase.auth_client":                  MagicMock(),
    }
    return stubs


# Placeholders — preenchidos em setUpModule
ClientFilesDialog: Any = None
_cf_patcher: Any = None


def setUpModule() -> None:  # noqa: N802
    global ClientFilesDialog, _cf_patcher
    _cf_patcher = patch.dict(sys.modules, _build_stubs())
    _cf_patcher.start()
    spec = importlib.util.spec_from_file_location(_DIALOG_MOD_NAME, _DIALOG_MOD_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[_DIALOG_MOD_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    ClientFilesDialog = cast(Any, mod).ClientFilesDialog


def tearDownModule() -> None:  # noqa: N802
    global ClientFilesDialog, _cf_patcher
    ClientFilesDialog = None
    sys.modules.pop(_DIALOG_MOD_NAME, None)
    if _cf_patcher is not None:
        _cf_patcher.stop()
    _cf_patcher = None


# ---------------------------------------------------------------------------
# 3. Helper: cria instância sem __init__
# ---------------------------------------------------------------------------

def _bare_instance() -> ClientFilesDialog:
    """Cria ClientFilesDialog com __new__, setando apenas atributos mínimos."""
    obj = ClientFilesDialog.__new__(ClientFilesDialog)
    obj._executor = None
    obj._closing = False
    return obj


# ---------------------------------------------------------------------------
# 4. Testes de _shutdown_executor
# ---------------------------------------------------------------------------

class TestShutdownExecutor(unittest.TestCase):

    def test_shutdown_calls_shutdown_with_cancel_futures(self):
        """Deve chamar shutdown(wait=False, cancel_futures=True) no executor."""
        obj = _bare_instance()
        mock_exec = MagicMock()
        obj._executor = mock_exec

        obj._shutdown_executor()

        mock_exec.shutdown.assert_called_once_with(wait=False, cancel_futures=True)

    def test_shutdown_sets_executor_to_none(self):
        """Após _shutdown_executor, self._executor deve ser None."""
        obj = _bare_instance()
        obj._executor = MagicMock()

        obj._shutdown_executor()

        self.assertIsNone(obj._executor)

    def test_shutdown_idempotent_first_call_none(self):
        """Chamar _shutdown_executor quando _executor já é None não estoura."""
        obj = _bare_instance()
        obj._executor = None

        try:
            obj._shutdown_executor()
        except Exception as exc:
            self.fail(f"_shutdown_executor levantou com _executor=None: {exc}")

    def test_shutdown_idempotent_two_calls(self):
        """Chamar _shutdown_executor duas vezes não estoura."""
        obj = _bare_instance()
        obj._executor = MagicMock()

        obj._shutdown_executor()
        try:
            obj._shutdown_executor()
        except Exception as exc:
            self.fail(f"Segunda chamada a _shutdown_executor levantou: {exc}")

    def test_shutdown_fallback_when_type_error(self):
        """Se shutdown(cancel_futures=True) levantar TypeError, deve tentar sem cancel_futures."""
        obj = _bare_instance()
        mock_exec = MagicMock()

        # Primeiro call levanta TypeError (Python < 3.9); segundo deve funcionar
        mock_exec.shutdown.side_effect = [TypeError("unexpected keyword"), None]
        obj._executor = mock_exec

        obj._shutdown_executor()

        # Deve ter sido chamado duas vezes
        self.assertEqual(mock_exec.shutdown.call_count, 2)
        # A segunda chamada não deve ter cancel_futures
        second_call_kwargs = mock_exec.shutdown.call_args_list[1].kwargs
        self.assertNotIn("cancel_futures", second_call_kwargs)

    def test_shutdown_executor_zeroed_before_shutdown_call(self):
        """self._executor deve ser zerado para None ANTES de chamar shutdown,
        prevenindo submits concorrentes enquanto shutdown está correndo."""
        obj = _bare_instance()
        seen_executor_during_shutdown: list = []

        def _spy_shutdown(**kwargs):
            # Captura o estado de obj._executor durante a chamada
            seen_executor_during_shutdown.append(obj._executor)

        mock_exec = MagicMock()
        mock_exec.shutdown.side_effect = _spy_shutdown
        obj._executor = mock_exec

        obj._shutdown_executor()

        # obj._executor já deve ser None no momento em que shutdown() rodou
        self.assertEqual(seen_executor_during_shutdown, [None])


# ---------------------------------------------------------------------------
# 5. Testes de _safe_close (usa _shutdown_executor)
# ---------------------------------------------------------------------------

class TestSafeClose(unittest.TestCase):

    def _make_closeable(self) -> ClientFilesDialog:
        obj = _bare_instance()
        obj._executor = MagicMock()
        # Métodos necessários para _safe_close
        obj._cancel_afters = MagicMock()
        obj.destroy = MagicMock()
        return obj

    def test_safe_close_sets_closing_flag(self):
        obj = self._make_closeable()
        obj._safe_close()
        self.assertTrue(obj._closing)

    def test_safe_close_calls_shutdown_executor(self):
        obj = self._make_closeable()
        obj._safe_close()
        self.assertIsNone(obj._executor)

    def test_safe_close_calls_cancel_afters(self):
        obj = self._make_closeable()
        obj._safe_close()
        obj._cancel_afters.assert_called_once()

    def test_safe_close_calls_destroy(self):
        obj = self._make_closeable()
        obj._safe_close()
        obj.destroy.assert_called_once()

    def test_safe_close_idempotent(self):
        """Chamar _safe_close duas vezes não deve chamar _cancel_afters/destroy duas vezes."""
        obj = self._make_closeable()
        obj._safe_close()
        obj._safe_close()
        obj._cancel_afters.assert_called_once()
        obj.destroy.assert_called_once()

    def test_safe_close_destroy_exception_suppressed(self):
        """Se destroy() levantar, _safe_close não deve propagar a exceção."""
        obj = self._make_closeable()
        obj.destroy.side_effect = RuntimeError("widget already dead")
        try:
            obj._safe_close()
        except Exception as exc:
            self.fail(f"_safe_close não deveria propagar exceção de destroy: {exc}")


if __name__ == "__main__":
    unittest.main()
