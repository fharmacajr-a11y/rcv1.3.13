# -*- coding: utf-8 -*-
"""
Testes para lixeira_helpers.py - Fase 01

Cobertura:
1. format_trash_status_text (6 testes)
2. calculate_trash_button_states (5 testes)
3. validate_selection_for_action (4 testes)
4. extract_field_value (7 testes)
5. format_confirmation_message (5 testes)
6. format_progress_text (5 testes)
7. format_result_message (6 testes)

Total: 38 testes
"""

from __future__ import annotations


from src.modules.lixeira.views.lixeira_helpers import (
    calculate_trash_button_states,
    extract_field_value,
    format_confirmation_message,
    format_progress_text,
    format_result_message,
    format_trash_status_text,
    validate_selection_for_action,
)


# ==============================================================================
# 1. format_trash_status_text (6 testes)
# ==============================================================================


def test_format_trash_status_text_zero_items() -> None:
    """Testa formatação com zero itens."""
    assert format_trash_status_text(0) == "0 item(ns) na lixeira"


def test_format_trash_status_text_one_item() -> None:
    """Testa formatação com um item."""
    assert format_trash_status_text(1) == "1 item(ns) na lixeira"


def test_format_trash_status_text_multiple_items() -> None:
    """Testa formatação com múltiplos itens."""
    assert format_trash_status_text(42) == "42 item(ns) na lixeira"


def test_format_trash_status_text_large_count() -> None:
    """Testa formatação com quantidade grande."""
    assert format_trash_status_text(9999) == "9999 item(ns) na lixeira"


def test_format_trash_status_text_negative_count() -> None:
    """Testa formatação com valor negativo (edge case)."""
    result = format_trash_status_text(-5)
    assert result == "-5 item(ns) na lixeira"


def test_format_trash_status_text_return_type() -> None:
    """Valida que retorno é sempre string."""
    result = format_trash_status_text(10)
    assert isinstance(result, str)


# ==============================================================================
# 2. calculate_trash_button_states (5 testes)
# ==============================================================================


def test_calculate_trash_button_states_no_selection_not_busy() -> None:
    """Testa estados quando não há seleção e não está busy."""
    result = calculate_trash_button_states(has_selection=False, is_busy=False)
    assert result == {
        "restore_enabled": False,
        "purge_enabled": False,
        "refresh_enabled": True,
        "close_enabled": True,
    }


def test_calculate_trash_button_states_has_selection_not_busy() -> None:
    """Testa estados quando há seleção e não está busy."""
    result = calculate_trash_button_states(has_selection=True, is_busy=False)
    assert result == {
        "restore_enabled": True,
        "purge_enabled": True,
        "refresh_enabled": True,
        "close_enabled": True,
    }


def test_calculate_trash_button_states_no_selection_busy() -> None:
    """Testa estados quando não há seleção mas está busy."""
    result = calculate_trash_button_states(has_selection=False, is_busy=True)
    assert result == {
        "restore_enabled": False,
        "purge_enabled": False,
        "refresh_enabled": False,
        "close_enabled": False,
    }


def test_calculate_trash_button_states_has_selection_busy() -> None:
    """Testa estados quando há seleção mas está busy (busy prevalece)."""
    result = calculate_trash_button_states(has_selection=True, is_busy=True)
    assert result == {
        "restore_enabled": False,
        "purge_enabled": False,
        "refresh_enabled": False,
        "close_enabled": False,
    }


def test_calculate_trash_button_states_return_structure() -> None:
    """Valida estrutura do dicionário retornado."""
    result = calculate_trash_button_states(has_selection=True, is_busy=False)
    assert isinstance(result, dict)
    assert set(result.keys()) == {
        "restore_enabled",
        "purge_enabled",
        "refresh_enabled",
        "close_enabled",
    }
    assert all(isinstance(v, bool) for v in result.values())


# ==============================================================================
# 3. validate_selection_for_action (4 testes)
# ==============================================================================


def test_validate_selection_for_action_no_selection() -> None:
    """Testa validação sem seleção."""
    is_valid, msg = validate_selection_for_action(0, "restaurar")
    assert not is_valid
    assert msg == "Selecione pelo menos um registro para restaurar."


def test_validate_selection_for_action_with_selection() -> None:
    """Testa validação com seleção válida."""
    is_valid, msg = validate_selection_for_action(1, "restaurar")
    assert is_valid
    assert msg == ""


def test_validate_selection_for_action_multiple_selection() -> None:
    """Testa validação com múltiplos itens selecionados."""
    is_valid, msg = validate_selection_for_action(5, "apagar")
    assert is_valid
    assert msg == ""


def test_validate_selection_for_action_default_action_name() -> None:
    """Testa mensagem com nome de ação padrão."""
    is_valid, msg = validate_selection_for_action(0)
    assert not is_valid
    assert msg == "Selecione pelo menos um registro para ação."


# ==============================================================================
# 4. extract_field_value (7 testes)
# ==============================================================================


def test_extract_field_value_from_object_attribute() -> None:
    """Testa extração de campo de objeto com atributo."""

    class Cliente:
        def __init__(self) -> None:
            self.razao_social = "Empresa X"

    result = extract_field_value(Cliente(), "razao_social")
    assert result == "Empresa X"


def test_extract_field_value_from_dict() -> None:
    """Testa extração de campo de dicionário."""
    obj = {"nome": "João"}
    result = extract_field_value(obj, "nome", "name")
    assert result == "João"


def test_extract_field_value_fallback_to_second_field() -> None:
    """Testa fallback para segundo nome de campo."""
    obj = {"name": "John"}
    result = extract_field_value(obj, "nome", "name")
    assert result == "John"


def test_extract_field_value_no_field_found() -> None:
    """Testa quando nenhum campo é encontrado."""
    obj = {}
    result = extract_field_value(obj, "nome", "name")
    assert result is None


def test_extract_field_value_none_object() -> None:
    """Testa extração de None."""
    result = extract_field_value(None, "campo")
    assert result is None


def test_extract_field_value_skips_none_values() -> None:
    """Testa que valores None são ignorados."""
    obj = {"campo1": None, "campo2": "valor"}
    result = extract_field_value(obj, "campo1", "campo2")
    assert result == "valor"


def test_extract_field_value_with_exception_in_getattr() -> None:
    """Testa comportamento com exceção em getattr."""

    class BadObject:
        @property
        def bad_prop(self) -> str:
            raise ValueError("Erro!")

    obj = BadObject()
    # Deve retornar None ao invés de propagar exceção
    result = extract_field_value(obj, "bad_prop")
    assert result is None


# ==============================================================================
# 5. format_confirmation_message (5 testes)
# ==============================================================================


def test_format_confirmation_message_restore_single() -> None:
    """Testa mensagem de restauração para um item."""
    result = format_confirmation_message("Restaurar", 1, False)
    assert result == "Restaurar 1 registro(s) para a lista principal?"


def test_format_confirmation_message_restore_multiple() -> None:
    """Testa mensagem de restauração para múltiplos itens."""
    result = format_confirmation_message("Restaurar", 5, False)
    assert result == "Restaurar 5 registro(s) para a lista principal?"


def test_format_confirmation_message_purge_destructive() -> None:
    """Testa mensagem de apagar definitivo (destrutiva)."""
    result = format_confirmation_message("Apagar", 3, True)
    assert "APAGAR DEFINITIVAMENTE" in result
    assert "3 registro(s)" in result
    assert "não pode ser desfeita" in result


def test_format_confirmation_message_purge_multiple_destructive() -> None:
    """Testa mensagem destrutiva com múltiplos itens."""
    result = format_confirmation_message("Apagar", 10, True)
    assert "APAGAR DEFINITIVAMENTE 10 registro(s)?" in result


def test_format_confirmation_message_non_destructive_structure() -> None:
    """Valida estrutura de mensagem não-destrutiva."""
    result = format_confirmation_message("Arquivar", 7, False)
    assert "Arquivar 7 registro(s) para a lista principal?" == result


# ==============================================================================
# 6. format_progress_text (5 testes)
# ==============================================================================


def test_format_progress_text_start() -> None:
    """Testa texto de progresso no início."""
    result = format_progress_text(0, 10)
    assert result == "Apagando 0/10 registro(s)... Aguarde."


def test_format_progress_text_mid() -> None:
    """Testa texto de progresso no meio."""
    result = format_progress_text(5, 10)
    assert result == "Apagando 5/10 registro(s)... Aguarde."


def test_format_progress_text_end() -> None:
    """Testa texto de progresso no fim."""
    result = format_progress_text(10, 10)
    assert result == "Apagando 10/10 registro(s)... Aguarde."


def test_format_progress_text_custom_action() -> None:
    """Testa texto de progresso com ação customizada."""
    result = format_progress_text(3, 7, "Restaurando")
    assert result == "Restaurando 3/7 registro(s)... Aguarde."


def test_format_progress_text_single_item() -> None:
    """Testa texto de progresso com um único item."""
    result = format_progress_text(1, 1)
    assert result == "Apagando 1/1 registro(s)... Aguarde."


# ==============================================================================
# 7. format_result_message (6 testes)
# ==============================================================================


def test_format_result_message_success_no_errors() -> None:
    """Testa mensagem de sucesso sem erros."""
    title, msg, is_err = format_result_message(5, None, "restaurado(s)")
    assert title == "Pronto"
    assert msg == "5 registro(s) restaurado(s)."
    assert not is_err


def test_format_result_message_success_empty_error_list() -> None:
    """Testa mensagem de sucesso com lista de erros vazia."""
    title, msg, is_err = format_result_message(3, [], "apagado(s)")
    assert title == "Pronto"
    assert msg == "3 registro(s) apagado(s)."
    assert not is_err


def test_format_result_message_partial_failure() -> None:
    """Testa mensagem de falha parcial."""
    errors = [(1, "Erro X"), (2, "Erro Y")]
    title, msg, is_err = format_result_message(3, errors, "apagado(s)")
    assert title == "Falha parcial"
    assert "3 apagado(s)" in msg
    assert "ID 1: Erro X" in msg
    assert "ID 2: Erro Y" in msg
    assert is_err


def test_format_result_message_single_error() -> None:
    """Testa mensagem com um único erro."""
    errors = [(10, "Registro não encontrado")]
    title, msg, is_err = format_result_message(0, errors, "restaurado(s)")
    assert title == "Falha parcial"
    assert "ID 10: Registro não encontrado" in msg
    assert is_err


def test_format_result_message_multiple_errors() -> None:
    """Testa mensagem com múltiplos erros."""
    errors = [(1, "Erro A"), (2, "Erro B"), (3, "Erro C")]
    title, msg, is_err = format_result_message(7, errors, "apagado(s)")
    assert title == "Falha parcial"
    assert "7 apagado(s)" in msg
    assert all(f"ID {i}: Erro {c}" in msg for i, c in [(1, "A"), (2, "B"), (3, "C")])
    assert is_err


def test_format_result_message_return_structure() -> None:
    """Valida estrutura da tupla retornada."""
    title, msg, is_err = format_result_message(5, None)
    assert isinstance(title, str)
    assert isinstance(msg, str)
    assert isinstance(is_err, bool)
