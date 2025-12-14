# -*- coding: utf-8 -*-
"""Testes para garantir compatibilidade SUPABASE_KEY → SUPABASE_ANON_KEY."""

from unittest.mock import patch


def test_supabase_client_accepts_supabase_key_fallback(monkeypatch):
    """Verifica que SUPABASE_KEY funciona como fallback de SUPABASE_ANON_KEY."""
    # Limpar variáveis primeiro
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key-12345")

    # Reset singleton para forçar recriação
    import infra.supabase.db_client as db_client

    db_client._SUPABASE_SINGLETON = None
    db_client._SINGLETON_REUSE_LOGGED = False

    # Mock create_client to avoid real connection
    with patch("infra.supabase.db_client.create_client") as mock_create:
        mock_create.return_value = object()

        # Deve aceitar sem erro
        db_client.get_supabase()

        # Verificar que create_client foi chamado com a key correta
        assert mock_create.called
        call_args = mock_create.call_args
        assert call_args[0][1] == "test-key-12345", "Deve usar SUPABASE_KEY como fallback"


def test_supabase_client_prefers_anon_key_over_key(monkeypatch):
    """Verifica que SUPABASE_ANON_KEY tem prioridade sobre SUPABASE_KEY."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "old-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "new-anon-key")

    import infra.supabase.db_client as db_client

    db_client._SUPABASE_SINGLETON = None
    db_client._SINGLETON_REUSE_LOGGED = False

    with patch("infra.supabase.db_client.create_client") as mock_create:
        mock_create.return_value = object()

        db_client.get_supabase()

        call_args = mock_create.call_args
        assert call_args[0][1] == "new-anon-key", "Deve preferir SUPABASE_ANON_KEY"


def test_supabase_client_raises_if_no_key(monkeypatch):
    """Verifica que erro é claro quando nenhuma key está presente."""
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")

    import infra.supabase.db_client as db_client
    from infra.supabase import types as supa_types

    # Limpar singleton e módulo types
    db_client._SUPABASE_SINGLETON = None
    monkeypatch.setattr(supa_types, "SUPABASE_URL", None)
    monkeypatch.setattr(supa_types, "SUPABASE_ANON_KEY", None)

    try:
        db_client.get_supabase()
        assert False, "Deveria ter levantado RuntimeError"
    except RuntimeError as e:
        assert "SUPABASE_ANON_KEY" in str(e) or "SUPABASE_KEY" in str(e)
