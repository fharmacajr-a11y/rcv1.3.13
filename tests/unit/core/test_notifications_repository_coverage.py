"""Testes unitários para aumentar cobertura do notifications_repository.

Cobre:
- list_notifications: select completo, order/limit, lista vazia, exceções
- count_unread: filtros corretos, retorno int, exceções
- mark_all_read: casos de sucesso já cobertos, adicionar edge cases
- insert_notification: error handling (APIError estruturado)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from postgrest.exceptions import APIError


def test_list_notifications_success() -> None:
    """Testa list_notifications com sucesso e verifica colunas selecionadas."""
    from infra.repositories.notifications_repository import list_notifications

    # Mock do supabase client
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "notif-1",
            "created_at": "2025-12-20T14:30:00Z",
            "message": "Test message 1",
            "is_read": False,
            "module": "anvisa",
            "event": "created",
            "client_id": "client-1",
            "request_id": "req-1",
            "actor_email": "user@example.com",
        },
        {
            "id": "notif-2",
            "created_at": "2025-12-20T13:00:00Z",
            "message": "Test message 2",
            "is_read": True,
            "module": "sites",
            "event": "updated",
            "client_id": "client-2",
            "request_id": "req-2",
            "actor_email": "admin@example.com",
        },
    ]

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_limit = MagicMock()
    mock_limit.limit.return_value = mock_execute

    mock_order = MagicMock()
    mock_order.order.return_value = mock_limit

    mock_eq = MagicMock()
    mock_eq.eq.return_value = mock_order

    mock_select = MagicMock()
    mock_select.select.return_value = mock_eq

    mock_table = MagicMock()
    mock_table.table.return_value = mock_select

    with patch("infra.supabase_client.supabase", mock_table):
        # Executar
        result = list_notifications("org-123", limit=50)

        # Verificar resultado
        assert len(result) == 2
        assert result[0]["id"] == "notif-1"
        assert result[1]["id"] == "notif-2"

        # Verificar que select incluiu todas as colunas esperadas
        mock_select.select.assert_called_once()
        select_arg = mock_select.select.call_args[0][0]
        expected_cols = [
            "id",
            "created_at",
            "message",
            "is_read",
            "module",
            "event",
            "client_id",
            "request_id",
            "actor_email",
        ]
        for col in expected_cols:
            assert col in select_arg, f"Coluna {col} não incluída no select"

        # Verificar que eq foi chamado com org_id
        mock_eq.eq.assert_called_once_with("org_id", "org-123")

        # Verificar que order foi chamado com created_at desc
        mock_order.order.assert_called_once_with("created_at", desc=True)

        # Verificar que limit foi chamado com valor correto
        mock_limit.limit.assert_called_once_with(50)


def test_list_notifications_empty_result() -> None:
    """Testa list_notifications quando não há notificações."""
    from infra.repositories.notifications_repository import list_notifications

    # Mock retornando lista vazia
    mock_response = MagicMock()
    mock_response.data = []

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value = (
            mock_execute
        )

        # Executar
        result = list_notifications("org-456")

        # Deve retornar lista vazia
        assert result == []
        assert isinstance(result, list)


def test_list_notifications_exception() -> None:
    """Testa list_notifications quando ocorre exceção."""
    from infra.repositories.notifications_repository import list_notifications

    # Mock que lança exceção
    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.side_effect = Exception("Database connection error")

        # Executar (não deve propagar exceção)
        result = list_notifications("org-789")

        # Deve retornar lista vazia em caso de erro
        assert result == []


def test_list_notifications_response_data_none() -> None:
    """Testa list_notifications quando response.data é None."""
    from infra.repositories.notifications_repository import list_notifications

    # Mock com data = None
    mock_response = MagicMock()
    mock_response.data = None

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value = (
            mock_execute
        )

        # Executar
        result = list_notifications("org-999")

        # Deve retornar lista vazia (fallback)
        assert result == []


def test_count_unread_success() -> None:
    """Testa count_unread com sucesso e verifica filtros."""
    from infra.repositories.notifications_repository import count_unread

    # Mock do supabase client
    mock_response = MagicMock()
    mock_response.count = 5

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_eq_is_read = MagicMock()
    mock_eq_is_read.eq.return_value = mock_execute

    mock_eq_org = MagicMock()
    mock_eq_org.eq.return_value = mock_eq_is_read

    mock_select = MagicMock()
    mock_select.select.return_value = mock_eq_org

    mock_table = MagicMock()
    mock_table.table.return_value = mock_select

    with patch("infra.supabase_client.supabase", mock_table):
        # Executar
        result = count_unread("org-abc")

        # Verificar resultado
        assert result == 5
        assert isinstance(result, int)

        # Verificar que select foi chamado com count="exact"
        mock_select.select.assert_called_once_with("id", count="exact")

        # Verificar filtros: org_id e is_read
        # Primeira chamada eq: org_id
        mock_eq_org.eq.assert_called_once_with("org_id", "org-abc")
        # Segunda chamada eq: is_read=False
        mock_eq_is_read.eq.assert_called_once_with("is_read", False)


def test_count_unread_zero() -> None:
    """Testa count_unread quando não há notificações não lidas."""
    from infra.repositories.notifications_repository import count_unread

    # Mock retornando count=0
    mock_response = MagicMock()
    mock_response.count = 0

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value = mock_execute

        # Executar
        result = count_unread("org-def")

        # Deve retornar 0
        assert result == 0


def test_count_unread_exception() -> None:
    """Testa count_unread quando ocorre exceção."""
    from infra.repositories.notifications_repository import count_unread

    # Mock que lança exceção
    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.side_effect = Exception("Connection timeout")

        # Executar (não deve propagar exceção)
        result = count_unread("org-ghi")

        # Deve retornar 0 em caso de erro
        assert result == 0


def test_count_unread_count_none() -> None:
    """Testa count_unread quando response.count é None."""
    from infra.repositories.notifications_repository import count_unread

    # Mock com count = None
    mock_response = MagicMock()
    mock_response.count = None

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value = mock_execute

        # Executar
        result = count_unread("org-jkl")

        # Deve retornar 0 (fallback)
        assert result == 0


def test_insert_notification_rls_blocked() -> None:
    """Testa insert_notification quando RLS bloqueia (data vazia)."""
    from infra.repositories.notifications_repository import insert_notification

    # Mock retornando data vazia (bloqueado por RLS)
    mock_response = MagicMock()
    mock_response.data = []

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_insert = MagicMock()
    mock_insert.insert.return_value = mock_execute

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_insert

        # Executar
        result = insert_notification(
            org_id="org-blocked",
            module="anvisa",
            event="created",
            message="Test",
            actor_user_id="user-1",
            actor_email="test@example.com",
        )

        # Deve retornar False (bloqueado)
        assert result is False


def test_insert_notification_api_error_dict() -> None:
    """Testa insert_notification quando APIError retorna dict estruturado."""
    from infra.repositories.notifications_repository import insert_notification

    # Criar mock de APIError com dict nos args
    error_data = {
        "message": "Row level security violation",
        "code": "42501",
        "details": "Policy check failed",
        "hint": "Check your RLS policies",
    }

    # Mock completo que simula APIError
    mock_api_error = MagicMock(spec=APIError)
    mock_api_error.args = (error_data,)

    mock_insert = MagicMock()
    mock_insert.insert.side_effect = mock_api_error

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_insert

        # Executar (não deve propagar exceção)
        result = insert_notification(
            org_id="org-error",
            module="sites",
            event="deleted",
            message="Error test",
            actor_user_id="user-2",
            actor_email="error@example.com",
        )

        # Deve retornar False
        assert result is False


def test_insert_notification_api_error_string() -> None:
    """Testa insert_notification quando APIError retorna string simples."""
    from infra.repositories.notifications_repository import insert_notification

    # Criar mock de APIError com string nos args
    mock_api_error = MagicMock(spec=APIError)
    mock_api_error.args = ("Simple error message",)

    mock_insert = MagicMock()
    mock_insert.insert.side_effect = mock_api_error

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_insert

        # Executar (não deve propagar exceção)
        result = insert_notification(
            org_id="org-error2",
            module="hub",
            event="updated",
            message="String error test",
            actor_user_id="user-3",
            actor_email="error2@example.com",
        )

        # Deve retornar False
        assert result is False


def test_insert_notification_generic_exception() -> None:
    """Testa insert_notification quando ocorre exceção genérica."""
    from infra.repositories.notifications_repository import insert_notification

    # Mock que lança exceção genérica
    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.side_effect = RuntimeError("Unexpected error")

        # Executar (não deve propagar exceção)
        result = insert_notification(
            org_id="org-error3",
            module="crm",
            event="sync",
            message="Generic error test",
            actor_user_id="user-4",
            actor_email="error3@example.com",
        )

        # Deve retornar False
        assert result is False


def test_notifications_repository_adapter_methods() -> None:
    """Testa que NotificationsRepositoryAdapter delega para funções corretas."""
    from infra.repositories.notifications_repository import NotificationsRepositoryAdapter

    adapter = NotificationsRepositoryAdapter()

    # Mock das funções do módulo
    with (
        patch("infra.repositories.notifications_repository.list_notifications") as mock_list,
        patch("infra.repositories.notifications_repository.count_unread") as mock_count,
        patch("infra.repositories.notifications_repository.mark_all_read") as mock_mark,
        patch("infra.repositories.notifications_repository.insert_notification") as mock_insert,
    ):
        mock_list.return_value = [{"id": "1"}]
        mock_count.return_value = 3
        mock_mark.return_value = True
        mock_insert.return_value = True

        # Testar cada método do adapter
        result_list = adapter.list_notifications("org-1", limit=10)
        assert result_list == [{"id": "1"}]
        mock_list.assert_called_once_with("org-1", 10)

        result_count = adapter.count_unread("org-2")
        assert result_count == 3
        mock_count.assert_called_once_with("org-2")

        result_mark = adapter.mark_all_read("org-3")
        assert result_mark is True
        mock_mark.assert_called_once_with("org-3")

        result_insert = adapter.insert_notification(
            org_id="org-4",
            module="test",
            event="test_event",
            message="Test adapter",
            actor_user_id="user-5",
            actor_email="adapter@example.com",
        )
        assert result_insert is True
        mock_insert.assert_called_once()
