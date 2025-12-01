"""
Round 11 - Comprehensive test coverage for clientes/forms/_dupes.py

Objetivo: Aumentar a cobertura de ~20% para 80%+ testando todas as funções e branches.

Funções testadas:
- has_cnpj_conflict(info) - Verifica se há conflito de CNPJ
- has_razao_conflict(info) - Verifica se há conflito de Razão Social
- build_cnpj_warning(info) - Constrói mensagem de warning para CNPJ duplicado
- build_razao_confirm(info) - Constrói mensagem de confirmação para Razão duplicada
- show_cnpj_warning_and_abort(parent, info) - Mostra warning e retorna False
- ask_razao_confirm(parent, info) - Mostra diálogo de confirmação
- _extract_conflict_attr(cliente, attr) - Extrai atributo de dict ou objeto
- _format_conflict_line(cliente) - Formata linha de conflito para exibição
- _normalized_conflicts(entries) - Normaliza entradas de conflitos
- _parent_kwargs(parent) - Extrai kwargs para messagebox
"""

from __future__ import annotations

import tkinter as tk
from typing import Any
from unittest.mock import Mock, patch

from src.modules.clientes.forms._dupes import (
    _extract_conflict_attr,
    _format_conflict_line,
    _normalized_conflicts,
    _parent_kwargs,
    ask_razao_confirm,
    build_cnpj_warning,
    build_razao_confirm,
    has_cnpj_conflict,
    has_razao_conflict,
    show_cnpj_warning_and_abort,
)


# ============================================================================
# Fixtures and Helpers
# ============================================================================


def make_client_dict(
    *,
    id: int,
    cnpj: str = "",
    razao_social: str = "",
) -> dict[str, Any]:
    """Helper to create a client dict for testing."""
    return {
        "id": id,
        "cnpj": cnpj,
        "razao_social": razao_social,
    }


def make_client_object(
    *,
    id: int,
    cnpj: str = "",
    razao_social: str = "",
) -> Any:
    """Helper to create a client object (Mock) for testing."""
    obj = Mock()
    obj.id = id
    obj.cnpj = cnpj
    obj.razao_social = razao_social
    return obj


# ============================================================================
# Test _extract_conflict_attr()
# ============================================================================


class TestExtractConflictAttr:
    """Test _extract_conflict_attr function that extracts attributes from dict or object."""

    def test_extracts_from_dict_with_key_present(self):
        """Should extract value from dict when key exists."""
        cliente = {"id": 123, "cnpj": "12345678000190"}

        result = _extract_conflict_attr(cliente, "id")

        assert result == 123

    def test_extracts_from_dict_returns_none_when_key_missing(self):
        """Should return None from dict when key doesn't exist."""
        cliente = {"id": 123}

        result = _extract_conflict_attr(cliente, "cnpj")

        assert result is None

    def test_extracts_from_object_with_attribute_present(self):
        """Should extract value from object when attribute exists."""
        cliente = make_client_object(id=456, cnpj="98765432000100")

        result = _extract_conflict_attr(cliente, "cnpj")

        assert result == "98765432000100"

    def test_extracts_from_object_returns_none_when_attribute_missing(self):
        """Should return None from object when attribute doesn't exist."""

        # Create a simple object without cnpj attribute
        class SimpleClient:
            def __init__(self):
                self.id = 789

        cliente = SimpleClient()

        result = _extract_conflict_attr(cliente, "cnpj")

        assert result is None

    def test_extracts_empty_string_from_dict(self):
        """Should extract empty string if that's the value."""
        cliente = {"razao_social": ""}

        result = _extract_conflict_attr(cliente, "razao_social")

        assert result == ""

    def test_extracts_none_value_from_dict(self):
        """Should extract None if that's the value in dict."""
        cliente = {"cnpj": None}

        result = _extract_conflict_attr(cliente, "cnpj")

        assert result is None


# ============================================================================
# Test _format_conflict_line()
# ============================================================================


class TestFormatConflictLine:
    """Test _format_conflict_line function that formats client info for display."""

    def test_formats_dict_with_all_fields(self):
        """Should format complete client dict."""
        cliente = make_client_dict(id=100, cnpj="11222333000144", razao_social="Empresa ABC Ltda")

        result = _format_conflict_line(cliente)

        assert result == "- ID 100 - Empresa ABC Ltda (CNPJ: 11222333000144)"

    def test_formats_object_with_all_fields(self):
        """Should format complete client object."""
        cliente = make_client_object(id=200, cnpj="55666777000188", razao_social="Farmácia São João")

        result = _format_conflict_line(cliente)

        assert result == "- ID 200 - Farmácia São João (CNPJ: 55666777000188)"

    def test_formats_with_missing_id(self):
        """Should use '?' when id is missing."""
        cliente = {"cnpj": "12345", "razao_social": "Empresa XYZ"}

        result = _format_conflict_line(cliente)

        assert "ID ?" in result
        assert "Empresa XYZ" in result

    def test_formats_with_missing_cnpj(self):
        """Should use '-' when CNPJ is missing."""
        cliente = {"id": 300, "razao_social": "Loja ABC"}

        result = _format_conflict_line(cliente)

        assert "ID 300" in result
        assert "(CNPJ: -)" in result

    def test_formats_with_missing_razao_social(self):
        """Should use '-' when razao_social is missing."""
        cliente = {"id": 400, "cnpj": "99888777000166"}

        result = _format_conflict_line(cliente)

        assert "ID 400 -" in result
        assert "(CNPJ: 99888777000166)" in result

    def test_formats_with_all_fields_missing(self):
        """Should handle completely empty client."""
        cliente: dict[str, Any] = {}

        result = _format_conflict_line(cliente)

        assert result == "- ID ? - - (CNPJ: -)"


# ============================================================================
# Test _normalized_conflicts()
# ============================================================================


class TestNormalizedConflicts:
    """Test _normalized_conflicts function that normalizes conflict entries."""

    def test_returns_empty_list_for_none(self):
        """Should return empty list when entries is None."""
        result = _normalized_conflicts(None)

        assert result == []

    def test_returns_same_list_when_already_list(self):
        """Should return the same list when input is already a list."""
        entries = [{"id": 1}, {"id": 2}]

        result = _normalized_conflicts(entries)

        assert result == entries
        assert result is entries  # Same object

    def test_converts_tuple_to_list(self):
        """Should convert tuple to list."""
        entries = ({"id": 1}, {"id": 2})

        result = _normalized_conflicts(entries)

        assert result == [{"id": 1}, {"id": 2}]
        assert isinstance(result, list)

    def test_converts_set_to_list(self):
        """Should convert set to list."""
        # Sets não mantém ordem, então usamos um elemento só para teste confiável
        entries = {"item"}

        result = _normalized_conflicts(entries)

        assert isinstance(result, list)
        assert "item" in result

    def test_returns_empty_list_for_empty_list(self):
        """Should return empty list for empty list input."""
        result = _normalized_conflicts([])

        assert result == []

    def test_converts_generator_to_list(self):
        """Should convert generator to list."""

        def gen():
            yield {"id": 1}
            yield {"id": 2}

        result = _normalized_conflicts(gen())

        assert result == [{"id": 1}, {"id": 2}]


# ============================================================================
# Test has_cnpj_conflict()
# ============================================================================


class TestHasCnpjConflict:
    """Test has_cnpj_conflict function that checks for CNPJ conflicts."""

    def test_returns_true_when_cnpj_conflict_exists(self):
        """Should return True when cnpj_conflict key has truthy value."""
        info = {"cnpj_conflict": {"id": 123, "cnpj": "12345"}}

        result = has_cnpj_conflict(info)

        assert result is True

    def test_returns_false_when_cnpj_conflict_is_none(self):
        """Should return False when cnpj_conflict is None."""
        info = {"cnpj_conflict": None}

        result = has_cnpj_conflict(info)

        assert result is False

    def test_returns_false_when_cnpj_conflict_is_empty_dict(self):
        """Should return False when cnpj_conflict is empty dict."""
        info = {"cnpj_conflict": {}}

        result = has_cnpj_conflict(info)

        assert result is False

    def test_returns_false_when_cnpj_conflict_key_missing(self):
        """Should return False when cnpj_conflict key doesn't exist."""
        info: dict[str, Any] = {"other_key": "value"}

        result = has_cnpj_conflict(info)

        assert result is False

    def test_returns_false_when_info_is_none(self):
        """Should return False when info is None."""
        result = has_cnpj_conflict(None)

        assert result is False

    def test_returns_false_when_info_is_empty_dict(self):
        """Should return False when info is empty dict."""
        result = has_cnpj_conflict({})

        assert result is False


# ============================================================================
# Test has_razao_conflict()
# ============================================================================


class TestHasRazaoConflict:
    """Test has_razao_conflict function that checks for Razão Social conflicts."""

    def test_returns_true_when_razao_conflicts_has_items(self):
        """Should return True when razao_conflicts has entries."""
        info = {
            "razao_conflicts": [
                {"id": 1, "razao_social": "Empresa A"},
                {"id": 2, "razao_social": "Empresa A"},
            ]
        }

        result = has_razao_conflict(info)

        assert result is True

    def test_returns_false_when_razao_conflicts_is_empty_list(self):
        """Should return False when razao_conflicts is empty list."""
        info = {"razao_conflicts": []}

        result = has_razao_conflict(info)

        assert result is False

    def test_returns_false_when_razao_conflicts_is_none(self):
        """Should return False when razao_conflicts is None."""
        info = {"razao_conflicts": None}

        result = has_razao_conflict(info)

        assert result is False

    def test_returns_false_when_razao_conflicts_key_missing(self):
        """Should return False when razao_conflicts key doesn't exist."""
        info: dict[str, Any] = {"other_key": "value"}

        result = has_razao_conflict(info)

        assert result is False

    def test_returns_false_when_info_is_none(self):
        """Should return False when info is None."""
        result = has_razao_conflict(None)

        assert result is False

    def test_returns_false_when_info_is_empty_dict(self):
        """Should return False when info is empty dict."""
        result = has_razao_conflict({})

        assert result is False

    def test_returns_true_when_razao_conflicts_is_tuple(self):
        """Should return True when razao_conflicts is non-empty tuple."""
        info = {"razao_conflicts": ({"id": 1}, {"id": 2})}

        result = has_razao_conflict(info)

        assert result is True


# ============================================================================
# Test build_cnpj_warning()
# ============================================================================


class TestBuildCnpjWarning:
    """Test build_cnpj_warning function that builds CNPJ warning message."""

    def test_builds_warning_with_complete_conflict(self):
        """Should build complete warning message with all fields."""
        conflict = make_client_dict(id=100, cnpj="12345678000190", razao_social="Empresa Conflitante")
        info = {"cnpj_conflict": conflict}

        title, message = build_cnpj_warning(info)

        assert title == "CNPJ duplicado"
        assert "ID 100" in message
        assert "Empresa Conflitante" in message
        assert "12345678000190" in message
        assert "CNPJ já cadastrado" in message

    def test_builds_warning_with_missing_id(self):
        """Should use '?' for missing id."""
        conflict = {"cnpj": "99999", "razao_social": "Empresa"}
        info = {"cnpj_conflict": conflict}

        title, message = build_cnpj_warning(info)

        assert "ID ?" in message

    def test_builds_warning_with_missing_razao_social(self):
        """Should use '-' for missing razao_social."""
        conflict = {"id": 200, "cnpj": "88888"}
        info = {"cnpj_conflict": conflict}

        title, message = build_cnpj_warning(info)

        assert "ID 200 -" in message

    def test_builds_warning_with_missing_cnpj(self):
        """Should use '-' for missing CNPJ."""
        conflict = {"id": 300, "razao_social": "Loja XYZ"}
        info = {"cnpj_conflict": conflict}

        title, message = build_cnpj_warning(info)

        assert "CNPJ registrado: -" in message

    def test_returns_empty_message_when_no_conflict(self):
        """Should return empty message when cnpj_conflict is None."""
        info = {"cnpj_conflict": None}

        title, message = build_cnpj_warning(info)

        assert title == "CNPJ duplicado"
        assert message == ""

    def test_returns_empty_message_when_conflict_key_missing(self):
        """Should return empty message when cnpj_conflict key doesn't exist."""
        info: dict[str, Any] = {}

        title, message = build_cnpj_warning(info)

        assert title == "CNPJ duplicado"
        assert message == ""


# ============================================================================
# Test build_razao_confirm()
# ============================================================================


class TestBuildRazaoConfirm:
    """Test build_razao_confirm function that builds Razão Social confirmation message."""

    def test_builds_confirm_with_one_conflict(self):
        """Should build message with single conflict."""
        conflicts = [make_client_dict(id=1, cnpj="111", razao_social="Empresa A")]
        info = {"razao_conflicts": conflicts}

        title, message = build_razao_confirm(info)

        assert title == "Razão Social repetida"
        assert "ID 1" in message
        assert "Empresa A" in message
        assert "CNPJ: 111" in message
        assert "Deseja continuar?" in message

    def test_builds_confirm_with_two_conflicts(self):
        """Should list both conflicts."""
        conflicts = [
            make_client_dict(id=1, cnpj="111", razao_social="Empresa A"),
            make_client_dict(id=2, cnpj="222", razao_social="Empresa A"),
        ]
        info = {"razao_conflicts": conflicts}

        title, message = build_razao_confirm(info)

        assert "ID 1" in message
        assert "ID 2" in message

    def test_builds_confirm_with_three_conflicts(self):
        """Should list all three conflicts."""
        conflicts = [
            make_client_dict(id=1, cnpj="111", razao_social="Empresa A"),
            make_client_dict(id=2, cnpj="222", razao_social="Empresa A"),
            make_client_dict(id=3, cnpj="333", razao_social="Empresa A"),
        ]
        info = {"razao_conflicts": conflicts}

        title, message = build_razao_confirm(info)

        assert "ID 1" in message
        assert "ID 2" in message
        assert "ID 3" in message
        assert "e mais" not in message  # Só 3, sem "e mais"

    def test_limits_display_to_three_conflicts(self):
        """Should limit display to first 3 conflicts and show count of remaining."""
        conflicts = [
            make_client_dict(id=1, cnpj="111", razao_social="Empresa A"),
            make_client_dict(id=2, cnpj="222", razao_social="Empresa A"),
            make_client_dict(id=3, cnpj="333", razao_social="Empresa A"),
            make_client_dict(id=4, cnpj="444", razao_social="Empresa A"),
            make_client_dict(id=5, cnpj="555", razao_social="Empresa A"),
        ]
        info = {"razao_conflicts": conflicts}

        title, message = build_razao_confirm(info)

        assert "ID 1" in message
        assert "ID 2" in message
        assert "ID 3" in message
        assert "ID 4" not in message
        assert "ID 5" not in message
        assert "e mais 2 registro(s)" in message

    def test_builds_confirm_with_four_conflicts_shows_one_remaining(self):
        """Should show '... e mais 1 registro(s)' for 4 conflicts."""
        conflicts = [make_client_dict(id=i, cnpj=f"{i}00", razao_social="Empresa") for i in range(1, 5)]
        info = {"razao_conflicts": conflicts}

        title, message = build_razao_confirm(info)

        assert "e mais 1 registro(s)" in message

    def test_builds_confirm_with_empty_conflicts(self):
        """Should handle empty conflicts list."""
        info = {"razao_conflicts": []}

        title, message = build_razao_confirm(info)

        assert title == "Razão Social repetida"
        assert "Deseja continuar?" in message
        # Mensagem deve ter apenas o header

    def test_builds_confirm_with_none_conflicts(self):
        """Should handle None conflicts."""
        info = {"razao_conflicts": None}

        title, message = build_razao_confirm(info)

        assert title == "Razão Social repetida"


# ============================================================================
# Test _parent_kwargs()
# ============================================================================


class TestParentKwargs:
    """Test _parent_kwargs function that extracts parent kwargs for messagebox."""

    def test_returns_parent_dict_for_tk_widget(self):
        """Should return dict with parent key for Tk widget."""
        parent = Mock(spec=tk.Misc)

        result = _parent_kwargs(parent)

        assert result == {"parent": parent}

    def test_returns_empty_dict_for_non_tk_object(self):
        """Should return empty dict for non-Tk object."""
        parent = "not a widget"

        result = _parent_kwargs(parent)

        assert result == {}

    def test_returns_empty_dict_for_none(self):
        """Should return empty dict for None."""
        result = _parent_kwargs(None)

        assert result == {}

    def test_returns_parent_dict_for_toplevel(self):
        """Should work with Toplevel widget."""
        parent = Mock(spec=tk.Toplevel)

        result = _parent_kwargs(parent)

        assert result == {"parent": parent}


# ============================================================================
# Test show_cnpj_warning_and_abort()
# ============================================================================


class TestShowCnpjWarningAndAbort:
    """Test show_cnpj_warning_and_abort function that shows warning dialog."""

    @patch("src.modules.clientes.forms._dupes.messagebox.showwarning")
    def test_shows_warning_and_returns_false(self, mock_showwarning):
        """Should show warning messagebox and return False."""
        parent = Mock(spec=tk.Misc)
        conflict = make_client_dict(id=100, cnpj="12345", razao_social="Empresa")
        info = {"cnpj_conflict": conflict}

        result = show_cnpj_warning_and_abort(parent, info)

        assert result is False
        mock_showwarning.assert_called_once()
        call_args = mock_showwarning.call_args
        assert call_args[0][0] == "CNPJ duplicado"
        assert "ID 100" in call_args[0][1]
        assert call_args[1] == {"parent": parent}

    @patch("src.modules.clientes.forms._dupes.messagebox.showwarning")
    def test_calls_showwarning_without_parent_for_non_tk(self, mock_showwarning):
        """Should call showwarning without parent kwarg for non-Tk parent."""
        parent = "not a widget"
        conflict = make_client_dict(id=200, cnpj="99999", razao_social="Loja")
        info = {"cnpj_conflict": conflict}

        result = show_cnpj_warning_and_abort(parent, info)

        assert result is False
        mock_showwarning.assert_called_once()
        call_args = mock_showwarning.call_args
        assert call_args[1] == {}  # Empty kwargs


# ============================================================================
# Test ask_razao_confirm()
# ============================================================================


class TestAskRazaoConfirm:
    """Test ask_razao_confirm function that shows confirmation dialog."""

    @patch("src.modules.clientes.forms._dupes.messagebox.askokcancel")
    def test_shows_askokcancel_and_returns_result(self, mock_askokcancel):
        """Should show askokcancel dialog and return its result."""
        mock_askokcancel.return_value = True
        parent = Mock(spec=tk.Misc)
        conflicts = [make_client_dict(id=1, cnpj="111", razao_social="Empresa")]
        info = {"razao_conflicts": conflicts}

        result = ask_razao_confirm(parent, info)

        assert result is True
        mock_askokcancel.assert_called_once()
        call_args = mock_askokcancel.call_args
        assert call_args[0][0] == "Razão Social repetida"
        assert "Deseja continuar?" in call_args[0][1]
        assert call_args[1] == {"parent": parent}

    @patch("src.modules.clientes.forms._dupes.messagebox.askokcancel")
    def test_returns_false_when_user_cancels(self, mock_askokcancel):
        """Should return False when user cancels."""
        mock_askokcancel.return_value = False
        parent = Mock(spec=tk.Misc)
        conflicts = [make_client_dict(id=2, cnpj="222", razao_social="Loja")]
        info = {"razao_conflicts": conflicts}

        result = ask_razao_confirm(parent, info)

        assert result is False

    @patch("src.modules.clientes.forms._dupes.messagebox.askokcancel")
    def test_calls_askokcancel_without_parent_for_non_tk(self, mock_askokcancel):
        """Should call askokcancel without parent kwarg for non-Tk parent."""
        mock_askokcancel.return_value = True
        parent = None
        conflicts = [make_client_dict(id=3, cnpj="333", razao_social="Farmácia")]
        info = {"razao_conflicts": conflicts}

        result = ask_razao_confirm(parent, info)

        assert result is True
        call_args = mock_askokcancel.call_args
        assert call_args[1] == {}  # Empty kwargs


__all__ = [
    "TestExtractConflictAttr",
    "TestFormatConflictLine",
    "TestNormalizedConflicts",
    "TestHasCnpjConflict",
    "TestHasRazaoConflict",
    "TestBuildCnpjWarning",
    "TestBuildRazaoConfirm",
    "TestParentKwargs",
    "TestShowCnpjWarningAndAbort",
    "TestAskRazaoConfirm",
]
