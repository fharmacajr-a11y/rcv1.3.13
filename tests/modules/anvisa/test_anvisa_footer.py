# -*- coding: utf-8 -*-
"""Testes para o footer ANVISA."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import patch

import pytest

from src.modules.anvisa.views.anvisa_footer import AnvisaFooter


# Verificar se Tkinter está disponível
def _tk_available():
    """Verifica se Tkinter está disponível no ambiente."""
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


TK_AVAILABLE = _tk_available()
requires_display = pytest.mark.skipif(
    not TK_AVAILABLE,
    reason="Tkinter display não disponível (ambiente sem GUI)",
)


@pytest.fixture
def root():
    """Fixture para criar root window."""
    if not TK_AVAILABLE:
        pytest.skip("Tkinter display não disponível")
    window = tk.Tk()
    yield window
    window.destroy()


@requires_display
def test_footer_creation(root):
    """Testa criação básica do footer."""
    footer = AnvisaFooter(
        root,
        default_process="Alteração do Responsável Legal",
        base_prefix="org123/client456",
        org_id="org123",
    )

    assert footer._base_prefix == "org123/client456"
    assert footer._org_id == "org123"
    assert footer._process_var.get() == "Alteração do Responsável Legal"
    assert len(footer._selected_files) == 0


@requires_display
def test_select_pdfs_empty_selection(root):
    """Testa quando usuário cancela seleção de arquivos."""
    footer = AnvisaFooter(
        root,
        default_process="Alteração do Responsável Legal",
        base_prefix="org123/client456",
        org_id="org123",
    )

    with patch("tkinter.filedialog.askopenfilenames", return_value=()):
        footer._on_select_pdfs()

    assert len(footer._selected_files) == 0
    assert str(footer._btn_upload.cget("state")) == "disabled"


@requires_display
def test_select_pdfs_with_files(root):
    """Testa seleção de arquivos PDF."""
    footer = AnvisaFooter(
        root,
        default_process="Alteração do Responsável Legal",
        base_prefix="org123/client456",
        org_id="org123",
    )

    mock_files = ("/path/to/file1.pdf", "/path/to/file2.pdf")

    with patch("tkinter.filedialog.askopenfilenames", return_value=mock_files):
        footer._on_select_pdfs()

    assert len(footer._selected_files) == 2
    assert str(footer._btn_upload.cget("state")) == "normal"
    assert "2 arquivo(s) selecionado(s)" in footer._files_label_var.get()


@requires_display
def test_upload_without_files(root):
    """Testa upload sem arquivos selecionados."""
    footer = AnvisaFooter(
        root,
        default_process="Alteração do Responsável Legal",
        base_prefix="org123/client456",
        org_id="org123",
    )

    with patch("tkinter.messagebox.showwarning") as mock_warning:
        footer._on_upload()

    mock_warning.assert_called_once()


@requires_display
def test_upload_success(root):
    """Testa upload bem-sucedido."""
    callback_called = False

    def on_complete():
        nonlocal callback_called
        callback_called = True

    footer = AnvisaFooter(
        root,
        default_process="Alteração do Responsável Legal",
        base_prefix="org123/client456",
        org_id="org123",
        on_upload_complete=on_complete,
    )

    footer._selected_files = ["/path/to/file1.pdf", "/path/to/file2.pdf"]

    with (
        patch("adapters.storage.api.upload_file") as mock_upload,
        patch("tkinter.messagebox.showinfo") as mock_info,
    ):
        footer._on_upload()

    assert mock_upload.call_count == 2
    mock_info.assert_called_once()
    assert callback_called
    assert len(footer._selected_files) == 0
    assert str(footer._btn_upload.cget("state")) == "disabled"


@requires_display
def test_upload_with_errors(root):
    """Testa upload com alguns arquivos falhando."""
    footer = AnvisaFooter(
        root,
        default_process="Alteração do Responsável Legal",
        base_prefix="org123/client456",
        org_id="org123",
    )

    footer._selected_files = ["/path/to/file1.pdf", "/path/to/file2.pdf"]

    def side_effect(*args, **kwargs):
        # Primeiro upload sucede, segundo falha
        if "file2" in args[0]:
            raise Exception("Upload failed")

    with (
        patch("adapters.storage.api.upload_file", side_effect=side_effect) as mock_upload,
        patch("tkinter.messagebox.showwarning") as mock_warning,
    ):
        footer._on_upload()

    assert mock_upload.call_count == 2
    mock_warning.assert_called_once()
