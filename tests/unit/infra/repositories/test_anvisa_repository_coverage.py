"""Testes para aumentar cobertura do anvisa_requests_repository.

Foca em cobrir casos de edge/erro não cobertos pelos testes existentes:
- Exceções em _get_supabase_and_user
- Exceções em _resolve_org_id
- update_request_status: fallback sem org_id, count=0, data vazio
- delete_request: casos de sucesso e falha
- Funções auxiliares
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_get_supabase_and_user_no_user_id() -> None:
    """Testa _get_supabase_and_user quando user.id é None."""
    from infra.repositories.anvisa_requests_repository import _get_supabase_and_user

    # Mock do supabase com user sem ID
    mock_user = MagicMock()
    mock_user.id = None

    mock_resp = MagicMock()
    mock_resp.user = mock_user

    mock_auth = MagicMock()
    mock_auth.get_user.return_value = mock_resp

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.auth = mock_auth

        # Deve lançar RuntimeError
        with pytest.raises(RuntimeError, match="Usuário não autenticado"):
            _get_supabase_and_user()


def test_get_supabase_and_user_auth_exception() -> None:
    """Testa _get_supabase_and_user quando auth.get_user lança exceção."""
    from infra.repositories.anvisa_requests_repository import _get_supabase_and_user

    # Mock que lança exceção
    mock_auth = MagicMock()
    mock_auth.get_user.side_effect = Exception("Connection timeout")

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.auth = mock_auth

        # Deve propagar como RuntimeError
        with pytest.raises(RuntimeError, match="Falha na autenticação"):
            _get_supabase_and_user()


def test_resolve_org_id_no_membership() -> None:
    """Testa _resolve_org_id quando usuário não tem membership."""
    from infra.repositories.anvisa_requests_repository import _resolve_org_id

    # Mock retornando lista vazia
    mock_response = MagicMock()
    mock_response.data = []

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value = mock_execute

        # Deve lançar RuntimeError
        with pytest.raises(RuntimeError, match="Organização não encontrada"):
            _resolve_org_id("user-without-org")


def test_resolve_org_id_query_exception() -> None:
    """Testa _resolve_org_id quando query lança exceção."""
    from infra.repositories.anvisa_requests_repository import _resolve_org_id

    # Mock que lança exceção
    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.side_effect = Exception("Database error")

        # Deve propagar como RuntimeError
        with pytest.raises(RuntimeError, match="Falha ao obter organização"):
            _resolve_org_id("user-123")


def test_list_requests_exception() -> None:
    """Testa list_requests quando query lança exceção."""
    from infra.repositories.anvisa_requests_repository import list_requests

    # Mock que lança exceção
    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.side_effect = RuntimeError("Network error")

        # Deve propagar RuntimeError
        with pytest.raises(RuntimeError, match="Falha ao carregar demandas"):
            list_requests("org-error")


def test_update_request_status_invalid_status() -> None:
    """Testa update_request_status com status inválido."""
    from infra.repositories.anvisa_requests_repository import update_request_status

    # Chamar com status inválido
    result = update_request_status("req-123", "invalid_status")

    # Deve retornar False sem lançar exceção
    assert result is False


def test_update_request_status_fallback_without_org_id() -> None:
    """Testa update_request_status quando falha ao obter org_id e usa fallback."""
    from infra.repositories.anvisa_requests_repository import update_request_status

    # Mock: _get_supabase_and_user lança exceção, força fallback
    # Mock: update com sucesso no fallback
    mock_response = MagicMock()
    mock_response.data = [{"id": "req-456", "status": "draft"}]

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_eq2 = MagicMock()
    mock_eq2.eq.return_value = mock_execute

    mock_eq1 = MagicMock()
    mock_eq1.eq.return_value = mock_eq2

    mock_update = MagicMock()
    mock_update.update.return_value = mock_eq1

    mock_table = MagicMock()
    mock_table.table.return_value = mock_update

    with patch("infra.supabase_client.supabase", mock_table):
        # Mock _get_supabase_and_user para lançar exceção
        with patch("infra.repositories.anvisa_requests_repository._get_supabase_and_user") as mock_get_user:
            mock_get_user.side_effect = RuntimeError("User not found")

            # Executar (deve usar fallback)
            result = update_request_status("req-456", "draft")

            # Verificar sucesso
            assert result is True


def test_update_request_status_no_rows_affected() -> None:
    """Testa update_request_status quando 0 linhas são atualizadas."""
    from infra.repositories.anvisa_requests_repository import update_request_status

    # Mock: response com data vazio e count=0
    mock_response = MagicMock()
    mock_response.data = []
    mock_response.count = 0

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_eq2 = MagicMock()
    mock_eq2.eq.return_value = mock_execute

    mock_eq1 = MagicMock()
    mock_eq1.eq.return_value = mock_eq2

    mock_update = MagicMock()
    mock_update.update.return_value = mock_eq1

    mock_table = MagicMock()
    mock_table.table.return_value = mock_update

    # Mock _get_supabase_and_user
    with patch("infra.supabase_client.supabase", mock_table):
        with patch("infra.repositories.anvisa_requests_repository._get_supabase_and_user") as mock_get_user:
            mock_get_user.return_value = (mock_table, "user-123")

            # Mock _resolve_org_id
            with patch("infra.repositories.anvisa_requests_repository._resolve_org_id") as mock_resolve:
                mock_resolve.return_value = "org-123"

                # Executar
                result = update_request_status("req-nonexistent", "draft")

                # Deve retornar False (0 linhas afetadas)
                assert result is False


def test_update_request_status_data_empty_but_count_not_zero() -> None:
    """Testa update_request_status quando data vazio mas count != 0."""
    from infra.repositories.anvisa_requests_repository import update_request_status

    # Mock: response com data vazio mas count=1 (edge case)
    mock_response = MagicMock()
    mock_response.data = []
    mock_response.count = 1

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_eq2 = MagicMock()
    mock_eq2.eq.return_value = mock_execute

    mock_eq1 = MagicMock()
    mock_eq1.eq.return_value = mock_eq2

    mock_update = MagicMock()
    mock_update.update.return_value = mock_eq1

    mock_table = MagicMock()
    mock_table.table.return_value = mock_update

    with patch("infra.supabase_client.supabase", mock_table):
        with patch("infra.repositories.anvisa_requests_repository._get_supabase_and_user") as mock_get_user:
            mock_get_user.return_value = (mock_table, "user-123")

            with patch("infra.repositories.anvisa_requests_repository._resolve_org_id") as mock_resolve:
                mock_resolve.return_value = "org-123"

                # Executar
                result = update_request_status("req-edge", "draft")

                # Deve retornar False (data vazio)
                assert result is False


def test_update_request_status_generic_exception() -> None:
    """Testa update_request_status quando ocorre exceção genérica."""
    from infra.repositories.anvisa_requests_repository import update_request_status

    # Mock que lança exceção no update
    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.side_effect = Exception("Unexpected error")

        # Executar (não deve propagar exceção)
        result = update_request_status("req-error", "draft")

        # Deve retornar False
        assert result is False


def test_delete_request_success() -> None:
    """Testa delete_request com sucesso."""
    from infra.repositories.anvisa_requests_repository import delete_request

    # Mock de sucesso
    mock_response = MagicMock()
    mock_response.data = [{"id": "req-delete-1"}]

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_eq = MagicMock()
    mock_eq.eq.return_value = mock_execute

    mock_delete = MagicMock()
    mock_delete.delete.return_value = mock_eq

    mock_table = MagicMock()
    mock_table.table.return_value = mock_delete

    with patch("infra.supabase_client.supabase", mock_table):
        # Executar
        result = delete_request("req-delete-1")

        # Verificar sucesso
        assert result is True


def test_delete_request_no_rows_deleted() -> None:
    """Testa delete_request quando nenhuma linha é deletada."""
    from infra.repositories.anvisa_requests_repository import delete_request

    # Mock com data vazio
    mock_response = MagicMock()
    mock_response.data = []

    mock_execute = MagicMock()
    mock_execute.execute.return_value = mock_response

    mock_eq = MagicMock()
    mock_eq.eq.return_value = mock_execute

    mock_delete = MagicMock()
    mock_delete.delete.return_value = mock_eq

    mock_table = MagicMock()
    mock_table.table.return_value = mock_delete

    with patch("infra.supabase_client.supabase", mock_table):
        # Executar
        result = delete_request("req-nonexistent")

        # Deve retornar False
        assert result is False


def test_delete_request_exception() -> None:
    """Testa delete_request quando ocorre exceção."""
    from infra.repositories.anvisa_requests_repository import delete_request

    # Mock que lança exceção
    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.side_effect = Exception("Delete failed")

        # Executar (deve propagar RuntimeError)
        with pytest.raises(RuntimeError, match="Falha ao excluir demanda"):
            delete_request("req-error")
