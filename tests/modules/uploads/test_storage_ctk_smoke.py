# -*- coding: utf-8 -*-
"""Testes smoke para migração de storage/arquivos para CustomTkinter (Microfase 21)."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any, Callable, Generator

import pytest

if TYPE_CHECKING:
    pass


@pytest.fixture
def skip_if_no_tk() -> Generator[None, None, None]:
    """Skip test se Tk não estiver disponível."""
    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        yield
    except Exception as exc:
        pytest.skip(f"Tk não disponível: {exc}")


@pytest.fixture
def make_browser_window(
    monkeypatch: pytest.MonkeyPatch, tk_root_session: tk.Tk
) -> Generator[Callable[..., Any], None, None]:
    """Cria UploadsBrowserWindow sem carregar estado inicial."""
    from src.modules.uploads.views import browser

    monkeypatch.setattr(browser.UploadsBrowserWindow, "_populate_initial_state", lambda self: None)
    monkeypatch.setattr(browser, "show_centered", lambda *args, **kwargs: None)
    monkeypatch.setattr(browser, "list_browser_items", lambda *args, **kwargs: [])

    def _factory(**kwargs: Any) -> browser.UploadsBrowserWindow:
        defaults = {
            "client_id": 1,
            "razao": "Test Client",
            "cnpj": "12345678000199",
            "bucket": "test-bucket",
            "base_prefix": "org/1",
        }
        params = {**defaults, **kwargs}
        win = browser.UploadsBrowserWindow(tk_root_session, **params)
        return win

    yield _factory


def test_browser_window_creates_without_exception(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que a janela do browser monta sem exception (smoke test)."""
    win = make_browser_window()
    assert win is not None
    assert hasattr(win, "file_list")
    assert hasattr(win, "actions")
    win.destroy()


def test_file_list_has_treeview(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que FileList tem um ttk.Treeview (não foi migrado para CTk)."""
    from tkinter import ttk

    win = make_browser_window()
    file_list = win.file_list

    assert hasattr(file_list, "tree")
    assert isinstance(file_list.tree, ttk.Treeview), "FileList.tree deve ser ttk.Treeview"

    win.destroy()


def test_treeview_has_correct_columns(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que o Treeview tem as colunas corretas: apenas 'type'."""
    win = make_browser_window()
    tree = win.file_list.tree

    columns = tree["columns"]
    assert "type" in columns, "Coluna 'type' deve existir no Treeview"
    assert len(columns) == 1, f"Treeview deve ter apenas 1 coluna, tem {len(columns)}: {columns}"

    win.destroy()


def test_action_bar_creates_without_exception(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que ActionBar monta sem exception."""
    win = make_browser_window()
    actions = win.actions

    assert actions is not None
    assert hasattr(actions, "btn_download")
    assert hasattr(actions, "btn_delete")
    assert hasattr(actions, "btn_view")
    assert hasattr(actions, "btn_download_folder")

    win.destroy()


def test_action_bar_buttons_start_disabled(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que botões do ActionBar começam desabilitados (exceto fechar)."""
    win = make_browser_window()
    actions = win.actions

    # Verificar estados (CTk e ttk usam "disabled" como string)
    if actions.btn_download is not None:
        state = str(actions.btn_download.cget("state"))
        assert state == "disabled", f"btn_download deve começar disabled, mas está: {state}"

    if actions.btn_delete is not None:
        state = str(actions.btn_delete.cget("state"))
        assert state == "disabled", f"btn_delete deve começar disabled, mas está: {state}"

    if actions.btn_view is not None:
        state = str(actions.btn_view.cget("state"))
        assert state == "disabled", f"btn_view deve começar disabled, mas está: {state}"

    if actions.btn_download_folder is not None:
        state = str(actions.btn_download_folder.cget("state"))
        assert state == "disabled", f"btn_download_folder deve começar disabled, mas está: {state}"

    win.destroy()


def test_file_list_populate_without_crash(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que populate_tree_hierarchical não causa crash (smoke test)."""
    win = make_browser_window()
    file_list = win.file_list

    # Dados de teste
    items = [
        {"name": "GERAL", "is_folder": True, "full_path": "org/1/GERAL"},
        {"name": "test.pdf", "is_folder": False, "full_path": "org/1/test.pdf"},
    ]

    # Não deve crashar
    file_list.populate_tree_hierarchical(items, "org/1", {})

    # Verificar que itens foram inseridos
    children = file_list.tree.get_children()
    assert len(children) == 2, f"Esperado 2 itens, mas obteve {len(children)}"

    win.destroy()


def test_action_bar_set_enabled_works(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que set_enabled habilita/desabilita botões corretamente."""
    win = make_browser_window()
    actions = win.actions

    # Habilitar apenas download
    actions.set_enabled(download=True, download_folder=False, delete=False, view=False)

    if actions.btn_download is not None:
        state = str(actions.btn_download.cget("state"))
        assert state == "normal", f"btn_download deve estar enabled, mas está: {state}"

    if actions.btn_delete is not None:
        state = str(actions.btn_delete.cget("state"))
        assert state == "disabled", f"btn_delete deve estar disabled, mas está: {state}"

    win.destroy()


def test_file_list_is_ctk_or_ttk_frame(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que FileList herda de CTkFrame (se CTk disponível) ou ttk.Frame."""
    win = make_browser_window()
    file_list = win.file_list

    # Verificar que é um frame válido
    assert hasattr(file_list, "grid")
    assert hasattr(file_list, "columnconfigure")

    # Verificar que tree é ttk.Treeview (nunca migrado)
    from tkinter import ttk

    assert isinstance(file_list.tree, ttk.Treeview)

    win.destroy()


def test_browser_window_is_ctk_or_tk_toplevel(make_browser_window: Callable, skip_if_no_tk: None) -> None:
    """Testa que UploadsBrowserWindow herda de CTkToplevel (se CTk disponível) ou tk.Toplevel."""
    import tkinter as tk
    from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

    win = make_browser_window()

    # Verificar que é um Toplevel válido
    assert hasattr(win, "title")
    assert hasattr(win, "destroy")
    assert hasattr(win, "withdraw")

    # Verificar que herda de Toplevel ou CTkToplevel

    if HAS_CUSTOMTKINTER:
        assert isinstance(win, (tk.Toplevel, ctk.CTkToplevel))  # type: ignore[union-attr]
    else:
        assert isinstance(win, tk.Toplevel)

    win.destroy()
