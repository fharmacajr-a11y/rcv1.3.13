# -*- coding: utf-8 -*-

"""Testes unitários para helpers de eventos de main_screen.

Round 7 - Fase 3: Testes para lógica de classificação de seleção e decisões.
"""

from __future__ import annotations

from src.modules.clientes.core.ui_helpers import (
    can_perform_multi_item_action,
    can_perform_single_item_action,
    classify_selection,
    get_selection_count,
    has_selection,
    validate_single_selection,
)


class TestClassifySelection:
    """Testes para classify_selection."""

    def test_classify_selection_empty_list(self) -> None:
        """Testa classificação de lista vazia."""
        status, client_id = classify_selection([])
        assert status == "none"
        assert client_id is None

    def test_classify_selection_empty_set(self) -> None:
        """Testa classificação de set vazio."""
        status, client_id = classify_selection(set())
        assert status == "none"
        assert client_id is None

    def test_classify_selection_single_item_list(self) -> None:
        """Testa classificação de lista com um item."""
        status, client_id = classify_selection(["123"])
        assert status == "single"
        assert client_id == "123"

    def test_classify_selection_single_item_set(self) -> None:
        """Testa classificação de set com um item."""
        status, client_id = classify_selection({"abc"})
        assert status == "single"
        assert client_id == "abc"

    def test_classify_selection_single_item_tuple(self) -> None:
        """Testa classificação de tupla com um item."""
        status, client_id = classify_selection(("xyz",))
        assert status == "single"
        assert client_id == "xyz"

    def test_classify_selection_multiple_items_list(self) -> None:
        """Testa classificação de lista com múltiplos itens."""
        status, client_id = classify_selection(["123", "456"])
        assert status == "multiple"
        assert client_id is None

    def test_classify_selection_multiple_items_set(self) -> None:
        """Testa classificação de set com múltiplos itens."""
        status, client_id = classify_selection({"abc", "def", "ghi"})
        assert status == "multiple"
        assert client_id is None

    def test_classify_selection_many_items(self) -> None:
        """Testa classificação com muitos itens."""
        many_ids = [str(i) for i in range(100)]
        status, client_id = classify_selection(many_ids)
        assert status == "multiple"
        assert client_id is None

    def test_classify_selection_preserves_id_type(self) -> None:
        """Testa que o ID retornado mantém o tipo original."""
        # String
        status, client_id = classify_selection(["string_id"])
        assert status == "single"
        assert client_id == "string_id"
        assert isinstance(client_id, str)


class TestCanPerformSingleItemAction:
    """Testes para can_perform_single_item_action."""

    def test_can_perform_single_item_action_with_single(self) -> None:
        """Testa que retorna True para status 'single'."""
        assert can_perform_single_item_action("single") is True

    def test_can_perform_single_item_action_with_none(self) -> None:
        """Testa que retorna False para status 'none'."""
        assert can_perform_single_item_action("none") is False

    def test_can_perform_single_item_action_with_multiple(self) -> None:
        """Testa que retorna False para status 'multiple'."""
        assert can_perform_single_item_action("multiple") is False


class TestCanPerformMultiItemAction:
    """Testes para can_perform_multi_item_action."""

    def test_can_perform_multi_item_action_with_single(self) -> None:
        """Testa que retorna True para status 'single'."""
        assert can_perform_multi_item_action("single") is True

    def test_can_perform_multi_item_action_with_multiple(self) -> None:
        """Testa que retorna True para status 'multiple'."""
        assert can_perform_multi_item_action("multiple") is True

    def test_can_perform_multi_item_action_with_none(self) -> None:
        """Testa que retorna False para status 'none'."""
        assert can_perform_multi_item_action("none") is False


class TestValidateSingleSelection:
    """Testes para validate_single_selection."""

    def test_validate_single_selection_valid(self) -> None:
        """Testa validação com seleção válida (exatamente 1 item)."""
        is_valid, client_id, error_key = validate_single_selection(["123"])

        assert is_valid is True
        assert client_id == "123"
        assert error_key is None

    def test_validate_single_selection_none_selected(self) -> None:
        """Testa validação com nenhum item selecionado."""
        is_valid, client_id, error_key = validate_single_selection([])

        assert is_valid is False
        assert client_id is None
        assert error_key == "none_selected"

    def test_validate_single_selection_multiple_selected(self) -> None:
        """Testa validação com múltiplos itens selecionados."""
        is_valid, client_id, error_key = validate_single_selection(["123", "456"])

        assert is_valid is False
        assert client_id is None
        assert error_key == "multiple_selected"

    def test_validate_single_selection_with_set(self) -> None:
        """Testa validação com set (tipo comum de retorno de seleção)."""
        is_valid, client_id, error_key = validate_single_selection({"abc"})

        assert is_valid is True
        assert client_id == "abc"
        assert error_key is None

    def test_validate_single_selection_empty_set(self) -> None:
        """Testa validação com set vazio."""
        is_valid, client_id, error_key = validate_single_selection(set())

        assert is_valid is False
        assert client_id is None
        assert error_key == "none_selected"


class TestGetSelectionCount:
    """Testes para get_selection_count."""

    def test_get_selection_count_empty(self) -> None:
        """Testa contagem com seleção vazia."""
        assert get_selection_count([]) == 0
        assert get_selection_count(set()) == 0

    def test_get_selection_count_single(self) -> None:
        """Testa contagem com um item."""
        assert get_selection_count(["123"]) == 1
        assert get_selection_count({"abc"}) == 1

    def test_get_selection_count_multiple(self) -> None:
        """Testa contagem com múltiplos itens."""
        assert get_selection_count(["1", "2", "3"]) == 3
        assert get_selection_count({"a", "b", "c", "d"}) == 4

    def test_get_selection_count_many(self) -> None:
        """Testa contagem com muitos itens."""
        many = [str(i) for i in range(100)]
        assert get_selection_count(many) == 100


class TestHasSelection:
    """Testes para has_selection."""

    def test_has_selection_empty_list(self) -> None:
        """Testa com lista vazia."""
        assert has_selection([]) is False

    def test_has_selection_empty_set(self) -> None:
        """Testa com set vazio."""
        assert has_selection(set()) is False

    def test_has_selection_single_item(self) -> None:
        """Testa com um item."""
        assert has_selection(["123"]) is True
        assert has_selection({"abc"}) is True

    def test_has_selection_multiple_items(self) -> None:
        """Testa com múltiplos itens."""
        assert has_selection(["1", "2", "3"]) is True
        assert has_selection({"a", "b"}) is True


class TestEventHelpersIntegration:
    """Testes de integração entre os helpers de eventos."""

    def test_workflow_single_selection_validation(self) -> None:
        """Testa workflow completo para validação de seleção única."""
        # Simula seleção de um item
        selected = {"client_123"}

        # 1. Verifica se há seleção
        assert has_selection(selected) is True

        # 2. Classifica a seleção
        status, client_id = classify_selection(selected)
        assert status == "single"
        assert client_id == "client_123"

        # 3. Valida se pode executar ação de item único
        assert can_perform_single_item_action(status) is True

        # 4. Valida seleção completa
        is_valid, validated_id, error = validate_single_selection(selected)
        assert is_valid is True
        assert validated_id == "client_123"
        assert error is None

    def test_workflow_no_selection(self) -> None:
        """Testa workflow quando não há seleção."""
        selected = set()

        # 1. Verifica que não há seleção
        assert has_selection(selected) is False
        assert get_selection_count(selected) == 0

        # 2. Classifica
        status, client_id = classify_selection(selected)
        assert status == "none"
        assert client_id is None

        # 3. Valida que não pode executar ações
        assert can_perform_single_item_action(status) is False
        assert can_perform_multi_item_action(status) is False

        # 4. Validação completa retorna erro
        is_valid, _, error = validate_single_selection(selected)
        assert is_valid is False
        assert error == "none_selected"

    def test_workflow_multiple_selection(self) -> None:
        """Testa workflow com múltiplos itens selecionados."""
        selected = {"client_1", "client_2", "client_3"}

        # 1. Verifica seleção múltipla
        assert has_selection(selected) is True
        assert get_selection_count(selected) == 3

        # 2. Classifica
        status, client_id = classify_selection(selected)
        assert status == "multiple"
        assert client_id is None

        # 3. Valida permissões
        assert can_perform_single_item_action(status) is False
        assert can_perform_multi_item_action(status) is True

        # 4. Validação para ação única falha
        is_valid, _, error = validate_single_selection(selected)
        assert is_valid is False
        assert error == "multiple_selected"

    def test_different_collection_types(self) -> None:
        """Testa que diferentes tipos de coleção funcionam consistentemente."""
        # List
        list_selection = ["id1"]
        assert classify_selection(list_selection)[0] == "single"
        assert validate_single_selection(list_selection)[0] is True

        # Set
        set_selection = {"id1"}
        assert classify_selection(set_selection)[0] == "single"
        assert validate_single_selection(set_selection)[0] is True

        # Tuple
        tuple_selection = ("id1",)
        assert classify_selection(tuple_selection)[0] == "single"
        assert validate_single_selection(tuple_selection)[0] is True

        # Todos devem ter contagem 1
        assert get_selection_count(list_selection) == 1
        assert get_selection_count(set_selection) == 1
        assert get_selection_count(tuple_selection) == 1
