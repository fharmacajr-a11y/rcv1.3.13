# -*- coding: utf-8 -*-
"""Testes de consistência entre QuickActionsViewModel e QuickActionsController (MF-21).

Objetivo: garantir que ViewModel e Controller permaneçam alinhados quanto aos IDs
de actions suportadas, evitando duplicação perigosa e inconsistências.

Estratégia:
- Controller é a fonte de verdade via get_supported_action_ids()
- ViewModel define apenas UI (labels, ícones, ordem)
- Testes garantem que ambos expõem os mesmos IDs canônicos
- Testes garantem que "sites" (MF-17) está presente
- Testes garantem que alias "cashflow" NÃO aparece como action separada de UI
"""

from __future__ import annotations

import pytest

from src.modules.hub.controllers.quick_actions_controller import (
    QuickActionsController,
)
from src.modules.hub.viewmodels.quick_actions_vm import QuickActionsViewModel


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


class FakeNavigator:
    """Implementação fake do HubQuickActionsNavigatorProtocol para testes."""

    def open_clientes(self) -> None:
        pass

    def open_senhas(self) -> None:
        pass

    def open_auditoria(self) -> None:
        pass

    def open_fluxo_caixa(self) -> None:
        pass

    def open_anvisa(self) -> None:
        pass

    def open_farmacia_popular(self) -> None:
        pass

    def open_sngpc(self) -> None:
        pass

    def open_sifap(self) -> None:
        pass

    def open_sites(self) -> None:
        pass


@pytest.fixture
def fake_navigator():
    """Fixture que fornece um fake navigator."""
    return FakeNavigator()


@pytest.fixture
def quick_actions_controller(fake_navigator):
    """Fixture que fornece um QuickActionsController."""
    return QuickActionsController(navigator=fake_navigator)


@pytest.fixture
def quick_actions_viewmodel():
    """Fixture que fornece um QuickActionsViewModel."""
    return QuickActionsViewModel()


# ═══════════════════════════════════════════════════════════════════════
# Testes de consistência Controller <-> ViewModel
# ═══════════════════════════════════════════════════════════════════════


def test_viewmodel_e_controller_tem_mesmo_conjunto_de_action_ids(quick_actions_controller, quick_actions_viewmodel):
    """Teste: ViewModel e Controller expõem os mesmos IDs canônicos de actions.

    Controller é a fonte de verdade via get_supported_action_ids().
    ViewModel deve ter exatamente os mesmos IDs em sua lista de actions.
    """
    # Arrange & Act
    ids_controller = set(quick_actions_controller.get_supported_action_ids())

    # Obter IDs do ViewModel via build_state
    state = quick_actions_viewmodel.build_state()
    ids_viewmodel = {action.id for action in state.actions}

    # Assert
    assert ids_controller == ids_viewmodel, (
        f"IDs do Controller e ViewModel devem ser idênticos.\n"
        f"Controller: {sorted(ids_controller)}\n"
        f"ViewModel: {sorted(ids_viewmodel)}\n"
        f"Apenas no Controller: {sorted(ids_controller - ids_viewmodel)}\n"
        f"Apenas no ViewModel: {sorted(ids_viewmodel - ids_controller)}"
    )


def test_viewmodel_nao_repete_ids_de_actions(quick_actions_viewmodel):
    """Teste: ViewModel não contém IDs duplicados de actions."""
    # Arrange & Act
    state = quick_actions_viewmodel.build_state()
    ids = [action.id for action in state.actions]

    # Assert
    assert len(ids) == len(set(ids)), f"ViewModel contém IDs duplicados: {ids}\nIDs únicos: {set(ids)}"


def test_viewmodel_contem_sites_quando_controller_suporta_sites(quick_actions_controller, quick_actions_viewmodel):
    """Teste: Action 'sites' (MF-17) aparece tanto no Controller quanto no ViewModel."""
    # Arrange & Act
    ids_controller = quick_actions_controller.get_supported_action_ids()

    state = quick_actions_viewmodel.build_state()
    ids_viewmodel = {action.id for action in state.actions}

    # Assert
    assert "sites" in ids_controller, "Controller deve suportar 'sites'"
    assert "sites" in ids_viewmodel, "ViewModel deve expor 'sites' na UI"


def test_viewmodel_nao_expoe_alias_cashflow_como_item_separado(quick_actions_viewmodel):
    """Teste: Alias 'cashflow' NÃO aparece como action separada no ViewModel.

    'cashflow' é apenas um alias de 'fluxo_caixa' no Controller.
    Deve existir apenas 'fluxo_caixa' no ViewModel (UI).
    """
    # Arrange & Act
    state = quick_actions_viewmodel.build_state()
    ids_viewmodel = {action.id for action in state.actions}

    # Assert
    assert "cashflow" not in ids_viewmodel, "'cashflow' é alias, não deve aparecer como action separada no ViewModel"
    assert "fluxo_caixa" in ids_viewmodel, "'fluxo_caixa' deve aparecer no ViewModel (é a action canônica)"


def test_controller_get_supported_action_ids_retorna_tupla_imutavel(quick_actions_controller):
    """Teste: get_supported_action_ids() retorna tupla (imutável)."""
    # Act
    result = quick_actions_controller.get_supported_action_ids()

    # Assert
    assert isinstance(result, tuple), "Deve retornar tupla (imutável)"
    assert len(result) > 0, "Deve ter pelo menos uma action"


def test_controller_get_supported_action_ids_nao_inclui_alias(quick_actions_controller):
    """Teste: get_supported_action_ids() NÃO inclui aliases como 'cashflow'."""
    # Act
    ids = quick_actions_controller.get_supported_action_ids()

    # Assert
    assert "cashflow" not in ids, "'cashflow' é alias, não deve estar na lista canônica"
    assert "fluxo_caixa" in ids, "'fluxo_caixa' é a action canônica"


def test_controller_get_supported_action_ids_contem_todas_actions_principais(
    quick_actions_controller,
):
    """Teste: get_supported_action_ids() contém todas as 9 actions principais."""
    # Act
    ids = set(quick_actions_controller.get_supported_action_ids())

    # Expected: todas as actions que têm método open_* no Navigator Protocol
    expected = {
        "clientes",
        "senhas",
        "auditoria",
        "fluxo_caixa",
        "anvisa",
        "farmacia_popular",
        "sngpc",
        "sifap",
        "sites",
    }

    # Assert
    assert ids == expected, (
        f"IDs retornados devem incluir todas as 9 actions principais.\n"
        f"Esperado: {sorted(expected)}\n"
        f"Obtido: {sorted(ids)}\n"
        f"Faltando: {sorted(expected - ids)}\n"
        f"Extra: {sorted(ids - expected)}"
    )


def test_viewmodel_todas_actions_tem_label_nao_vazio(quick_actions_viewmodel):
    """Teste: Todas as actions do ViewModel têm label não-vazio."""
    # Arrange & Act
    state = quick_actions_viewmodel.build_state()

    # Assert
    for action in state.actions:
        assert action.label, f"Action '{action.id}' deve ter label não-vazio"
        assert len(action.label.strip()) > 0, f"Action '{action.id}' tem label vazio ou apenas espaços"


def test_viewmodel_todas_actions_estao_habilitadas_por_padrao(quick_actions_viewmodel):
    """Teste: Todas as actions do ViewModel estão habilitadas por padrão."""
    # Arrange & Act
    state = quick_actions_viewmodel.build_state()

    # Assert
    for action in state.actions:
        assert action.is_enabled is True, f"Action '{action.id}' deve estar habilitada por padrão"


def test_viewmodel_build_state_retorna_actions_ordenadas(quick_actions_viewmodel):
    """Teste: build_state() retorna actions ordenadas por campo 'order'."""
    # Arrange & Act
    state = quick_actions_viewmodel.build_state()

    # Assert - verificar que está ordenado por order
    orders = [action.order for action in state.actions]
    assert orders == sorted(orders), f"Actions devem estar ordenadas por 'order', mas encontrado: {orders}"


def test_viewmodel_build_state_nao_retorna_erro_por_padrao(quick_actions_viewmodel):
    """Teste: build_state() não retorna erro em condições normais."""
    # Arrange & Act
    state = quick_actions_viewmodel.build_state()

    # Assert
    assert state.error_message is None, "Não deve ter erro em condições normais"
    assert state.is_loading is False, "Não deve estar em loading após build"
    assert len(state.actions) > 0, "Deve retornar pelo menos uma action"


def test_controller_handle_action_click_reconhece_todos_ids_suportados(
    quick_actions_controller,
):
    """Teste: handle_action_click retorna True para todos os IDs suportados."""
    # Arrange
    supported_ids = quick_actions_controller.get_supported_action_ids()

    # Act & Assert
    for action_id in supported_ids:
        result = quick_actions_controller.handle_action_click(action_id)
        assert (
            result is True
        ), f"handle_action_click('{action_id}') deve retornar True (action está em get_supported_action_ids())"


def test_controller_handle_action_click_reconhece_alias_cashflow(quick_actions_controller):
    """Teste: handle_action_click reconhece alias 'cashflow' mesmo não estando em supported_ids."""
    # Arrange
    supported_ids = quick_actions_controller.get_supported_action_ids()

    # Assert setup
    assert "cashflow" not in supported_ids, "cashflow não deve estar em supported_ids"
    assert "fluxo_caixa" in supported_ids, "fluxo_caixa deve estar em supported_ids"

    # Act
    result = quick_actions_controller.handle_action_click("cashflow")

    # Assert
    assert result is True, "handle_action_click deve aceitar alias 'cashflow'"


def test_integracao_viewmodel_fornece_ui_para_todas_actions_do_controller(
    quick_actions_controller, quick_actions_viewmodel
):
    """Teste de integração: ViewModel fornece UI para todas as actions do Controller."""
    # Arrange
    controller_ids = set(quick_actions_controller.get_supported_action_ids())

    state = quick_actions_viewmodel.build_state()
    viewmodel_actions = {action.id: action for action in state.actions}

    # Assert - todas as actions do controller têm representação no viewmodel
    for action_id in controller_ids:
        assert (
            action_id in viewmodel_actions
        ), f"Action '{action_id}' suportada pelo Controller deve ter representação no ViewModel"

        # Verificar que tem dados de UI válidos
        vm_action = viewmodel_actions[action_id]
        assert vm_action.label, f"Action '{action_id}' deve ter label"
        assert vm_action.id == action_id, "IDs devem corresponder"
