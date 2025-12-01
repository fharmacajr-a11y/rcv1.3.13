"""
TEST-001 Fase 28 – Cobertura de src/features/cashflow/repository.py

Objetivo:
    Aumentar cobertura de cashflow/repository.py de ~63% para ≥85-95%, testando:
    - Filtros avançados (tipo, período, texto, combinações)
    - CRUD direto (create, update, delete)
    - Agregados/totais (entradas, saídas, saldo)
    - Casos extremos e tratamento de erros

Escopo:
    - Não altera lógica de produção
    - Foca em branches não cobertos na Fase 1
    - Usa mocks para isolar Supabase
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Import direto do repository (não via service)
from src.features.cashflow import repository


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
    mock_table.ilike.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table

    return mock_client, mock_table


# ============================================================================
# TEST GROUP: list_entries() - Filtros Avançados
# ============================================================================


class TestListEntries:
    """Testes para list_entries() - filtros e combinações."""

    def test_list_entries_basic_date_range(self, mock_supabase_client):
        """Cenário: Listagem básica com período de datas."""
        mock_client, mock_table = mock_supabase_client

        # Dados mockados
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1", "date": "2025-01-01", "type": "IN", "amount": 100.0},
            {"id": "2", "date": "2025-01-15", "type": "OUT", "amount": 50.0},
        ]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(dfrom="2025-01-01", dto="2025-01-31")

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

        # Verificar que gte e lte foram chamados
        mock_table.gte.assert_called_once()
        mock_table.lte.assert_called_once()

    def test_list_entries_filter_type_in(self, mock_supabase_client):
        """Cenário: Filtro por tipo IN (apenas entradas)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "1", "type": "IN", "amount": 100.0}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(dfrom="2025-01-01", dto="2025-01-31", type_filter="IN")

        assert len(result) == 1
        assert result[0]["type"] == "IN"

        # Verificar que eq foi chamado com type
        calls = [str(call) for call in mock_table.eq.call_args_list]
        assert any("type" in call and "IN" in call for call in calls)

    def test_list_entries_filter_type_out(self, mock_supabase_client):
        """Cenário: Filtro por tipo OUT (apenas saídas)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "2", "type": "OUT", "amount": 50.0}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(dfrom="2025-01-01", dto="2025-01-31", type_filter="OUT")

        assert len(result) == 1
        assert result[0]["type"] == "OUT"

    def test_list_entries_filter_text_description(self, mock_supabase_client):
        """Cenário: Filtro por texto na descrição."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "1", "description": "Venda produto X"}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(dfrom="2025-01-01", dto="2025-01-31", text="produto")

        assert len(result) == 1

        # Verificar que ilike foi chamado
        mock_table.ilike.assert_called_once()
        args = mock_table.ilike.call_args
        assert "description" in args[0]
        assert "%produto%" in args[0]

    def test_list_entries_filter_text_ilike_exception(self, mock_supabase_client):
        """Cenário: Exceção no ilike deve ser ignorada (fallback)."""
        mock_client, mock_table = mock_supabase_client

        # ilike lança exceção
        mock_table.ilike.side_effect = Exception("ilike not supported")

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            # Não deve levantar exceção
            result = repository.list_entries(dfrom="2025-01-01", dto="2025-01-31", text="teste")

        assert result == []

    def test_list_entries_with_org_id(self, mock_supabase_client):
        """Cenário: Filtro por org_id."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "1", "org_id": "org-123"}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(dfrom="2025-01-01", dto="2025-01-31", org_id="org-123")

        assert len(result) == 1

        # Verificar que eq foi chamado com org_id
        calls = [str(call) for call in mock_table.eq.call_args_list]
        assert any("org_id" in call and "org-123" in call for call in calls)

    def test_list_entries_combined_filters(self, mock_supabase_client):
        """Cenário: Combinação de filtros (tipo + texto + org_id)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "1", "type": "IN", "description": "Venda", "org_id": "org-456"}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(
                dfrom="2025-01-01", dto="2025-01-31", type_filter="IN", text="Venda", org_id="org-456"
            )

        assert len(result) == 1

    def test_list_entries_empty_result(self, mock_supabase_client):
        """Cenário: Nenhum lançamento encontrado."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(dfrom="2025-01-01", dto="2025-01-31")

        assert result == []

    def test_list_entries_no_data_attribute(self, mock_supabase_client):
        """Cenário: Resposta sem atributo data (fallback para lista vazia)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        del mock_result.data  # Remove atributo data
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(dfrom="2025-01-01", dto="2025-01-31")

        assert result == []

    def test_list_entries_date_objects(self, mock_supabase_client):
        """Cenário: Usar objetos date em vez de strings."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(dfrom=date(2025, 1, 1), dto=date(2025, 1, 31))

        assert result == []

        # Verificar conversão para ISO
        gte_call = mock_table.gte.call_args
        lte_call = mock_table.lte.call_args
        assert "2025-01-01" in str(gte_call)
        assert "2025-01-31" in str(lte_call)


# ============================================================================
# TEST GROUP: totals() - Agregados
# ============================================================================


class TestTotals:
    """Testes para totals() - cálculo de totais e saldo."""

    def test_totals_mixed_entries(self, mock_supabase_client):
        """Cenário: Entradas e saídas mistas."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"type": "IN", "amount": 100.0},
            {"type": "IN", "amount": 50.0},
            {"type": "OUT", "amount": 30.0},
            {"type": "OUT", "amount": 20.0},
        ]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.totals(dfrom="2025-01-01", dto="2025-01-31")

        assert result["in"] == 150.0
        assert result["out"] == 50.0
        assert result["balance"] == 100.0

    def test_totals_only_in(self, mock_supabase_client):
        """Cenário: Apenas entradas."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"type": "IN", "amount": 100.0},
            {"type": "IN", "amount": 200.0},
        ]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.totals(dfrom="2025-01-01", dto="2025-01-31")

        assert result["in"] == 300.0
        assert result["out"] == 0.0
        assert result["balance"] == 300.0

    def test_totals_only_out(self, mock_supabase_client):
        """Cenário: Apenas saídas."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"type": "OUT", "amount": 50.0},
            {"type": "OUT", "amount": 25.0},
        ]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.totals(dfrom="2025-01-01", dto="2025-01-31")

        assert result["in"] == 0.0
        assert result["out"] == 75.0
        assert result["balance"] == -75.0

    def test_totals_empty_list(self, mock_supabase_client):
        """Cenário: Lista vazia (sem lançamentos)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.totals(dfrom="2025-01-01", dto="2025-01-31")

        assert result["in"] == 0.0
        assert result["out"] == 0.0
        assert result["balance"] == 0.0

    def test_totals_amount_none(self, mock_supabase_client):
        """Cenário: Valores None ou ausentes devem ser tratados como 0."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"type": "IN", "amount": None},
            {"type": "OUT"},  # Sem campo amount
            {"type": "IN", "amount": 100.0},
        ]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.totals(dfrom="2025-01-01", dto="2025-01-31")

        assert result["in"] == 100.0
        assert result["out"] == 0.0
        assert result["balance"] == 100.0

    def test_totals_lowercase_type(self, mock_supabase_client):
        """Cenário: Tipo em minúsculas (deve ser normalizado para upper)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"type": "in", "amount": 50.0},
            {"type": "out", "amount": 25.0},
        ]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.totals(dfrom="2025-01-01", dto="2025-01-31")

        assert result["in"] == 50.0
        assert result["out"] == 25.0

    def test_totals_with_org_id(self, mock_supabase_client):
        """Cenário: Totais filtrados por org_id."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"type": "IN", "amount": 100.0, "org_id": "org-123"},
        ]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.totals(dfrom="2025-01-01", dto="2025-01-31", org_id="org-123")

        assert result["in"] == 100.0


# ============================================================================
# TEST GROUP: create_entry() - Inserção
# ============================================================================


class TestCreateEntry:
    """Testes para create_entry() - criação de lançamentos."""

    def test_create_entry_success(self, mock_supabase_client):
        """Cenário: Criar lançamento com sucesso."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "new-123", "type": "IN", "amount": 100.0}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.create_entry({"type": "IN", "amount": 100.0, "description": "Venda"})

        assert result["id"] == "new-123"
        assert result["type"] == "IN"

    def test_create_entry_with_org_id(self, mock_supabase_client):
        """Cenário: Criar lançamento com org_id."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "new-456", "org_id": "org-789"}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.create_entry({"type": "OUT", "amount": 50.0}, org_id="org-789")

        assert result["org_id"] == "org-789"

        # Verificar que payload foi enviado com org_id
        insert_call = mock_table.insert.call_args
        assert "org_id" in insert_call[0][0]

    def test_create_entry_org_id_already_in_data(self, mock_supabase_client):
        """Cenário: org_id já presente no data (não deve sobrescrever)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "new-789", "org_id": "org-original"}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            repository.create_entry(
                {"type": "IN", "amount": 75.0, "org_id": "org-original"},
                org_id="org-override",  # Não deve sobrescrever
            )

        # Verificar que org_id original foi mantido
        insert_call = mock_table.insert.call_args
        assert insert_call[0][0]["org_id"] == "org-original"

    def test_create_entry_no_data_in_response(self, mock_supabase_client):
        """Cenário: Resposta sem data (fallback para payload original)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        payload = {"type": "IN", "amount": 100.0}

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.create_entry(payload)

        assert result == payload


# ============================================================================
# TEST GROUP: update_entry() - Atualização
# ============================================================================


class TestUpdateEntry:
    """Testes para update_entry() - atualização de lançamentos."""

    def test_update_entry_success(self, mock_supabase_client):
        """Cenário: Atualizar lançamento com sucesso."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "entry-123", "amount": 150.0}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.update_entry("entry-123", {"amount": 150.0})

        assert result["id"] == "entry-123"
        assert result["amount"] == 150.0

    def test_update_entry_multiple_fields(self, mock_supabase_client):
        """Cenário: Atualizar múltiplos campos."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "entry-456", "amount": 200.0, "description": "Updated"}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.update_entry("entry-456", {"amount": 200.0, "description": "Updated"})

        assert result["amount"] == 200.0
        assert result["description"] == "Updated"

    def test_update_entry_no_data_in_response(self, mock_supabase_client):
        """Cenário: Resposta sem data (fallback para id + data)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.update_entry("entry-789", {"amount": 250.0})

        assert result["id"] == "entry-789"
        assert result["amount"] == 250.0


# ============================================================================
# TEST GROUP: delete_entry() - Exclusão
# ============================================================================


class TestDeleteEntry:
    """Testes para delete_entry() - exclusão de lançamentos."""

    def test_delete_entry_success(self, mock_supabase_client):
        """Cenário: Excluir lançamento com sucesso."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            # Não deve levantar exceção
            repository.delete_entry("entry-to-delete")

        # Verificar que delete e eq foram chamados
        mock_table.delete.assert_called_once()
        mock_table.eq.assert_called_once_with("id", "entry-to-delete")


# ============================================================================
# TEST GROUP: Funções Auxiliares
# ============================================================================


class TestHelperFunctions:
    """Testes para funções auxiliares (_get_client, _fmt_api_error, _iso)."""

    def test_get_client_none_raises(self):
        """Cenário: _get_client quando _GET retorna None."""
        with patch.object(repository, "_GET", return_value=None):
            with pytest.raises(RuntimeError, match="Cliente Supabase não disponível"):
                repository._get_client()

    def test_fmt_api_error_with_code(self):
        """Cenário: _fmt_api_error com código."""
        # Criar mock de erro em vez de instanciar classe real
        error = MagicMock()
        error.code = "42P01"
        error.details = "Table not found"
        error.hint = "Create the table first"
        error.__str__ = lambda self: "Table not found"

        result = repository._fmt_api_error(error, "SELECT")

        assert "SELECT" in str(result)
        assert "42P01" in str(result)
        assert "Table not found" in str(result)
        assert "Create the table first" in str(result)

    def test_fmt_api_error_without_code(self):
        """Cenário: _fmt_api_error sem código."""
        error = MagicMock()
        error.code = None
        error.details = "Generic error"
        error.hint = None

        result = repository._fmt_api_error(error, "INSERT")

        assert "INSERT" in str(result)
        assert "Generic error" in str(result)

    def test_fmt_api_error_fallback_to_str(self):
        """Cenário: _fmt_api_error sem details (usa str(e))."""
        error = MagicMock()
        error.code = None
        error.details = None
        error.message = None
        error.__str__ = lambda self: "Fallback message"

        result = repository._fmt_api_error(error, "UPDATE")

        assert "UPDATE" in str(result)
        assert "Fallback message" in str(result)

    def test_iso_with_date_object(self):
        """Cenário: _iso com objeto date."""
        d = date(2025, 11, 21)
        result = repository._iso(d)
        assert result == "2025-11-21"

    def test_iso_with_string(self):
        """Cenário: _iso com string (retorna a própria string)."""
        s = "2025-11-21"
        result = repository._iso(s)
        assert result == "2025-11-21"


# ============================================================================
# TEST GROUP: Cobertura Adicional
# ============================================================================


class TestAdditionalCoverage:
    """Testes adicionais para aumentar cobertura."""

    def test_list_entries_no_dfrom_filter(self, mock_supabase_client):
        """Cenário: Listagem sem filtro de data inicial (None/vazio)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(
                dfrom="",  # Empty string
                dto="2025-01-31",
            )

        assert result == []

    def test_list_entries_no_dto_filter(self, mock_supabase_client):
        """Cenário: Listagem sem filtro de data final (None/vazio)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(
                dfrom="2025-01-01",
                dto="",  # Empty string
            )

        assert result == []

    def test_list_entries_invalid_type_filter(self, mock_supabase_client):
        """Cenário: Tipo inválido (não IN nem OUT) deve ser ignorado."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(
                dfrom="2025-01-01",
                dto="2025-01-31",
                type_filter="INVALID",  # Não é IN nem OUT
            )

        assert result == []

        # Verificar que eq NÃO foi chamado com type (porque filtro é inválido)
        type_eq_calls = [call for call in mock_table.eq.call_args_list if len(call[0]) > 0 and call[0][0] == "type"]
        assert len(type_eq_calls) == 0

    def test_list_entries_without_org_id(self, mock_supabase_client):
        """Cenário: Listagem sem org_id (None)."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.list_entries(
                dfrom="2025-01-01",
                dto="2025-01-31",
                org_id=None,  # Explicitamente None
            )

        assert result == []

    def test_totals_type_without_upper(self, mock_supabase_client):
        """Cenário: Tipo None ou vazio deve ser tratado."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [
            {"type": None, "amount": 50.0},  # Tipo None
            {"amount": 100.0},  # Sem campo type
        ]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.totals(dfrom="2025-01-01", dto="2025-01-31")

        # Como type é None ou ausente, tudo vai para OUT
        assert result["in"] == 0.0
        assert result["out"] == 150.0

    def test_create_entry_without_org_id(self, mock_supabase_client):
        """Cenário: Criar lançamento sem passar org_id."""
        mock_client, mock_table = mock_supabase_client

        mock_result = MagicMock()
        mock_result.data = [{"id": "new-without-org"}]
        mock_table.execute.return_value = mock_result

        with patch.object(repository, "_get_client", return_value=mock_client):
            result = repository.create_entry(
                {"type": "IN", "amount": 100.0}
                # org_id não passado
            )

        assert result["id"] == "new-without-org"
