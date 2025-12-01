# -*- coding: utf-8 -*-
"""Testes para o foco inicial do dialogo de login (SupabaseLoginDialog)."""

from __future__ import annotations

import os
import tkinter as tk

import pytest

from src.ui import login_dialog as login_dialog_module

if os.environ.get("RC_RUN_GUI_TESTS") != "1":
    pytest.skip(
        "GUI tests de LoginDialog pulados por padrão (defina RC_RUN_GUI_TESTS=1 para rodar).",
        allow_module_level=True,
    )


@pytest.fixture
def root(tk_root_session: tk.Tk):
    """Cria Toplevel para testes do dialogo de login."""
    toplevel = tk.Toplevel(master=tk_root_session)
    toplevel.withdraw()
    try:
        yield toplevel
    finally:
        try:
            toplevel.destroy()
        except tk.TclError:
            pass


def test_login_dialog_focuses_password_when_email_prefilled(monkeypatch: pytest.MonkeyPatch, root: tk.Tk) -> None:
    """Quando ha e-mail salvo nas preferencias, o foco inicial deve ir para a senha."""

    def fake_load_login_prefs() -> dict[str, object]:
        return {"email": "user@test.com", "remember_email": True}

    # Patch em src.ui.login_dialog.prefs_utils.load_login_prefs
    monkeypatch.setattr(
        login_dialog_module.prefs_utils,
        "load_login_prefs",
        fake_load_login_prefs,
    )

    dlg = login_dialog_module.LoginDialog(root)
    try:
        dlg.update()
        focused = dlg.focus_get()
        assert focused is dlg.pass_entry
    finally:
        try:
            dlg.grab_release()
        except tk.TclError:
            pass
        dlg.destroy()


def test_login_dialog_focuses_email_when_no_saved_email(monkeypatch: pytest.MonkeyPatch, root: tk.Tk) -> None:
    """Sem e-mail salvo, o foco inicial continua no campo de e-mail."""

    def fake_load_login_prefs() -> dict[str, object]:
        return {}

    monkeypatch.setattr(
        login_dialog_module.prefs_utils,
        "load_login_prefs",
        fake_load_login_prefs,
    )

    dlg = login_dialog_module.LoginDialog(root)
    try:
        dlg.update()
        focused = dlg.focus_get()
        assert focused is dlg.email_entry
    finally:
        try:
            dlg.grab_release()
        except tk.TclError:
            pass
        dlg.destroy()
