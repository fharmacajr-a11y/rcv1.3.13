from __future__ import annotations

import logging
import sys
import types

import src.utils.errors as errors


def _restore_excepthook(original) -> None:
    sys.excepthook = original


def test_install_hook_logs_and_calls_original(monkeypatch, caplog) -> None:
    original_hook = sys.excepthook
    called: list[tuple[type[BaseException], BaseException, object]] = []

    def fake_original(exc_type, exc_value, exc_tb) -> None:
        called.append((exc_type, exc_value, exc_tb))

    monkeypatch.setattr(sys, "excepthook", fake_original)
    monkeypatch.setenv("RC_NO_GUI_ERRORS", "1")
    caplog.set_level(logging.CRITICAL)
    try:
        errors.install_global_exception_hook()
        assert sys.excepthook is not fake_original

        err = RuntimeError("boom")
        sys.excepthook(RuntimeError, err, None)

        assert called == [(RuntimeError, err, None)]
        assert any("Unhandled exception" in record.message for record in caplog.records)
    finally:
        _restore_excepthook(original_hook)


def test_exception_hook_shows_gui_when_allowed(monkeypatch) -> None:
    original_hook = sys.excepthook
    monkeypatch.delenv("RC_NO_GUI_ERRORS", raising=False)
    calls: list[tuple[str, str]] = []

    tk_mod = types.ModuleType("tkinter")
    tk_mod._default_root = object()
    messagebox_mod = types.ModuleType("tkinter.messagebox")

    def showerror(title: str, message: str) -> None:
        calls.append((title, message))

    messagebox_mod.showerror = showerror
    monkeypatch.setitem(sys.modules, "tkinter", tk_mod)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox_mod)

    try:
        errors.install_global_exception_hook()
        exc = ValueError("bad")
        sys.excepthook(ValueError, exc, None)
    finally:
        _restore_excepthook(original_hook)
        sys.modules.pop("tkinter", None)
        sys.modules.pop("tkinter.messagebox", None)

    assert calls and "ValueError: bad" in calls[0][1]


def test_exception_hook_logs_warning_when_gui_fails(monkeypatch, caplog) -> None:
    original_hook = sys.excepthook
    monkeypatch.delenv("RC_NO_GUI_ERRORS", raising=False)
    caplog.set_level(logging.WARNING)

    tk_mod = types.ModuleType("tkinter")
    tk_mod._default_root = object()
    messagebox_mod = types.ModuleType("tkinter.messagebox")

    def raise_showerror(*_args, **_kwargs) -> None:
        raise RuntimeError("gui boom")

    messagebox_mod.showerror = raise_showerror
    monkeypatch.setitem(sys.modules, "tkinter", tk_mod)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox_mod)

    try:
        errors.install_global_exception_hook()
        exc = RuntimeError("oops")
        sys.excepthook(RuntimeError, exc, None)
    finally:
        _restore_excepthook(original_hook)
        sys.modules.pop("tkinter", None)
        sys.modules.pop("tkinter.messagebox", None)

    assert any("Failed to show GUI error dialog" in record.message for record in caplog.records)


def test_exception_hook_handles_missing_default_root(monkeypatch) -> None:
    original_hook = sys.excepthook
    monkeypatch.delenv("RC_NO_GUI_ERRORS", raising=False)

    tk_mod = types.ModuleType("tkinter")

    def __getattr__(name: str):
        if name == "_default_root":
            raise RuntimeError("no default root")
        raise AttributeError(name)

    tk_mod.__getattr__ = __getattr__  # type: ignore[attr-defined]
    messagebox_mod = types.ModuleType("tkinter.messagebox")
    messagebox_mod.showerror = lambda *_args, **_kwargs: None
    tk_mod.messagebox = messagebox_mod  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "tkinter", tk_mod)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox_mod)

    try:
        errors.install_global_exception_hook()
        exc = Exception("fallback")
        # should swallow _default_root failure and still call original hook
        errors_called: list[tuple[type[BaseException], BaseException, object]] = []

        def fake_original(exc_type, exc_value, exc_tb) -> None:
            errors_called.append((exc_type, exc_value, exc_tb))

        sys.excepthook = fake_original
        errors.install_global_exception_hook()
        sys.excepthook(Exception, exc, None)
        assert errors_called == [(Exception, exc, None)]
    finally:
        _restore_excepthook(original_hook)
        sys.modules.pop("tkinter", None)
        sys.modules.pop("tkinter.messagebox", None)


def test_uninstall_restores_builtin(monkeypatch) -> None:
    original_hook = sys.excepthook
    monkeypatch.setenv("RC_NO_GUI_ERRORS", "1")
    try:
        errors.install_global_exception_hook()
        assert sys.excepthook is not original_hook
        errors.uninstall_global_exception_hook()
        assert sys.excepthook is sys.__excepthook__
    finally:
        _restore_excepthook(original_hook)
