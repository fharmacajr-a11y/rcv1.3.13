"""Testes para o módulo de Fluxo de Caixa (cashflow).

Cobertura de:
- Listagem de lançamentos
- Cálculo de totais (entradas/saídas/saldo)
- Criação, atualização e exclusão de lançamentos
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.features.cashflow import repository


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_client():
    """Mock do cliente Supabase para testes."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_entries():
    """Lançamentos de exemplo para testes."""
    return [
        {
            "id": "1",
            "date": "2024-01-01",
            "type": "IN",
            "amount": 1000.0,
            "description": "Venda produto A",
            "org_id": "org-123",
        },
        {
            "id": "2",
            "date": "2024-01-02",
            "type": "OUT",
            "amount": 500.0,
            "description": "Compra material",
            "org_id": "org-123",
        },
        {
            "id": "3",
            "date": "2024-01-03",
            "type": "IN",
            "amount": 750.0,
            "description": "Venda produto B",
            "org_id": "org-123",
        },
    ]


# ============================================================================
# TESTES - list_entries()
# ============================================================================


def test_list_entries_basic(mock_client, sample_entries):
    """Testa listagem básica de lançamentos."""
    mock_response = MagicMock()
    mock_response.data = sample_entries

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.list_entries(
            dfrom=date(2024, 1, 1),
            dto=date(2024, 1, 31),
        )

    assert len(result) == 3
    assert result[0]["id"] == "1"
    assert result[1]["amount"] == 500.0


def test_list_entries_with_type_filter(mock_client, sample_entries):
    """Testa listagem com filtro por tipo (IN/OUT)."""
    # Simula filtro no backend retornando apenas entradas
    filtered = [e for e in sample_entries if e["type"] == "IN"]
    mock_response = MagicMock()
    mock_response.data = filtered

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.list_entries(
            dfrom="2024-01-01",
            dto="2024-01-31",
            type_filter="IN",
        )

    assert len(result) == 2
    assert all(e["type"] == "IN" for e in result)


def test_list_entries_with_text_search(mock_client):
    """Testa listagem com busca por texto."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "1", "description": "Venda produto A", "type": "IN", "amount": 100.0}]

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.ilike.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.list_entries(
            dfrom="2024-01-01",
            dto="2024-01-31",
            text="produto",
        )

    assert len(result) == 1
    assert "produto" in result[0]["description"].lower()


def test_list_entries_empty_result(mock_client):
    """Testa listagem quando não há lançamentos no período."""
    mock_response = MagicMock()
    mock_response.data = []

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.list_entries(
            dfrom="2024-12-01",
            dto="2024-12-31",
        )

    assert result == []


# ============================================================================
# TESTES - totals()
# ============================================================================


def test_totals_basic(mock_client, sample_entries):
    """Testa cálculo de totais (entradas/saídas/saldo)."""
    mock_response = MagicMock()
    mock_response.data = sample_entries

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.totals(
            dfrom=date(2024, 1, 1),
            dto=date(2024, 1, 31),
        )

    # Entradas: 1000 + 750 = 1750
    # Saídas: 500
    # Saldo: 1750 - 500 = 1250
    assert result["in"] == 1750.0
    assert result["out"] == 500.0
    assert result["balance"] == 1250.0


def test_totals_only_income(mock_client):
    """Testa totais quando há apenas entradas."""
    entries = [
        {"type": "IN", "amount": 1000.0},
        {"type": "IN", "amount": 500.0},
    ]
    mock_response = MagicMock()
    mock_response.data = entries

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.totals(dfrom="2024-01-01", dto="2024-01-31")

    assert result["in"] == 1500.0
    assert result["out"] == 0.0
    assert result["balance"] == 1500.0


def test_totals_only_expenses(mock_client):
    """Testa totais quando há apenas saídas."""
    entries = [
        {"type": "OUT", "amount": 300.0},
        {"type": "OUT", "amount": 200.0},
    ]
    mock_response = MagicMock()
    mock_response.data = entries

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.totals(dfrom="2024-01-01", dto="2024-01-31")

    assert result["in"] == 0.0
    assert result["out"] == 500.0
    assert result["balance"] == -500.0


def test_totals_empty_period(mock_client):
    """Testa totais em período sem lançamentos."""
    mock_response = MagicMock()
    mock_response.data = []

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.totals(dfrom="2024-12-01", dto="2024-12-31")

    assert result["in"] == 0.0
    assert result["out"] == 0.0
    assert result["balance"] == 0.0


# ============================================================================
# TESTES - create_entry()
# ============================================================================


def test_create_entry_basic(mock_client):
    """Testa criação de lançamento."""
    new_entry = {
        "date": "2024-01-15",
        "type": "IN",
        "amount": 1500.0,
        "description": "Nova venda",
    }
    created = {**new_entry, "id": "new-123"}

    mock_response = MagicMock()
    mock_response.data = [created]

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.create_entry(new_entry)

    assert result["id"] == "new-123"
    assert result["amount"] == 1500.0


def test_create_entry_with_org_id(mock_client):
    """Testa criação com org_id."""
    new_entry = {
        "date": "2024-01-15",
        "type": "IN",
        "amount": 1000.0,
        "description": "Venda",
    }
    created = {**new_entry, "id": "new-456", "org_id": "org-999"}

    mock_response = MagicMock()
    mock_response.data = [created]

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.create_entry(new_entry, org_id="org-999")

    assert result["org_id"] == "org-999"


# ============================================================================
# TESTES - update_entry()
# ============================================================================


def test_update_entry_basic(mock_client):
    """Testa atualização de lançamento."""
    updated_data = {"amount": 2000.0, "description": "Venda atualizada"}
    updated_entry = {"id": "entry-123", **updated_data}

    mock_response = MagicMock()
    mock_response.data = [updated_entry]

    mock_table = MagicMock()
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.update_entry("entry-123", updated_data)

    assert result["id"] == "entry-123"
    assert result["amount"] == 2000.0
    assert result["description"] == "Venda atualizada"


# ============================================================================
# TESTES - delete_entry()
# ============================================================================


def test_delete_entry_basic(mock_client):
    """Testa exclusão de lançamento."""
    mock_table = MagicMock()
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        # Não deve lançar exceção
        repository.delete_entry("entry-456")

    # Verifica que o método foi chamado
    mock_table.delete.assert_called_once()
    mock_table.eq.assert_called_once_with("id", "entry-456")


# ============================================================================
# TESTES - EDGE CASES
# ============================================================================


def test_totals_handles_none_amounts(mock_client):
    """Testa totais quando amount é None."""
    entries = [
        {"type": "IN", "amount": None},
        {"type": "OUT", "amount": 100.0},
        {"type": "IN", "amount": 200.0},
    ]
    mock_response = MagicMock()
    mock_response.data = entries

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.totals(dfrom="2024-01-01", dto="2024-01-31")

    # None deve ser tratado como 0
    assert result["in"] == 200.0
    assert result["out"] == 100.0
    assert result["balance"] == 100.0


def test_iso_date_conversion():
    """Testa conversão de date para ISO string."""
    from src.db.supabase_repo import to_iso_date

    # Date object
    d = date(2024, 1, 15)
    assert to_iso_date(d) == "2024-01-15"

    # String já formatada
    assert to_iso_date("2024-01-15") == "2024-01-15"
