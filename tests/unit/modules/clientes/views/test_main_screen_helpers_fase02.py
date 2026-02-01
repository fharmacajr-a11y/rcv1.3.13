"""Testes unitários para main_screen_helpers do módulo clientes - FASE 02.

REFACTOR-UI-007 - Fase 02: Selection logic
Cobertura: has_selection, get_selection_count, is_single_selection,
           is_multiple_selection, get_first_selected_id, can_edit_selection,
           can_delete_selection, can_open_folder_for_selection
"""

from __future__ import annotations


from src.modules.clientes.core.ui_helpers import (
    can_delete_selection,
    can_edit_selection,
    can_open_folder_for_selection,
    get_first_selected_id,
    get_selection_count,
    has_selection,
    is_multiple_selection,
    is_single_selection,
)


class TestHasSelection:
    """Testes para verificação de existência de seleção."""

    def test_with_single_selection(self):
        """Deve retornar True com 1 item selecionado."""
        result = has_selection(("item1",))
        assert result is True

    def test_with_multiple_selection(self):
        """Deve retornar True com múltiplos itens."""
        result = has_selection(("item1", "item2", "item3"))
        assert result is True

    def test_with_empty_selection(self):
        """Deve retornar False sem seleção."""
        result = has_selection(())
        assert result is False

    def test_with_empty_list(self):
        """Deve retornar False com lista vazia."""
        result = has_selection([])
        assert result is False


class TestGetSelectionCount:
    """Testes para contagem de itens selecionados."""

    def test_single_item(self):
        """Deve retornar 1 para item único."""
        result = get_selection_count(("item1",))
        assert result == 1

    def test_multiple_items(self):
        """Deve retornar contagem correta para múltiplos itens."""
        result = get_selection_count(("item1", "item2", "item3"))
        assert result == 3

    def test_empty_selection(self):
        """Deve retornar 0 sem seleção."""
        result = get_selection_count(())
        assert result == 0

    def test_large_selection(self):
        """Deve contar corretamente seleções grandes."""
        items = tuple(f"item{i}" for i in range(100))
        result = get_selection_count(items)
        assert result == 100


class TestIsSingleSelection:
    """Testes para verificação de seleção única."""

    def test_exactly_one_item(self):
        """Deve retornar True para exatamente 1 item."""
        result = is_single_selection(("item1",))
        assert result is True

    def test_multiple_items(self):
        """Deve retornar False para múltiplos itens."""
        result = is_single_selection(("item1", "item2"))
        assert result is False

    def test_empty_selection(self):
        """Deve retornar False sem seleção."""
        result = is_single_selection(())
        assert result is False

    def test_three_items(self):
        """Deve retornar False para 3 ou mais itens."""
        result = is_single_selection(("item1", "item2", "item3"))
        assert result is False


class TestIsMultipleSelection:
    """Testes para verificação de seleção múltipla."""

    def test_two_items(self):
        """Deve retornar True para 2 itens."""
        result = is_multiple_selection(("item1", "item2"))
        assert result is True

    def test_three_items(self):
        """Deve retornar True para 3+ itens."""
        result = is_multiple_selection(("item1", "item2", "item3"))
        assert result is True

    def test_single_item(self):
        """Deve retornar False para item único."""
        result = is_multiple_selection(("item1",))
        assert result is False

    def test_empty_selection(self):
        """Deve retornar False sem seleção."""
        result = is_multiple_selection(())
        assert result is False

    def test_large_selection(self):
        """Deve retornar True para seleções grandes."""
        items = tuple(f"item{i}" for i in range(50))
        result = is_multiple_selection(items)
        assert result is True


class TestGetFirstSelectedId:
    """Testes para obter ID do primeiro item selecionado."""

    def test_single_item(self):
        """Deve retornar ID do único item."""
        result = get_first_selected_id(("item1",))
        assert result == "item1"

    def test_multiple_items(self):
        """Deve retornar ID do primeiro item."""
        result = get_first_selected_id(("item1", "item2", "item3"))
        assert result == "item1"

    def test_empty_selection(self):
        """Deve retornar None sem seleção."""
        result = get_first_selected_id(())
        assert result is None

    def test_numeric_ids(self):
        """Deve funcionar com IDs numéricos."""
        result = get_first_selected_id(("123", "456"))
        assert result == "123"

    def test_special_characters(self):
        """Deve funcionar com IDs contendo caracteres especiais."""
        result = get_first_selected_id(("item-1_test", "item-2"))
        assert result == "item-1_test"


class TestCanEditSelection:
    """Testes para verificação de permissão de edição."""

    def test_single_selection_online(self):
        """Deve permitir edição com 1 item e online."""
        result = can_edit_selection(("item1",), is_online=True)
        assert result is True

    def test_single_selection_offline(self):
        """Não deve permitir edição offline."""
        result = can_edit_selection(("item1",), is_online=False)
        assert result is False

    def test_multiple_selection_online(self):
        """Não deve permitir edição com múltiplos itens."""
        result = can_edit_selection(("item1", "item2"), is_online=True)
        assert result is False

    def test_empty_selection_online(self):
        """Não deve permitir edição sem seleção."""
        result = can_edit_selection((), is_online=True)
        assert result is False

    def test_empty_selection_offline(self):
        """Não deve permitir edição sem seleção e offline."""
        result = can_edit_selection((), is_online=False)
        assert result is False

    def test_multiple_selection_offline(self):
        """Não deve permitir edição com múltiplos itens offline."""
        result = can_edit_selection(("item1", "item2"), is_online=False)
        assert result is False


class TestCanDeleteSelection:
    """Testes para verificação de permissão de exclusão."""

    def test_single_selection_online(self):
        """Deve permitir exclusão com 1 item e online."""
        result = can_delete_selection(("item1",), is_online=True)
        assert result is True

    def test_multiple_selection_online(self):
        """Deve permitir exclusão com múltiplos itens e online."""
        result = can_delete_selection(("item1", "item2"), is_online=True)
        assert result is True

    def test_single_selection_offline(self):
        """Não deve permitir exclusão offline."""
        result = can_delete_selection(("item1",), is_online=False)
        assert result is False

    def test_empty_selection_online(self):
        """Não deve permitir exclusão sem seleção."""
        result = can_delete_selection((), is_online=True)
        assert result is False

    def test_empty_selection_offline(self):
        """Não deve permitir exclusão sem seleção e offline."""
        result = can_delete_selection((), is_online=False)
        assert result is False

    def test_large_selection_online(self):
        """Deve permitir exclusão com muitos itens e online."""
        items = tuple(f"item{i}" for i in range(50))
        result = can_delete_selection(items, is_online=True)
        assert result is True


class TestCanOpenFolderForSelection:
    """Testes para verificação de permissão de abrir pasta."""

    def test_single_selection(self):
        """Deve permitir abrir pasta com 1 item."""
        result = can_open_folder_for_selection(("item1",))
        assert result is True

    def test_multiple_selection(self):
        """Não deve permitir abrir pasta com múltiplos itens."""
        result = can_open_folder_for_selection(("item1", "item2"))
        assert result is False

    def test_empty_selection(self):
        """Não deve permitir abrir pasta sem seleção."""
        result = can_open_folder_for_selection(())
        assert result is False

    def test_three_items(self):
        """Não deve permitir abrir pasta com 3+ itens."""
        result = can_open_folder_for_selection(("item1", "item2", "item3"))
        assert result is False


# Testes de integração


class TestSelectionWorkflows:
    """Testes de workflows completos de seleção."""

    def test_edit_workflow_valid(self):
        """Simula workflow válido de edição."""
        selection = ("client_123",)

        # Verifica pré-condições
        assert has_selection(selection)
        assert is_single_selection(selection)
        assert can_edit_selection(selection, is_online=True)

        # Obtém ID para edição
        client_id = get_first_selected_id(selection)
        assert client_id == "client_123"

    def test_edit_workflow_invalid_multiple(self):
        """Simula tentativa de edição com múltiplos itens."""
        selection = ("client_123", "client_456")

        # Verifica estado
        assert has_selection(selection)
        assert is_multiple_selection(selection)
        assert not is_single_selection(selection)
        assert not can_edit_selection(selection, is_online=True)

    def test_delete_workflow_single(self):
        """Simula exclusão de item único."""
        selection = ("client_123",)

        # Verifica permissão
        assert can_delete_selection(selection, is_online=True)
        assert get_selection_count(selection) == 1

    def test_delete_workflow_multiple(self):
        """Simula exclusão em massa."""
        selection = ("client_123", "client_456", "client_789")

        # Verifica permissão
        assert can_delete_selection(selection, is_online=True)
        assert get_selection_count(selection) == 3
        assert is_multiple_selection(selection)

    def test_open_folder_workflow(self):
        """Simula abertura de pasta do cliente."""
        selection = ("client_123",)

        # Verifica permissão
        assert can_open_folder_for_selection(selection)

        # Obtém ID para localizar pasta
        client_id = get_first_selected_id(selection)
        assert client_id == "client_123"

    def test_offline_workflow(self):
        """Simula operações offline."""
        selection = ("client_123",)

        # Nenhuma operação de rede deve ser permitida
        assert not can_edit_selection(selection, is_online=False)
        assert not can_delete_selection(selection, is_online=False)

        # Operações locais (como abrir pasta) ainda permitidas
        assert can_open_folder_for_selection(selection)

    def test_empty_selection_workflow(self):
        """Simula estado sem seleção."""
        selection = ()

        # Nenhuma operação deve ser permitida
        assert not has_selection(selection)
        assert get_selection_count(selection) == 0
        assert not can_edit_selection(selection, is_online=True)
        assert not can_delete_selection(selection, is_online=True)
        assert not can_open_folder_for_selection(selection)
        assert get_first_selected_id(selection) is None

    def test_multi_select_restrictions(self):
        """Simula restrições de seleção múltipla."""
        selection = ("client_123", "client_456")

        # Algumas operações bloqueadas
        assert not can_edit_selection(selection, is_online=True)
        assert not can_open_folder_for_selection(selection)

        # Outras permitidas
        assert can_delete_selection(selection, is_online=True)

    def test_selection_state_transitions(self):
        """Simula transições de estado de seleção."""
        # Estado 1: Nenhuma seleção
        sel1 = ()
        assert not has_selection(sel1)

        # Estado 2: Usuário seleciona 1 item
        sel2 = ("item1",)
        assert has_selection(sel2)
        assert is_single_selection(sel2)
        assert can_edit_selection(sel2, is_online=True)

        # Estado 3: Usuário adiciona mais itens (Ctrl+Click)
        sel3 = ("item1", "item2", "item3")
        assert is_multiple_selection(sel3)
        assert not can_edit_selection(sel3, is_online=True)
        assert can_delete_selection(sel3, is_online=True)


class TestSelectionEdgeCases:
    """Testes de casos extremos de seleção."""

    def test_all_functions_with_empty_tuple(self):
        """Garante comportamento consistente com tupla vazia."""
        empty = ()

        assert not has_selection(empty)
        assert get_selection_count(empty) == 0
        assert not is_single_selection(empty)
        assert not is_multiple_selection(empty)
        assert get_first_selected_id(empty) is None
        assert not can_edit_selection(empty, is_online=True)
        assert not can_delete_selection(empty, is_online=True)
        assert not can_open_folder_for_selection(empty)

    def test_all_functions_with_single_item(self):
        """Garante comportamento consistente com item único."""
        single = ("item1",)

        assert has_selection(single)
        assert get_selection_count(single) == 1
        assert is_single_selection(single)
        assert not is_multiple_selection(single)
        assert get_first_selected_id(single) == "item1"
        assert can_edit_selection(single, is_online=True)
        assert can_delete_selection(single, is_online=True)
        assert can_open_folder_for_selection(single)

    def test_very_long_id(self):
        """Deve funcionar com IDs muito longos."""
        long_id = "client_" + "x" * 1000
        selection = (long_id,)

        assert get_first_selected_id(selection) == long_id

    def test_empty_string_id(self):
        """Deve funcionar com ID vazio (edge case)."""
        selection = ("",)

        assert has_selection(selection)
        assert get_first_selected_id(selection) == ""

    def test_unicode_ids(self):
        """Deve funcionar com IDs contendo Unicode."""
        selection = ("cliente_José_Ñoño_日本",)

        assert get_first_selected_id(selection) == "cliente_José_Ñoño_日本"

    def test_online_flag_variations(self):
        """Testa todas combinações de online/offline."""
        sel_single = ("item1",)
        sel_multi = ("item1", "item2")
        sel_empty = ()

        # Online
        assert can_edit_selection(sel_single, is_online=True)
        assert can_delete_selection(sel_single, is_online=True)
        assert can_delete_selection(sel_multi, is_online=True)

        # Offline
        assert not can_edit_selection(sel_single, is_online=False)
        assert not can_delete_selection(sel_single, is_online=False)
        assert not can_delete_selection(sel_multi, is_online=False)
        assert not can_delete_selection(sel_empty, is_online=False)
