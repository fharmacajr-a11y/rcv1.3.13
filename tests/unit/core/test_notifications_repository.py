"""Testes unitários para notifications_repository.

Testa insert_notification com actor_user_id e error handling robusto.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from postgrest.exceptions import APIError


def test_insert_notification_uses_actor_user_id() -> None:
    """Testa que insert_notification usa actor_user_id (não actor_uid) no payload."""
    from infra.repositories.notifications_repository import insert_notification

    # Mock do supabase client
    mock_response = MagicMock()
    mock_response.data = [{"id": "test-id-123"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    # Patch do supabase dentro do módulo infra.supabase_client
    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar insert
        result = insert_notification(
            org_id="org-123",
            module="anvisa",
            event="created",
            message="Test message",
            actor_user_id="user-uuid-456",
            actor_email="test@example.com",
            client_id="789",
            request_id="req-xyz",
        )

        # Verificar sucesso
        assert result is True

        # Verificar que insert foi chamado com actor_user_id
        mock_table.insert.assert_called_once()
        call_args = mock_table.insert.call_args
        payload = call_args[0][0]  # Primeiro argumento posicional

        # Garantir que usa actor_user_id (NÃO actor_uid)
        assert "actor_user_id" in payload
        assert payload["actor_user_id"] == "user-uuid-456"
        assert "actor_uid" not in payload  # Nunca deve existir

        # Verificar outros campos
        assert payload["org_id"] == "org-123"
        assert payload["module"] == "anvisa"
        assert payload["event"] == "created"
        assert payload["message"] == "Test message"
        assert payload["actor_email"] == "test@example.com"
        assert payload["client_id"] == "789"
        assert payload["request_id"] == "req-xyz"
        assert payload["is_read"] is False


def test_insert_notification_api_error_with_string() -> None:
    """Testa que APIError com args[0] = str não quebra (retorna False e loga)."""
    from infra.repositories.notifications_repository import insert_notification

    # Mock do supabase client que lança APIError com string
    mock_table = MagicMock()

    # Criar APIError mock com args sendo string
    api_error = MagicMock(spec=APIError)
    api_error.args = ("PGRST204: column 'actor_uid' does not exist",)

    mock_table.insert.return_value.execute.side_effect = api_error

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar insert (não deve quebrar)
        result = insert_notification(
            org_id="org-123",
            module="anvisa",
            event="created",
            message="Test message",
            actor_user_id="user-uuid",
        )

        # Deve retornar False (erro)
        assert result is False


def test_insert_notification_api_error_with_dict() -> None:
    """Testa que APIError com args[0] = dict funciona corretamente."""
    from infra.repositories.notifications_repository import insert_notification

    # Mock do supabase client que lança APIError com dict estruturado
    mock_table = MagicMock()

    # APIError com args sendo um dict (erro PostgREST estruturado)
    error_dict = {
        "code": "PGRST204",
        "message": "column 'actor_uid' does not exist",
        "details": "Column not found in table",
        "hint": "Check schema definition",
    }
    # Criar APIError mock com args sendo dict
    api_error = MagicMock(spec=APIError)
    api_error.args = (error_dict,)

    mock_table.insert.return_value.execute.side_effect = api_error

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar insert (não deve quebrar)
        result = insert_notification(
            org_id="org-123",
            module="anvisa",
            event="created",
            message="Test message",
        )

        # Deve retornar False (erro)
        assert result is False


def test_insert_notification_without_actor() -> None:
    """Testa insert sem actor (campos opcionais)."""
    from infra.repositories.notifications_repository import insert_notification

    # Mock do supabase client
    mock_response = MagicMock()
    mock_response.data = [{"id": "test-id-789"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar insert sem actor
        result = insert_notification(
            org_id="org-123",
            module="anvisa",
            event="created",
            message="Test message",
            # Sem actor_user_id e actor_email
        )

        # Verificar sucesso
        assert result is True

        # Verificar payload NÃO contém actor_user_id (campo opcional)
        call_args = mock_table.insert.call_args
        payload = call_args[0][0]

        assert "actor_user_id" not in payload
        assert "actor_email" not in payload
        assert payload["org_id"] == "org-123"


def test_notifications_repository_adapter() -> None:
    """Testa que NotificationsRepositoryAdapter usa actor_user_id."""
    from infra.repositories.notifications_repository import NotificationsRepositoryAdapter

    adapter = NotificationsRepositoryAdapter()

    # Mock do supabase client
    mock_response = MagicMock()
    mock_response.data = [{"id": "adapter-test-id"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar via adapter
        result = adapter.insert_notification(
            org_id="org-adapter",
            module="test",
            event="test_event",
            message="Adapter test",
            actor_user_id="adapter-user-id",
            actor_email="adapter@test.com",
        )

        # Verificar sucesso
        assert result is True

        # Verificar que insert foi chamado com actor_user_id
        call_args = mock_table.insert.call_args
        payload = call_args[0][0]

        assert "actor_user_id" in payload
        assert payload["actor_user_id"] == "adapter-user-id"
        assert "actor_uid" not in payload
