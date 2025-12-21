# -*- coding: utf-8 -*-
"""
Testes para lixeira_helpers.py - Fase 02

Cobertura:
1. should_open_new_trash_window (2 testes)
2. should_refresh_trash_window (4 testes)
3. calculate_progress_percentage (5 testes)
4. normalize_trash_row_data (6 testes)
5. format_author_initial (5 testes)
6. format_timestamp_with_author (3 testes)
7. parse_error_list_for_display (6 testes)

Total: 31 testes
"""

from __future__ import annotations

from src.modules.lixeira.views.lixeira_helpers import (
    calculate_progress_percentage,
    format_author_initial,
    format_timestamp_with_author,
    normalize_trash_row_data,
    parse_error_list_for_display,
    should_open_new_trash_window,
    should_refresh_trash_window,
)


# ==============================================================================
# 1. should_open_new_trash_window (2 testes)
# ==============================================================================


def test_should_open_new_trash_window_no_window_exists() -> None:
    """Testa que deve criar nova janela quando não existe."""
    assert should_open_new_trash_window(window_exists=False) is True


def test_should_open_new_trash_window_window_exists() -> None:
    """Testa que não deve criar nova janela quando já existe."""
    assert should_open_new_trash_window(window_exists=True) is False


# ==============================================================================
# 2. should_refresh_trash_window (4 testes)
# ==============================================================================


def test_should_refresh_trash_window_no_window() -> None:
    """Testa que não deve fazer refresh se janela não existe."""
    assert should_refresh_trash_window(window_exists=False) is False


def test_should_refresh_trash_window_window_exists() -> None:
    """Testa que deve fazer refresh se janela existe."""
    assert should_refresh_trash_window(window_exists=True) is True


def test_should_refresh_trash_window_with_pending_changes() -> None:
    """Testa refresh com mudanças pendentes (mas janela existe)."""
    assert should_refresh_trash_window(window_exists=True, _has_pending_changes=True) is True


def test_should_refresh_trash_window_no_window_but_pending() -> None:
    """Testa que não faz refresh se janela não existe (mesmo com pending)."""
    assert should_refresh_trash_window(window_exists=False, _has_pending_changes=True) is False


# ==============================================================================
# 3. calculate_progress_percentage (5 testes)
# ==============================================================================


def test_calculate_progress_percentage_start() -> None:
    """Testa cálculo no início (0%)."""
    assert calculate_progress_percentage(0, 10) == 0.0


def test_calculate_progress_percentage_middle() -> None:
    """Testa cálculo no meio (50%)."""
    assert calculate_progress_percentage(5, 10) == 50.0


def test_calculate_progress_percentage_end() -> None:
    """Testa cálculo no fim (100%)."""
    assert calculate_progress_percentage(10, 10) == 100.0


def test_calculate_progress_percentage_zero_total() -> None:
    """Testa cálculo com total zero (edge case)."""
    assert calculate_progress_percentage(3, 0) == 0.0


def test_calculate_progress_percentage_current_exceeds_total() -> None:
    """Testa cálculo quando current > total (cap em 100%)."""
    assert calculate_progress_percentage(15, 10) == 100.0


# ==============================================================================
# 4. normalize_trash_row_data (6 testes)
# ==============================================================================


def test_normalize_trash_row_data_dict_complete() -> None:
    """Testa normalização de dict completo."""
    row = {
        "id": 1,
        "razao_social": "Empresa X",
        "cnpj": "12345678000190",
        "nome": "João Silva",
        "whatsapp": "11999998888",
        "obs": "Cliente VIP",
        "ultima_alteracao": "2025-11-28T18:30:00",
        "ultima_por": "user-123",
    }
    result = normalize_trash_row_data(row)
    assert result["id"] == 1
    assert result["razao_social"] == "Empresa X"
    assert result["cnpj"] == "12345678000190"
    assert result["nome"] == "João Silva"
    assert result["whatsapp"] == "11999998888"
    assert result["obs"] == "Cliente VIP"
    assert result["ultima_alteracao"] == "2025-11-28T18:30:00"
    assert result["ultima_por"] == "user-123"


def test_normalize_trash_row_data_dict_partial() -> None:
    """Testa normalização de dict parcial (campos faltando)."""
    row = {"id": 2, "razao_social": "Empresa Y"}
    result = normalize_trash_row_data(row)
    assert result["id"] == 2
    assert result["razao_social"] == "Empresa Y"
    assert result["cnpj"] == ""
    assert result["nome"] == ""


def test_normalize_trash_row_data_object_with_attributes() -> None:
    """Testa normalização de objeto com atributos."""

    class Cliente:
        def __init__(self) -> None:
            self.id = 3
            self.razao_social = "Empresa Z"
            self.cnpj = "99999999000199"

    result = normalize_trash_row_data(Cliente())
    assert result["id"] == 3
    assert result["razao_social"] == "Empresa Z"
    assert result["cnpj"] == "99999999000199"


def test_normalize_trash_row_data_fallback_field_names() -> None:
    """Testa fallback para nomes alternativos de campos."""
    row = {
        "id": 4,
        "numero": "11888887777",  # fallback para whatsapp
        "observacoes": "Teste obs",  # fallback para obs
        "updated_at": "2025-11-27",  # fallback para ultima_alteracao
    }
    result = normalize_trash_row_data(row)
    assert result["whatsapp"] == "11888887777"
    assert result["obs"] == "Teste obs"
    assert result["ultima_alteracao"] == "2025-11-27"


def test_normalize_trash_row_data_custom_field_mappings() -> None:
    """Testa normalização com mapeamento customizado."""
    row = {"custom_id": 5, "company_name": "Custom Corp"}
    mappings = {
        "id": ["custom_id"],
        "razao_social": ["company_name"],
        "cnpj": ["tax_id"],
    }
    result = normalize_trash_row_data(row, field_mappings=mappings)
    assert result["id"] == 5
    assert result["razao_social"] == "Custom Corp"
    assert result["cnpj"] == ""  # não existe no row


def test_normalize_trash_row_data_empty_row() -> None:
    """Testa normalização de row vazio."""
    result = normalize_trash_row_data({})
    assert all(v == "" for v in result.values())


# ==============================================================================
# 5. format_author_initial (5 testes)
# ==============================================================================


def test_format_author_initial_with_mapping() -> None:
    """Testa formatação com mapeamento de iniciais."""
    result = format_author_initial("user-123", {"user-123": "JD"})
    assert result == "J"


def test_format_author_initial_with_display_name_fallback() -> None:
    """Testa fallback para display_name quando não há mapping."""
    result = format_author_initial("user-456", {}, "John Doe")
    assert result == "J"


def test_format_author_initial_with_id_fallback() -> None:
    """Testa fallback para primeiro char do ID."""
    result = format_author_initial("user-789", {})
    assert result == "U"


def test_format_author_initial_empty_author_id() -> None:
    """Testa formatação com author_id vazio."""
    result = format_author_initial("")
    assert result == ""


def test_format_author_initial_mapping_with_empty_alias() -> None:
    """Testa mapping com alias vazio (usa fallback)."""
    result = format_author_initial("user-999", {"user-999": ""}, "Fallback Name")
    assert result == "F"


# ==============================================================================
# 6. format_timestamp_with_author (3 testes)
# ==============================================================================


def test_format_timestamp_with_author_with_initial() -> None:
    """Testa formatação de timestamp com inicial."""
    result = format_timestamp_with_author("28/11/2025 18:30", "J")
    assert result == "28/11/2025 18:30 (J)"


def test_format_timestamp_with_author_no_initial() -> None:
    """Testa formatação sem inicial."""
    result = format_timestamp_with_author("28/11/2025 18:30", "")
    assert result == "28/11/2025 18:30"


def test_format_timestamp_with_author_empty_timestamp() -> None:
    """Testa formatação com timestamp vazio."""
    result = format_timestamp_with_author("", "J")
    assert result == ""


# ==============================================================================
# 7. parse_error_list_for_display (6 testes)
# ==============================================================================


def test_parse_error_list_for_display_tuple_format() -> None:
    """Testa parsing de lista com tuplas (id, msg)."""
    errors = [(1, "Erro A"), (2, "Erro B"), (3, "Erro C")]
    result = parse_error_list_for_display(errors)
    assert result == ["ID 1: Erro A", "ID 2: Erro B", "ID 3: Erro C"]


def test_parse_error_list_for_display_string_list() -> None:
    """Testa parsing de lista com strings simples."""
    errors = ["Erro genérico 1", "Erro genérico 2"]
    result = parse_error_list_for_display(errors)
    assert result == ["Erro genérico 1", "Erro genérico 2"]


def test_parse_error_list_for_display_single_string() -> None:
    """Testa parsing de string única."""
    result = parse_error_list_for_display("Erro único")
    assert result == ["Erro único"]


def test_parse_error_list_for_display_empty_list() -> None:
    """Testa parsing de lista vazia."""
    result = parse_error_list_for_display([])
    assert result == []


def test_parse_error_list_for_display_none() -> None:
    """Testa parsing de None."""
    result = parse_error_list_for_display(None)
    assert result == []


def test_parse_error_list_for_display_mixed_format() -> None:
    """Testa parsing de formato misto."""
    errors = [(1, "Erro com ID"), "Erro sem ID", [2, "Outro erro com ID"]]
    result = parse_error_list_for_display(errors)
    assert result == ["ID 1: Erro com ID", "Erro sem ID", "ID 2: Outro erro com ID"]
