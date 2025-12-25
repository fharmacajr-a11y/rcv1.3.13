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
    mock_insert_response = MagicMock()
    mock_insert_response.data = [{"id": "test-id-123"}]

    # Mock do pre-check (não existe duplicado)
    mock_check_response = MagicMock()
    mock_check_response.data = []  # Vazio = não existe

    mock_table = MagicMock()
    # Configurar select para pre-check retornar vazio
    mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_check_response
    # Configurar insert para retornar sucesso
    mock_table.insert.return_value.execute.return_value = mock_insert_response

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


def test_list_notifications_with_exclude_actor_email() -> None:
    """Testa que list_notifications filtra notificações do próprio autor."""
    from infra.repositories.notifications_repository import list_notifications

    # Mock do supabase client
    mock_response = MagicMock()
    mock_response.data = [
        {"id": "1", "message": "Notif 1", "actor_email": "other@example.com"},
        {"id": "2", "message": "Notif 2", "actor_email": "another@example.com"},
    ]

    mock_query = MagicMock()
    mock_query.neq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value = mock_query

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar list com exclude_actor_email
        notifications = list_notifications(org_id="org-123", limit=10, exclude_actor_email="current_user@example.com")

        # Verificar que neq foi chamado com actor_email
        mock_query.neq.assert_called_once_with("actor_email", "current_user@example.com")

        # Verificar resultado
        assert len(notifications) == 2


def test_count_unread_with_exclude_actor_email() -> None:
    """Testa que count_unread filtra notificações do próprio autor."""
    from infra.repositories.notifications_repository import count_unread

    # Mock do supabase client
    mock_response = MagicMock()
    mock_response.count = 5

    mock_query = MagicMock()
    mock_query.neq.return_value.execute.return_value = mock_response

    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.eq.return_value = mock_query

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar count com exclude_actor_email
        count = count_unread(org_id="org-123", exclude_actor_email="current_user@example.com")

        # Verificar que neq foi chamado com actor_email
        mock_query.neq.assert_called_once_with("actor_email", "current_user@example.com")

        # Verificar resultado
        assert count == 5


def test_insert_notification_dedupe_existing() -> None:
    """Testa que insert_notification não duplica quando request_id já existe."""
    from infra.repositories.notifications_repository import insert_notification

    # Mock do supabase client - simular que notificação já existe
    mock_existing_response = MagicMock()
    mock_existing_response.data = [{"id": "existing-id"}]

    mock_select = MagicMock()
    mock_select.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_existing_response

    mock_table = MagicMock()

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table
        # Mock select para pre-check
        mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_existing_response

        # Executar insert com request_id que já existe
        result = insert_notification(
            org_id="org-123",
            module="hub_notes",
            event="created",
            message="Duplicate test",
            request_id="hub_notes_created:note-123",
        )

        # Deve retornar True (dedupe bem-sucedido)
        assert result is True

        # Verificar que insert NÃO foi chamado (dedupe impediu)
        mock_table.insert.assert_not_called()


def test_insert_notification_dedupe_new() -> None:
    """Testa que insert_notification cria notificação quando request_id não existe."""
    from infra.repositories.notifications_repository import insert_notification

    # Mock do supabase client - simular que notificação NÃO existe
    mock_existing_response = MagicMock()
    mock_existing_response.data = []  # Vazio = não existe

    mock_insert_response = MagicMock()
    mock_insert_response.data = [{"id": "new-id"}]

    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_existing_response
    mock_table.insert.return_value.execute.return_value = mock_insert_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar insert com request_id novo
        result = insert_notification(
            org_id="org-123",
            module="hub_notes",
            event="created",
            message="New notification",
            request_id="hub_notes_created:note-456",
        )

        # Deve retornar True (inserido com sucesso)
        assert result is True

        # Verificar que insert FOI chamado (não havia duplicado)
        mock_table.insert.assert_called_once()


def test_insert_notification_normalizes_prefixed_uuid_request_id() -> None:
    """Testa normalização de request_id com formato 'prefixo:<uuid>'."""
    from infra.repositories.notifications_repository import insert_notification

    # UUID válido para teste
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    request_id_with_prefix = f"hub_notes_created:{test_uuid}"

    # Mock do supabase client
    mock_check_response = MagicMock()
    mock_check_response.data = []  # Não existe duplicado

    mock_insert_response = MagicMock()
    mock_insert_response.data = [{"id": "new-id"}]

    mock_table = MagicMock()
    # Mock do select para pre-check
    mock_select_chain = mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value
    mock_select_chain.execute.return_value = mock_check_response

    # Mock do insert
    mock_table.insert.return_value.execute.return_value = mock_insert_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar insert com request_id prefixado
        result = insert_notification(
            org_id="org-123",
            module="hub_notes",
            event="created",
            message="Test with prefixed UUID",
            request_id=request_id_with_prefix,
        )

        # Deve retornar True (sucesso)
        assert result is True

        # Verificar que pre-check usou UUID normalizado (sem prefixo)
        # A quarta chamada a .eq() é para request_id
        select_calls = mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.call_args_list
        assert len(select_calls) > 0
        request_id_check = select_calls[0][0]  # Primeiro argumento posicional
        assert request_id_check[0] == "request_id"
        assert request_id_check[1] == test_uuid  # UUID sem prefixo

        # Verificar que insert usou UUID normalizado (sem prefixo)
        mock_table.insert.assert_called_once()
        insert_args = mock_table.insert.call_args
        payload = insert_args[0][0]
        assert payload["request_id"] == test_uuid  # UUID sem prefixo


def test_extract_uuid_from_request_id_helper() -> None:
    """Testa helper _extract_uuid_from_request_id diretamente."""
    from infra.repositories.notifications_repository import _extract_uuid_from_request_id

    test_uuid = "550e8400-e29b-41d4-a716-446655440000"

    # Caso 1: UUID puro
    assert _extract_uuid_from_request_id(test_uuid) == test_uuid

    # Caso 2: Prefixo com UUID
    assert _extract_uuid_from_request_id(f"hub_notes_created:{test_uuid}") == test_uuid

    # Caso 3: Múltiplos ":" (pega último)
    assert _extract_uuid_from_request_id(f"prefix:sub:{test_uuid}") == test_uuid

    # Caso 4: String inválida (não é UUID)
    assert _extract_uuid_from_request_id("invalid-string") is None

    # Caso 5: Vazio
    assert _extract_uuid_from_request_id("") is None

    # Caso 6: Prefixo com string inválida (não UUID)
    assert _extract_uuid_from_request_id("hub_notes_created:note-123") is None
