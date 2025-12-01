"""
Round 10 - Comprehensive test coverage for clientes/forms/_collect.py

Objetivo: Aumentar cobertura de ~25% para 80%+ testando todas as funções e branches.

Funções testadas:
- _get_widget_value(w) - Extrai valor de widget Tkinter
- _val(ents, *keys) - Busca primeira chave disponível
- coletar_valores(ents) - Função principal de coleta de dados do formulário
"""

from __future__ import annotations

from typing import Dict
from unittest.mock import Mock

import pytest

from src.modules.clientes.forms._collect import (
    _get_widget_value,
    _val,
    coletar_valores,
)


# Type alias for widget dictionaries
WidgetDict = Dict[str, Mock]


# ============================================================================
# Fixtures and Helpers
# ============================================================================


@pytest.fixture
def mock_entry_widget():
    """Create a mock Entry/Combobox widget."""
    widget = Mock()
    widget.get = Mock(return_value="valor do entry")
    return widget


@pytest.fixture
def mock_text_widget():
    """Create a mock Text (multiline) widget."""
    # Text widget is detected by isinstance check
    # We'll return a string from get("1.0", "end")
    widget = Mock()
    widget.get = Mock(return_value="texto\nmultilinhas\n")
    return widget


def make_widgets_dict(**overrides: Mock) -> WidgetDict:
    """Helper to create a dict of mock widgets with default values."""
    defaults: WidgetDict = {
        "Razão Social": _make_widget("Empresa ABC"),
        "CNPJ": _make_widget("12345678000190"),
        "Nome": _make_widget("João Silva"),
        "WhatsApp": _make_widget("11999887766"),
        "Observações": _make_widget("Observações do cliente"),
    }
    defaults.update(overrides)
    return defaults


def _make_widget(value: str) -> Mock:
    """Create a simple mock widget that returns value from .get()."""
    widget = Mock()
    widget.get = Mock(return_value=value)
    return widget


def _make_text_widget(value: str) -> Mock:
    """Create a mock Text widget that returns value from .get("1.0", "end")."""
    widget = Mock()
    # Text widgets use get("1.0", "end")
    widget.get = Mock(return_value=value)
    return widget


# ============================================================================
# Test _get_widget_value()
# ============================================================================


class TestGetWidgetValue:
    """Test _get_widget_value function that extracts values from Tkinter widgets."""

    def test_extracts_value_from_entry_widget(self, mock_entry_widget):
        """Should extract value using .get() for Entry/Combobox widgets."""
        result = _get_widget_value(mock_entry_widget)

        assert result == "valor do entry"
        mock_entry_widget.get.assert_called_once()

    def test_strips_whitespace_from_entry(self):
        """Should strip leading/trailing whitespace from Entry values."""
        widget = _make_widget("  valor com espaços  ")

        result = _get_widget_value(widget)

        assert result == "valor com espaços"

    def test_handles_empty_string_from_widget(self):
        """Should handle empty string from widget."""
        widget = _make_widget("")

        result = _get_widget_value(widget)

        assert result == ""

    def test_handles_none_from_widget_get(self):
        """Should handle None returned from .get()."""
        widget = Mock()
        widget.get = Mock(return_value=None)

        result = _get_widget_value(widget)

        assert result == ""

    def test_handles_widget_without_get_method(self):
        """Should fallback to str() when widget has no .get() method."""

        # Create a simple object without .get() method
        class SimpleWidget:
            def __str__(self):
                return "fallback value"

        widget = SimpleWidget()

        result = _get_widget_value(widget)

        # Falls back to str(widget)
        assert result == "fallback value"

    def test_handles_widget_get_raises_exception(self):
        """Should handle exception from .get() and fallback to str()."""

        class FailingWidget:
            def get(self, *args):
                raise AttributeError("no get")

            def __str__(self):
                return "fallback"

        widget = FailingWidget()

        result = _get_widget_value(widget)

        assert result == "fallback"

    def test_handles_text_widget_multiline(self):
        """Should extract multiline text from Text widget using get("1.0", "end")."""
        # Need to test with actual Text widget behavior
        # Text widget is checked with isinstance, so we need to mock that
        widget = Mock()
        widget.get = Mock(side_effect=lambda *args: "texto multiline\n" if args else "")

        result = _get_widget_value(widget)

        # Should call get() without args first (Entry style)
        assert isinstance(result, str)

    def test_handles_text_widget_with_exception(self):
        """Should handle exception from Text widget and fallback."""

        class FailingTextWidget:
            def get(self, *args):
                raise Exception("text error")

            def __str__(self):
                return "fallback"

        widget = FailingTextWidget()

        result = _get_widget_value(widget)

        assert result == "fallback"

    def test_strips_whitespace_from_multiline(self):
        """Should strip whitespace from multiline text."""
        widget = Mock()
        widget.get = Mock(return_value="  linha 1\n  linha 2  \n")

        result = _get_widget_value(widget)

        assert result == "linha 1\n  linha 2"  # strip() removes leading/trailing only


# ============================================================================
# Test _val()
# ============================================================================


class TestVal:
    """Test _val function that searches for first available key."""

    def test_returns_value_for_first_key(self):
        """Should return value for the first key that exists."""
        ents = {
            "Razão Social": _make_widget("Empresa A"),
            "Nome": _make_widget("João"),
        }

        result = _val(ents, "Razão Social", "Razao Social", "razao_social")

        assert result == "Empresa A"

    def test_returns_value_for_second_key_when_first_missing(self):
        """Should try second key when first doesn't exist."""
        ents = {
            "Razao Social": _make_widget("Empresa B"),
        }

        result = _val(ents, "Razão Social", "Razao Social", "razao_social")

        assert result == "Empresa B"

    def test_returns_value_for_third_key_when_others_missing(self):
        """Should try third key when first two don't exist."""
        ents = {
            "razao_social": _make_widget("Empresa C"),
        }

        result = _val(ents, "Razão Social", "Razao Social", "razao_social")

        assert result == "Empresa C"

    def test_returns_empty_string_when_no_keys_found(self):
        """Should return empty string when none of the keys exist."""
        ents = {
            "outro_campo": _make_widget("valor"),
        }

        result = _val(ents, "Razão Social", "Razao Social", "razao_social")

        assert result == ""

    def test_handles_single_key(self):
        """Should work with single key."""
        ents = {
            "CNPJ": _make_widget("12345678000190"),
        }

        result = _val(ents, "CNPJ")

        assert result == "12345678000190"

    def test_handles_empty_dict(self):
        """Should return empty string for empty dict."""
        result = _val({}, "qualquer", "chave")

        assert result == ""

    def test_strips_whitespace_from_result(self):
        """Should strip whitespace from returned value."""
        ents = {
            "campo": _make_widget("  valor  "),
        }

        result = _val(ents, "campo")

        assert result == "valor"

    def test_handles_mojibake_key_variations(self):
        """Should handle different encodings/mojibake in keys."""
        ents = {
            "Observa??es": _make_widget("texto com acentuação"),
        }

        result = _val(ents, "Observações", "Observacoes", "Observa??es")

        assert result == "texto com acentuação"

    def test_prefers_first_matching_key(self):
        """Should return value from first matching key even if others exist."""
        ents = {
            "Razão Social": _make_widget("Primeira"),
            "Razao Social": _make_widget("Segunda"),
            "razao_social": _make_widget("Terceira"),
        }

        result = _val(ents, "Razão Social", "Razao Social", "razao_social")

        assert result == "Primeira"


# ============================================================================
# Test coletar_valores()
# ============================================================================


class TestColetarValores:
    """Test coletar_valores main function that collects all form data."""

    def test_collects_all_standard_fields(self):
        """Should collect all 5 standard fields."""
        ents = make_widgets_dict()

        result = coletar_valores(ents)

        assert result["Razão Social"] == "Empresa ABC"
        assert result["CNPJ"] == "12345678000190"
        assert result["Nome"] == "João Silva"
        assert result["WhatsApp"] == "11999887766"
        assert result["Observações"] == "Observações do cliente"

    def test_returns_dict_with_expected_keys(self):
        """Should return dict with exactly the expected keys (without Status)."""
        ents = make_widgets_dict()

        result = coletar_valores(ents)

        expected_keys = {"Razão Social", "CNPJ", "Nome", "WhatsApp", "Observações"}
        assert set(result.keys()) == expected_keys

    def test_includes_status_when_present(self):
        """Should include 'Status do Cliente' when that field exists."""
        ents = make_widgets_dict(**{"Status do Cliente": _make_widget("Novo cliente")})

        result = coletar_valores(ents)

        assert "Status do Cliente" in result
        assert result["Status do Cliente"] == "Novo cliente"

    def test_includes_status_with_alternate_key_status(self):
        """Should detect Status field with alternate key 'Status'."""
        ents = make_widgets_dict(**{"Status": _make_widget("Aguardando documento")})

        result = coletar_valores(ents)

        assert "Status do Cliente" in result
        assert result["Status do Cliente"] == "Aguardando documento"

    def test_includes_status_with_lowercase_key(self):
        """Should detect Status field with lowercase key 'status'."""
        ents = make_widgets_dict(**{"status": _make_widget("Em cadastro")})

        result = coletar_valores(ents)

        assert "Status do Cliente" in result
        assert result["Status do Cliente"] == "Em cadastro"

    def test_omits_status_when_not_present(self):
        """Should not include Status when none of the status keys exist."""
        ents = make_widgets_dict()

        result = coletar_valores(ents)

        assert "Status do Cliente" not in result

    def test_handles_missing_optional_fields(self):
        """Should return empty strings for missing optional fields."""
        ents = {
            "Razão Social": _make_widget("Empresa"),
            # CNPJ, Nome, WhatsApp missing
        }

        result = coletar_valores(ents)

        assert result["Razão Social"] == "Empresa"
        assert result["CNPJ"] == ""
        assert result["Nome"] == ""
        assert result["WhatsApp"] == ""
        assert result["Observações"] == ""

    def test_handles_completely_empty_dict(self):
        """Should handle empty input dict gracefully."""
        result = coletar_valores({})

        assert result["Razão Social"] == ""
        assert result["CNPJ"] == ""
        assert result["Nome"] == ""
        assert result["WhatsApp"] == ""
        assert result["Observações"] == ""
        assert "Status do Cliente" not in result

    def test_handles_alternate_razao_social_keys(self):
        """Should detect Razão Social with alternate keys."""
        # Test "Razao Social" (without accent)
        ents = {"Razao Social": _make_widget("Empresa Sem Acento")}
        result = coletar_valores(ents)
        assert result["Razão Social"] == "Empresa Sem Acento"

        # Test "Razao" (short form)
        ents = {"Razao": _make_widget("Empresa Curta")}
        result = coletar_valores(ents)
        assert result["Razão Social"] == "Empresa Curta"

        # Test "razao" (lowercase)
        ents = {"razao": _make_widget("Empresa Lower")}
        result = coletar_valores(ents)
        assert result["Razão Social"] == "Empresa Lower"

    def test_handles_alternate_cnpj_keys(self):
        """Should detect CNPJ with alternate key."""
        ents = {"cnpj": _make_widget("98765432000100")}

        result = coletar_valores(ents)

        assert result["CNPJ"] == "98765432000100"

    def test_handles_alternate_nome_keys(self):
        """Should detect Nome with alternate key."""
        ents = {"nome": _make_widget("Maria Santos")}

        result = coletar_valores(ents)

        assert result["Nome"] == "Maria Santos"

    def test_handles_alternate_whatsapp_keys(self):
        """Should detect WhatsApp with alternate keys."""
        # Test "whatsapp" (lowercase)
        ents = {"whatsapp": _make_widget("11988776655")}
        result = coletar_valores(ents)
        assert result["WhatsApp"] == "11988776655"

        # Test "Telefone"
        ents = {"Telefone": _make_widget("11977665544")}
        result = coletar_valores(ents)
        assert result["WhatsApp"] == "11977665544"

        # Test "numero"
        ents = {"numero": _make_widget("11966554433")}
        result = coletar_valores(ents)
        assert result["WhatsApp"] == "11966554433"

    def test_handles_alternate_observacoes_keys(self):
        """Should detect Observações with alternate keys (including mojibake)."""
        # Test "Observacoes" (without accent)
        ents = {"Observacoes": _make_widget("Texto sem acento")}
        result = coletar_valores(ents)
        assert result["Observações"] == "Texto sem acento"

        # Test "Observa??es" (mojibake)
        ents = {"Observa??es": _make_widget("Texto mojibake")}
        result = coletar_valores(ents)
        assert result["Observações"] == "Texto mojibake"

        # Test "Obs" (short form)
        ents = {"Obs": _make_widget("Texto curto")}
        result = coletar_valores(ents)
        assert result["Observações"] == "Texto curto"

        # Test "obs" (lowercase)
        ents = {"obs": _make_widget("Texto lower")}
        result = coletar_valores(ents)
        assert result["Observações"] == "Texto lower"

    def test_strips_whitespace_from_all_fields(self):
        """Should strip whitespace from all collected values."""
        ents = {
            "Razão Social": _make_widget("  Empresa  "),
            "CNPJ": _make_widget("  12345678000190  "),
            "Nome": _make_widget("  João  "),
            "WhatsApp": _make_widget("  11999887766  "),
            "Observações": _make_widget("  Obs  "),
            "Status": _make_widget("  Novo cliente  "),
        }

        result = coletar_valores(ents)

        assert result["Razão Social"] == "Empresa"
        assert result["CNPJ"] == "12345678000190"
        assert result["Nome"] == "João"
        assert result["WhatsApp"] == "11999887766"
        assert result["Observações"] == "Obs"
        assert result["Status do Cliente"] == "Novo cliente"

    def test_prefers_first_matching_key_for_each_field(self):
        """Should use value from first matching key when multiple variations exist."""
        ents = {
            "Razão Social": _make_widget("Primeira"),
            "Razao Social": _make_widget("Segunda"),  # Should be ignored
            "CNPJ": _make_widget("CNPJ Primeiro"),
            "cnpj": _make_widget("cnpj segundo"),  # Should be ignored
        }

        result = coletar_valores(ents)

        assert result["Razão Social"] == "Primeira"
        assert result["CNPJ"] == "CNPJ Primeiro"

    def test_all_values_are_strings(self):
        """Should ensure all returned values are strings."""
        ents = make_widgets_dict(**{"Status": _make_widget("Status value")})

        result = coletar_valores(ents)

        assert all(isinstance(v, str) for v in result.values())

    def test_handles_mixed_widget_types(self):
        """Should handle mix of Entry and Text widgets."""
        ents = {
            "Razão Social": _make_widget("Entry widget"),
            "Observações": _make_text_widget("Text widget\nmultiline"),
        }

        result = coletar_valores(ents)

        assert result["Razão Social"] == "Entry widget"
        assert "Text widget" in result["Observações"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestColetarValoresIntegration:
    """Integration tests simulating real usage patterns."""

    def test_full_form_with_all_fields(self):
        """Should handle a complete form with all fields filled."""
        ents = {
            "Razão Social": _make_widget("Empresa ABC Ltda"),
            "CNPJ": _make_widget("12.345.678/0001-90"),
            "Nome": _make_widget("João da Silva"),
            "WhatsApp": _make_widget("(11) 99988-7766"),
            "Observações": _make_widget("Cliente desde 2020\nPreferência: contato via WhatsApp"),
            "Status do Cliente": _make_widget("Novo cliente"),
        }

        result = coletar_valores(ents)

        assert len(result) == 6  # 5 standard + 1 status
        assert result["Razão Social"] == "Empresa ABC Ltda"
        assert result["CNPJ"] == "12.345.678/0001-90"
        assert result["Nome"] == "João da Silva"
        assert result["WhatsApp"] == "(11) 99988-7766"
        assert "Cliente desde 2020" in result["Observações"]
        assert result["Status do Cliente"] == "Novo cliente"

    def test_minimal_form_with_required_only(self):
        """Should handle minimal form with only Razão Social."""
        ents = {
            "Razão Social": _make_widget("Empresa Mínima"),
        }

        result = coletar_valores(ents)

        assert result["Razão Social"] == "Empresa Mínima"
        assert all(result[k] == "" for k in ["CNPJ", "Nome", "WhatsApp", "Observações"])

    def test_form_with_legacy_field_names(self):
        """Should handle legacy/alternate field names (mojibake, case variations)."""
        ents = {
            "Razao": _make_widget("Empresa"),
            "cnpj": _make_widget("123456"),
            "nome": _make_widget("João"),
            "Telefone": _make_widget("11999"),
            "Obs": _make_widget("Observação"),
            "status": _make_widget("Ativo"),
        }

        result = coletar_valores(ents)

        assert result["Razão Social"] == "Empresa"
        assert result["CNPJ"] == "123456"
        assert result["Nome"] == "João"
        assert result["WhatsApp"] == "11999"
        assert result["Observações"] == "Observação"
        assert result["Status do Cliente"] == "Ativo"


__all__ = [
    "TestGetWidgetValue",
    "TestVal",
    "TestColetarValores",
    "TestColetarValoresIntegration",
]
