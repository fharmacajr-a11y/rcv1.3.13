# -*- coding: utf-8 -*-
"""Testes adicionais para src/features/cashflow/repository.py - Coverage Pack 02.

Foco em branches não cobertas:
- Erros de API (PostgrestAPIError)
- Fallbacks de importação de cliente
- Tratamento de None/valores inválidos
- Exceções em filtros e queries
- Edge cases em cálculos
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.features.cashflow import repository


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_client():
    """Mock do cliente Supabase."""
    return MagicMock()


@pytest.fixture
def mock_postgrest_error():
    """Mock de PostgrestAPIError compatível."""
    # Importa a classe real do repository para compatibilidade
    from src.features.cashflow.repository import PostgrestAPIError

    # PostgrestAPIError espera um dict
    error = PostgrestAPIError(
        {
            "message": "Row not found",
            "details": "Row not found",
            "hint": "Check your query",
            "code": "PGRST116",
        }
    )
    return error


# ============================================================================
# TESTES - Helpers centralizados movidos para data.supabase_repo
# Os testes de get_supabase_client, format_api_error e to_iso_date
# estão em tests/data/test_supabase_repo.py
# ============================================================================


# ============================================================================
# TESTES - _apply_text_filter() com exceções
# ============================================================================


def test_apply_text_filter_handles_exception(monkeypatch):
    """Testa que _apply_text_filter retorna query original quando ilike falha."""
    mock_query = MagicMock()
    mock_query.ilike.side_effect = Exception("ilike not supported")

    result = repository._apply_text_filter(mock_query, "test")

    # Deve retornar query original sem modificação
    assert result is mock_query
    assert mock_query.ilike.called


def test_apply_text_filter_returns_unchanged_when_no_text():
    """Testa que _apply_text_filter não modifica query quando text é None."""
    mock_query = MagicMock()

    result = repository._apply_text_filter(mock_query, None)

    assert result is mock_query
    assert not mock_query.ilike.called


def test_apply_text_filter_returns_unchanged_when_empty_text():
    """Testa que _apply_text_filter não modifica query quando text é string vazia."""
    mock_query = MagicMock()

    result = repository._apply_text_filter(mock_query, "")

    assert result is mock_query
    assert not mock_query.ilike.called


# ============================================================================
# TESTES - list_entries() com erros de API
# ============================================================================


def test_list_entries_raises_on_postgrest_error(mock_client, mock_postgrest_error):
    """Testa que list_entries lança RuntimeError quando API retorna erro."""
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.side_effect = mock_postgrest_error
    mock_client.table.return_value = mock_table

    with (
        patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client),
        pytest.raises(RuntimeError, match="SELECT.*PGRST116"),
    ):
        repository.list_entries(
            dfrom=date(2024, 1, 1),
            dto=date(2024, 1, 31),
        )


def test_list_entries_with_org_id_filter(mock_client):
    """Testa list_entries com filtro de org_id."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "1", "org_id": "org-123"}]

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
            org_id="org-123",
        )

    assert len(result) == 1
    mock_table.eq.assert_called_with("org_id", "org-123")


def test_list_entries_handles_response_without_data(mock_client):
    """Testa que list_entries retorna lista vazia quando response.data é None."""
    mock_response = MagicMock()
    mock_response.data = None

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        result = repository.list_entries(dfrom="2024-01-01", dto="2024-01-31")

    assert result == []


# ============================================================================
# TESTES - totals() com valores None e edge cases
# ============================================================================


def test_totals_handles_mixed_none_values(mock_client):
    """Testa totals com mix de valores None e numéricos."""
    entries = [
        {"type": "IN", "amount": None},
        {"type": "IN", "amount": 1000.0},
        {"type": "OUT", "amount": None},
        {"type": "OUT", "amount": 300.0},
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

    assert result["in"] == 1000.0
    assert result["out"] == 300.0
    assert result["balance"] == 700.0


def test_totals_handles_missing_type_field(mock_client):
    """Testa totals quando field 'type' está ausente (tratado como OUT)."""
    entries = [
        {"amount": 500.0},  # Sem type
        {"type": "IN", "amount": 1000.0},
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

    # Entry sem type deve ser contabilizado como OUT
    assert result["in"] == 1000.0
    assert result["out"] == 500.0
    assert result["balance"] == 500.0


def test_totals_handles_zero_amounts(mock_client):
    """Testa totals com valores zero."""
    entries = [
        {"type": "IN", "amount": 0.0},
        {"type": "OUT", "amount": 0.0},
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
    assert result["out"] == 0.0
    assert result["balance"] == 0.0


# ============================================================================
# TESTES - create_entry() com erros
# ============================================================================


def test_create_entry_raises_on_postgrest_error(mock_client, mock_postgrest_error):
    """Testa que create_entry lança RuntimeError quando API retorna erro."""
    mock_table = MagicMock()
    mock_table.insert.return_value = mock_table
    mock_table.execute.side_effect = mock_postgrest_error
    mock_client.table.return_value = mock_table

    with (
        patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client),
        pytest.raises(RuntimeError, match="INSERT.*PGRST116"),
    ):
        repository.create_entry({"date": "2024-01-01", "type": "IN", "amount": 100.0})


def test_create_entry_returns_payload_when_response_empty(mock_client):
    """Testa que create_entry retorna payload quando response.data é vazio."""
    mock_response = MagicMock()
    mock_response.data = []

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        payload = {"date": "2024-01-01", "type": "IN", "amount": 100.0}
        result = repository.create_entry(payload)

    # Deve retornar o payload original quando response vazio
    assert result == payload


def test_create_entry_preserves_existing_org_id(mock_client):
    """Testa que create_entry não sobrescreve org_id existente no payload."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "new-1", "org_id": "org-original"}]

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        payload = {"date": "2024-01-01", "type": "IN", "amount": 100.0, "org_id": "org-original"}
        result = repository.create_entry(payload, org_id="org-different")

    # Deve preservar org_id original do payload
    assert result["org_id"] == "org-original"


# ============================================================================
# TESTES - update_entry() com erros
# ============================================================================


def test_update_entry_raises_on_postgrest_error(mock_client, mock_postgrest_error):
    """Testa que update_entry lança RuntimeError quando API retorna erro."""
    mock_table = MagicMock()
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = mock_postgrest_error
    mock_client.table.return_value = mock_table

    with (
        patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client),
        pytest.raises(RuntimeError, match="UPDATE.*PGRST116"),
    ):
        repository.update_entry("entry-123", {"amount": 500.0})


def test_update_entry_returns_fallback_when_response_empty(mock_client):
    """Testa que update_entry retorna fallback quando response.data é vazio."""
    mock_response = MagicMock()
    mock_response.data = []

    mock_table = MagicMock()
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = mock_response
    mock_client.table.return_value = mock_table

    with patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client):
        data = {"amount": 2000.0, "description": "Updated"}
        result = repository.update_entry("entry-456", data)

    # Deve retornar fallback com id + data
    assert result["id"] == "entry-456"
    assert result["amount"] == 2000.0
    assert result["description"] == "Updated"


# ============================================================================
# TESTES - delete_entry() com erros
# ============================================================================


def test_delete_entry_raises_on_postgrest_error(mock_client, mock_postgrest_error):
    """Testa que delete_entry lança RuntimeError quando API retorna erro."""
    mock_table = MagicMock()
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = mock_postgrest_error
    mock_client.table.return_value = mock_table

    with (
        patch("src.features.cashflow.repository.get_supabase_client", return_value=mock_client),
        pytest.raises(RuntimeError, match="DELETE.*PGRST116"),
    ):
        repository.delete_entry("entry-789")


# ============================================================================
# TESTES - _build_list_query() com diversos filtros
# ============================================================================


def test_build_list_query_applies_all_filters(mock_client):
    """Testa que _build_list_query aplica todos os filtros corretamente."""
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.ilike.return_value = mock_table
    mock_client.table.return_value = mock_table

    repository._build_list_query(
        mock_client,
        dfrom="2024-01-01",
        dto="2024-01-31",
        type_filter="IN",
        text="venda",
        org_id="org-123",
    )

    # Verifica chamadas
    mock_table.eq.assert_any_call("org_id", "org-123")
    mock_table.eq.assert_any_call("type", "IN")
    mock_table.gte.assert_called_once_with("date", "2024-01-01")
    mock_table.lte.assert_called_once_with("date", "2024-01-31")
    mock_table.ilike.assert_called_once_with("description", "%venda%")


def test_build_list_query_skips_invalid_type_filter(mock_client):
    """Testa que _build_list_query ignora type_filter inválido."""
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_client.table.return_value = mock_table

    repository._build_list_query(
        mock_client,
        dfrom="2024-01-01",
        dto="2024-01-31",
        type_filter="INVALID",  # Não deve aplicar filtro
        text=None,
        org_id=None,
    )

    # eq() não deve ter sido chamado para type
    eq_calls = [call for call in mock_table.eq.call_args_list if call[0][0] == "type"]
    assert len(eq_calls) == 0


# ============================================================================
# TESTES - _accumulate_totals() com edge cases
# ============================================================================


def test_accumulate_totals_handles_string_amounts():
    """Testa que _accumulate_totals converte strings para float."""
    rows = [
        {"type": "IN", "amount": "1000.50"},
        {"type": "OUT", "amount": "200.25"},
    ]

    result = repository._accumulate_totals(rows)

    assert result["in"] == 1000.50
    assert result["out"] == 200.25
    assert result["balance"] == 800.25


def test_accumulate_totals_handles_lowercase_type():
    """Testa que _accumulate_totals aceita type em lowercase."""
    rows = [
        {"type": "in", "amount": 500.0},
        {"type": "out", "amount": 100.0},
    ]

    result = repository._accumulate_totals(rows)

    assert result["in"] == 500.0
    assert result["out"] == 100.0
    assert result["balance"] == 400.0


def test_accumulate_totals_handles_empty_list():
    """Testa _accumulate_totals com lista vazia."""
    result = repository._accumulate_totals([])

    assert result["in"] == 0.0
    assert result["out"] == 0.0
    assert result["balance"] == 0.0
