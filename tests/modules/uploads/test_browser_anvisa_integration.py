# -*- coding: utf-8 -*-
"""Testes de integração para contexto ANVISA no browser."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_browser_accepts_anvisa_context():
    """Testa que open_files_browser aceita anvisa_context."""
    from src.modules.uploads import open_files_browser

    # Mock Supabase
    mock_supabase = MagicMock()
    mock_supabase.auth.get_session.return_value.session.user.id = "user123"

    anvisa_context = {
        "request_type": "Alteração do Responsável Legal",
        "on_upload_complete": lambda: None,
    }

    with (
        patch("src.modules.uploads.views.browser.UploadsBrowserWindow") as mock_window,
        patch("tkinter.Toplevel"),
    ):
        mock_window.return_value = MagicMock()

        # Chamar com anvisa_context
        open_files_browser(
            parent=None,
            supabase=mock_supabase,
            client_id=123,
            org_id="org123",
            razao="Teste Farmácia",
            cnpj="12345678901234",
            anvisa_context=anvisa_context,
        )

        # Verificar que foi chamado com anvisa_context
        mock_window.assert_called_once()
        call_kwargs = mock_window.call_args.kwargs
        assert "anvisa_context" in call_kwargs
        assert call_kwargs["anvisa_context"] == anvisa_context


def test_browser_works_without_anvisa_context():
    """Testa que open_files_browser funciona sem anvisa_context (backward compatible)."""
    from src.modules.uploads import open_files_browser

    # Mock Supabase
    mock_supabase = MagicMock()
    mock_supabase.auth.get_session.return_value.session.user.id = "user123"

    with (
        patch("src.modules.uploads.views.browser.UploadsBrowserWindow") as mock_window,
        patch("tkinter.Toplevel"),
    ):
        mock_window.return_value = MagicMock()

        # Chamar sem anvisa_context
        open_files_browser(
            parent=None,
            supabase=mock_supabase,
            client_id=123,
            org_id="org123",
            razao="Teste Farmácia",
            cnpj="12345678901234",
        )

        # Verificar que foi chamado sem erros
        mock_window.assert_called_once()
        call_kwargs = mock_window.call_args.kwargs
        assert call_kwargs.get("anvisa_context") is None
