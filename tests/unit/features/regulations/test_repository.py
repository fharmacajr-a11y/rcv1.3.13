# -*- coding: utf-8 -*-
"""Unit tests for src/features/regulations/repository.py.

Tests the data access layer for reg_obligations table, mocking the Supabase client
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
# TEST GROUP: list_obligations_for_org()
# ============================================================================


class TestListObligationsForOrg:
    """Testes para list_obligations_for_org() - filtros e combinações."""

    def test_list_obligations_basic_org_filter(self, mock_supabase_client):
        """Cenário: Listagem básica filtrando apenas por org_id."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        # Dados mockados
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "obl-1",
                "org_id": "org-123",
                "client_id": 1,
                "kind": "SNGPC",
                "title": "SNGPC Janeiro",
                "due_date": "2025-01-15",
                "status": "pending",
            },
            {
                "id": "obl-2",
                "org_id": "org-123",
                "client_id": 2,
                "kind": "FARMACIA_POPULAR",
                "title": "Farmácia Popular Janeiro",
                "due_date": "2025-01-20",
                "status": "done",
            },
        ]
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_obligations_for_org("org-123")

        assert len(result) == 2
        assert result[0]["id"] == "obl-1"
        assert result[1]["id"] == "obl-2"

        # Verificar que eq foi chamado com org_id
        mock_table.eq.assert_any_call("org_id", "org-123")
        mock_client.table.assert_called_with("reg_obligations")

    def test_list_obligations_with_date_range(self, mock_supabase_client):
        """Cenário: Filtro por período de datas."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "obl-1", "org_id": "org-123", "due_date": "2025-01-15"},
        ]
        mock_table.execute.return_value = mock_result

        start = date(2025, 1, 1)
        end = date(2025, 1, 31)

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_obligations_for_org("org-123", start_date=start, end_date=end)

        assert len(result) == 1

        # Verificar que gte e lte foram chamados
        mock_table.gte.assert_called_once_with("due_date", "2025-01-01")
        mock_table.lte.assert_called_once_with("due_date", "2025-01-31")

    def test_list_obligations_with_status_filter(self, mock_supabase_client):
        """Cenário: Filtro por status."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "obl-1", "org_id": "org-123", "status": "pending"},
        ]
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_obligations_for_org("org-123", status="pending")

        assert len(result) == 1
        assert result[0]["status"] == "pending"

        # Verificar que eq foi chamado com status
        calls = mock_table.eq.call_args_list
        status_calls = [c for c in calls if c[0][0] == "status"]
        assert len(status_calls) == 1
        assert status_calls[0][0][1] == "pending"

    def test_list_obligations_with_kind_filter(self, mock_supabase_client):
        """Cenário: Filtro por tipo de obrigação."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "obl-1", "org_id": "org-123", "kind": "SNGPC"},
        ]
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_obligations_for_org("org-123", kind="SNGPC")

        assert len(result) == 1

        # Verificar que eq foi chamado com kind
        calls = mock_table.eq.call_args_list
        kind_calls = [c for c in calls if c[0][0] == "kind"]
        assert len(kind_calls) == 1
        assert kind_calls[0][0][1] == "SNGPC"

    def test_list_obligations_with_limit(self, mock_supabase_client):
        """Cenário: Limitar número de resultados."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "obl-1", "org_id": "org-123"},
            {"id": "obl-2", "org_id": "org-123"},
        ]
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_obligations_for_org("org-123", limit=10)

        assert len(result) == 2

        # Verificar que limit foi chamado
        mock_table.limit.assert_called_once_with(10)

    def test_list_obligations_with_all_filters(self, mock_supabase_client):
        """Cenário: Combinação de todos os filtros."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "obl-1", "org_id": "org-123"}]
        mock_table.execute.return_value = mock_result

        start = date(2025, 1, 1)
        end = date(2025, 1, 31)

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_obligations_for_org(
                "org-123",
                start_date=start,
                end_date=end,
                status="pending",
                kind="SNGPC",
                limit=5,
            )

        assert len(result) == 1

        # Verificar que todos os filtros foram aplicados
        mock_table.gte.assert_called_once()
        mock_table.lte.assert_called_once()
        mock_table.limit.assert_called_once_with(5)

        # Verificar que eq foi chamado 3 vezes (org_id, status, kind)
        assert mock_table.eq.call_count == 3

    def test_list_obligations_returns_empty_list_when_no_data(self, mock_supabase_client):
        """Cenário: Retorna lista vazia quando não há dados."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_obligations_for_org("org-123")

        assert result == []

    def test_list_obligations_handles_none_data(self, mock_supabase_client):
        """Cenário: Trata resposta com data=None."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = None
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.list_obligations_for_org("org-123")

        assert result == []


# ============================================================================
# TEST GROUP: count_pending_obligations()
# ============================================================================


class TestCountPendingObligations:
    """Testes para count_pending_obligations() - contagem de pendentes."""

    def test_count_pending_obligations_basic(self, mock_supabase_client):
        """Cenário: Contagem básica de obrigações pendentes/atrasadas."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.count = 7
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.count_pending_obligations("org-123")

        assert result == 7

        # Verificar que select foi chamado com count="exact"
        mock_table.select.assert_called_with("id", count="exact")

        # Verificar que in_ foi chamado com status pending e overdue
        mock_table.in_.assert_called_once_with("status", ["pending", "overdue"])

    def test_count_pending_obligations_uses_correct_statuses(self, mock_supabase_client):
        """Cenário: Verifica que filtra por 'pending' e 'overdue'."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.count = 3
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            repository.count_pending_obligations("org-123")

        # Verificar que in_ foi chamado com os dois status corretos
        calls = mock_table.in_.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == "status"
        assert set(calls[0][0][1]) == {"pending", "overdue"}

    def test_count_pending_obligations_fallback_to_len(self, mock_supabase_client):
        """Cenário: Fallback para len(data) quando count não está disponível."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.count = None
        mock_result.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}]
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            result = repository.count_pending_obligations("org-123")

        assert result == 4

    def test_count_pending_obligations_filters_by_org(self, mock_supabase_client):
        """Cenário: Verifica que filtra por org_id."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.count = 5
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            repository.count_pending_obligations("org-999")

        # Verificar que eq foi chamado com org_id
        mock_table.eq.assert_called_once_with("org_id", "org-999")


# ============================================================================
# TEST GROUP: Tratamento de erros
# ============================================================================


class TestErrorHandling:
    """Testes para tratamento de erros da API."""

    def test_list_obligations_handles_api_error(self, mock_supabase_client):
        """Cenário: Trata erro da API corretamente."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        # Simular erro da API com formato correto (dict)
        mock_table.execute.side_effect = repository.PostgrestAPIError(
            {
                "message": "Connection failed",
                "code": "500",
                "details": "Internal server error",
                "hint": "Check server status",
            }
        )

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                repository.list_obligations_for_org("org-123")

        assert "SELECT" in str(exc_info.value)

    def test_count_pending_handles_api_error(self, mock_supabase_client):
        """Cenário: count_pending_obligations trata erro da API."""
        from src.features.regulations import repository

        mock_client, mock_table = mock_supabase_client

        # Simular erro da API com formato correto
        mock_table.execute.side_effect = repository.PostgrestAPIError({"message": "Query failed"})

        with patch("src.features.regulations.repository.get_supabase_client", return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                repository.count_pending_obligations("org-123")

        assert "COUNT" in str(exc_info.value)
