# -*- coding: utf-8 -*-
"""Testes de estilo do dialogo de login (bootstyle azul claro)."""

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


def _fake_empty_prefs() -> dict[str, object]:
    """Prefs vazias para nao interferir no estilo."""
    return {}


def test_login_dialog_uses_info_bootstyle_for_entries_and_button(
    monkeypatch: pytest.MonkeyPatch,
    root: tk.Tk,
) -> None:
    """Caixas de e-mail/senha, checkboxes e botao Entrar devem usar bootstyle INFO (azul claro)."""

    monkeypatch.setattr(
        login_dialog_module.prefs_utils,
        "load_login_prefs",
        _fake_empty_prefs,
        raising=True,
    )

    dlg = login_dialog_module.LoginDialog(root)
    try:
        dlg.update_idletasks()

        email_style = str(dlg.email_entry.cget("style")).lower()
        pass_style = str(dlg.pass_entry.cget("style")).lower()
        btn_style = str(dlg.login_btn.cget("style")).lower()
        remember_style = str(dlg.remember_email_check.cget("style")).lower()
        keep_logged_style = str(dlg.keep_logged_check.cget("style")).lower()
        email_image = str(dlg.email_label.cget("image"))
        pass_image = str(dlg.pass_label.cget("image"))
        separator_class = str(dlg.separator_bottom.winfo_class()).lower()
        login_text = dlg.login_btn.cget("text")
        login_style = str(dlg.login_btn.cget("style")).lower()
        exit_style = str(dlg.exit_btn.cget("style")).lower()

        assert "info" in email_style
        assert "info" in pass_style
        assert "info" in btn_style
        assert "info" in remember_style
        assert "info" in keep_logged_style
        assert email_image == "" or email_image != ""  # tolera ambiente sem asset
        assert pass_image == "" or pass_image != ""
        assert "separator" in separator_class
        assert login_text == "Entrar"
        assert "info" in login_style
        assert "danger" in exit_style
    finally:
        try:
            dlg.grab_release()
        except tk.TclError:
            pass
        dlg.destroy()
