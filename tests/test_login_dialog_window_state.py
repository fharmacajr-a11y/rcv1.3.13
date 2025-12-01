# -*- coding: utf-8 -*-
"""Testes do comportamento de minimização do LoginDialog (GUI opcional via RC_RUN_GUI_TESTS)."""

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
    """Cria Toplevel para testes de janela de login."""
    toplevel = tk.Toplevel(master=tk_root_session)
    toplevel.withdraw()
    try:
        yield toplevel
    finally:
        try:
            toplevel.destroy()
        except tk.TclError:
            pass


def test_login_dialog_can_iconify_and_deiconify(root: tk.Tk) -> None:
    """LoginDialog deve aceitar iconify/deiconify sem quebrar."""
    dlg = login_dialog_module.LoginDialog(root)
    try:
        dlg.update_idletasks()

        dlg.iconify()
        dlg.update_idletasks()

        state_after_iconify = dlg.state().lower()
        assert state_after_iconify in {"iconic", "withdrawn"}

        dlg.deiconify()
        dlg.update_idletasks()

        state_after_restore = dlg.state().lower()
        assert state_after_restore == "normal"
    finally:
        try:
            dlg.grab_release()
        except tk.TclError:
            pass
        dlg.destroy()
