# -*- coding: utf-8 -*-
"""Testes para o visualizador de PDF do browser."""

from __future__ import annotations

from unittest.mock import patch


def test_open_pdf_viewer_with_signature_keyword():
    """Testa que _open_pdf_viewer aceita signature= (compatibilidade)."""
    from src.modules.uploads.views.browser import UploadsBrowserWindow

    # Mock completo para não criar janela Tkinter
    with (
        patch("src.modules.uploads.views.browser.open_pdf_viewer") as mock_viewer,
        patch.object(UploadsBrowserWindow, "__init__", return_value=None),
    ):
        mock_viewer.return_value = None

        # Criar instância sem inicializar (já mockado __init__)
        browser = UploadsBrowserWindow.__new__(UploadsBrowserWindow)

        # Testar chamada com signature= (formato antigo)
        data = b"fake pdf content"
        browser._open_pdf_viewer(
            data_bytes=data,
            display_name="test.pdf",
            signature="test_signature",
        )

        # Verificar que open_pdf_viewer foi chamado
        mock_viewer.assert_called_once()


def test_open_pdf_viewer_with_underscore_signature():
    """Testa que _open_pdf_viewer aceita _signature= (formato preferido)."""
    from src.modules.uploads.views.browser import UploadsBrowserWindow

    # Mock completo para não criar janela Tkinter
    with (
        patch("src.modules.uploads.views.browser.open_pdf_viewer") as mock_viewer,
        patch.object(UploadsBrowserWindow, "__init__", return_value=None),
    ):
        mock_viewer.return_value = None

        # Criar instância sem inicializar
        browser = UploadsBrowserWindow.__new__(UploadsBrowserWindow)

        # Testar chamada com _signature= (formato preferido)
        data = b"fake pdf content"
        browser._open_pdf_viewer(
            data_bytes=data,
            display_name="test.pdf",
            _signature="test_signature",
        )

        # Verificar que open_pdf_viewer foi chamado
        mock_viewer.assert_called_once()


def test_open_pdf_viewer_signature_precedence():
    """Testa que _signature tem precedência sobre signature."""
    from src.modules.uploads.views.browser import UploadsBrowserWindow

    # Mock completo para não criar janela Tkinter
    with (
        patch("src.modules.uploads.views.browser.open_pdf_viewer") as mock_viewer,
        patch.object(UploadsBrowserWindow, "__init__", return_value=None),
    ):
        mock_viewer.return_value = None

        # Criar instância sem inicializar
        browser = UploadsBrowserWindow.__new__(UploadsBrowserWindow)

        # Testar chamada com ambos (deve usar _signature)
        data = b"fake pdf content"
        browser._open_pdf_viewer(
            data_bytes=data,
            display_name="test.pdf",
            _signature="preferred",
            signature="fallback",
        )

        # Verificar que open_pdf_viewer foi chamado
        mock_viewer.assert_called_once()
