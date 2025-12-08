# -*- coding: utf-8 -*-
"""Unit tests for src/features/tasks/repository.py.

Tests the data access layer for rc_tasks table, mocking the Supabase client
to verify correct query construction and response handling.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES - Mock do cliente Supabase
# ============================================================================


@pytest.fixture
def mock_supabase_client():
    """Mock do cliente Supabase para testes de repository."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    # Configurar chain methods
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.limit.return_value = mock_table

    return mock_client, mock_table


# ============================================================================
# TEST GROUP: list_tasks_for_org()
# ============================================================================


class TestListTasksForOrg:
    """Testes para list_tasks_for_org() - filtros e combinações."""

    def test_list_tasks_basic_org_filter(self, mock_supabase_client):
        """Cenário: Listagem básica filtrando apenas por org_id."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        # Dados mockados
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "task-1",
                "org_id": "org-123",
                "title": "Tarefa 1",
                "status": "pending",
                "priority": "normal",
            },
            {
                "id": "task-2",
                "org_id": "org-123",
                "title": "Tarefa 2",
                "status": "done",
                "priority": "high",
            },
        ]
        mock_table.execute.return_value = mock_result

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_tasks_for_org("org-123")

        assert len(result) == 2
        assert result[0]["id"] == "task-1"
        assert result[1]["id"] == "task-2"

        # Verificar que eq foi chamado com org_id
        mock_table.eq.assert_any_call("org_id", "org-123")
        mock_client.table.assert_called_with("rc_tasks")

    def test_list_tasks_with_due_date_filter(self, mock_supabase_client):
        """Cenário: Filtro por data de vencimento específica."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "task-1", "org_id": "org-123", "due_date": "2025-01-15"},
        ]
        mock_table.execute.return_value = mock_result

        test_date = date(2025, 1, 15)

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_tasks_for_org("org-123", due_date=test_date)

        assert len(result) == 1

        # Verificar que eq foi chamado com due_date
        calls = mock_table.eq.call_args_list
        due_date_calls = [c for c in calls if c[0][0] == "due_date"]
        assert len(due_date_calls) == 1
        assert due_date_calls[0][0][1] == "2025-01-15"

    def test_list_tasks_with_status_filter(self, mock_supabase_client):
        """Cenário: Filtro por status."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "task-1", "org_id": "org-123", "status": "pending"},
        ]
        mock_table.execute.return_value = mock_result

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_tasks_for_org("org-123", status="pending")

        assert len(result) == 1
        assert result[0]["status"] == "pending"

        # Verificar que eq foi chamado com status
        calls = mock_table.eq.call_args_list
        status_calls = [c for c in calls if c[0][0] == "status"]
        assert len(status_calls) == 1
        assert status_calls[0][0][1] == "pending"

    def test_list_tasks_with_assigned_to_filter(self, mock_supabase_client):
        """Cenário: Filtro por usuário responsável."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "task-1", "org_id": "org-123", "assigned_to": "user-456"},
        ]
        mock_table.execute.return_value = mock_result

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_tasks_for_org("org-123", assigned_to="user-456")

        assert len(result) == 1

        # Verificar que eq foi chamado com assigned_to
        calls = mock_table.eq.call_args_list
        assigned_calls = [c for c in calls if c[0][0] == "assigned_to"]
        assert len(assigned_calls) == 1
        assert assigned_calls[0][0][1] == "user-456"

    def test_list_tasks_with_all_filters(self, mock_supabase_client):
        """Cenário: Combinação de todos os filtros."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "task-1", "org_id": "org-123"}]
        mock_table.execute.return_value = mock_result

        test_date = date(2025, 1, 15)

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_tasks_for_org(
                "org-123",
                due_date=test_date,
                status="pending",
                assigned_to="user-456",
            )

        assert len(result) == 1

        # Verificar que eq foi chamado com todos os filtros
        calls = mock_table.eq.call_args_list
        assert len(calls) == 4  # org_id, due_date, status, assigned_to

    def test_list_tasks_returns_empty_list_when_no_data(self, mock_supabase_client):
        """Cenário: Retorna lista vazia quando não há dados."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_tasks_for_org("org-123")

        assert result == []

    def test_list_tasks_handles_none_data(self, mock_supabase_client):
        """Cenário: Trata resposta com data=None."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = None
        mock_table.execute.return_value = mock_result

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_tasks_for_org("org-123")

        assert result == []


# ============================================================================
# TEST GROUP: count_tasks_for_org()
# ============================================================================


class TestCountTasksForOrg:
    """Testes para count_tasks_for_org() - contagem com filtros."""

    def test_count_tasks_basic(self, mock_supabase_client):
        """Cenário: Contagem básica de tarefas."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.count = 5
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.count_tasks_for_org("org-123")

        assert result == 5

        # Verificar que select foi chamado com count="exact"
        mock_table.select.assert_called_with("id", count="exact")

    def test_count_tasks_with_due_date_filter(self, mock_supabase_client):
        """Cenário: Contagem com filtro de data."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.count = 3
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        test_date = date(2025, 1, 15)

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.count_tasks_for_org("org-123", due_date=test_date)

        assert result == 3

        # Verificar que eq foi chamado com due_date
        calls = mock_table.eq.call_args_list
        due_date_calls = [c for c in calls if c[0][0] == "due_date"]
        assert len(due_date_calls) == 1

    def test_count_tasks_with_status_filter(self, mock_supabase_client):
        """Cenário: Contagem com filtro de status."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.count = 2
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.count_tasks_for_org("org-123", status="pending")

        assert result == 2

        # Verificar que eq foi chamado com status
        calls = mock_table.eq.call_args_list
        status_calls = [c for c in calls if c[0][0] == "status"]
        assert len(status_calls) == 1

    def test_count_tasks_fallback_to_len_when_no_count(self, mock_supabase_client):
        """Cenário: Fallback para len(data) quando count não está disponível."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.count = None
        mock_result.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        mock_table.execute.return_value = mock_result

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            result = repository.count_tasks_for_org("org-123")

        assert result == 3


# ============================================================================
# TEST GROUP: Tratamento de erros
# ============================================================================


class TestErrorHandling:
    """Testes para tratamento de erros da API."""

    def test_list_tasks_handles_api_error(self, mock_supabase_client):
        """Cenário: Trata erro da API corretamente."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        # Simular erro da API usando MagicMock para evitar dependência do formato do construtor
        api_error = MagicMock(spec=repository.PostgrestAPIError)
        api_error.code = "500"
        api_error.details = "Internal server error"
        api_error.hint = "Check server status"
        api_error.message = "Connection failed"
        # Fazer com que isinstance() retorne True para PostgrestAPIError
        mock_table.execute.side_effect = repository.PostgrestAPIError(
            {
                "message": "Connection failed",
                "code": "500",
                "details": "Internal server error",
                "hint": "Check server status",
            }
        )

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                repository.list_tasks_for_org("org-123")

        assert "SELECT" in str(exc_info.value)

    def test_count_tasks_handles_api_error(self, mock_supabase_client):
        """Cenário: count_tasks_for_org trata erro da API."""
        from src.features.tasks import repository

        mock_client, mock_table = mock_supabase_client

        # Simular erro da API com formato correto
        mock_table.execute.side_effect = repository.PostgrestAPIError({"message": "Query failed"})

        with patch("src.features.tasks.repository.get_supabase_client", return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                repository.count_tasks_for_org("org-123")

        assert "COUNT" in str(exc_info.value)
