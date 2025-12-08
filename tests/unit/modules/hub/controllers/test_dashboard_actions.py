# -*- coding: utf-8 -*-
"""Testes unitários para DashboardActionController - FASE HUB-REFACTOR-03.

Valida que o controller headless encapsula corretamente a lógica de navegação
dos cards do dashboard, sem dependências de Tkinter.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.modules.hub.controllers import DashboardActionController
from src.modules.hub.dashboard_service import DashboardSnapshot
from src.modules.hub.viewmodels import DashboardViewModel


# ============================================================================
# FIXTURES
# ============================================================================


class FakeNavigator:
    """Fake Navigator para testes (implementa HubNavigatorProtocol)."""

    def __init__(self):
        self.clients_called = False
        self.pending_called = False
        self.tasks_called = False

    def go_to_clients(self) -> None:
        """Marca que navegação para clientes foi chamada."""
        self.clients_called = True

    def go_to_pending(self) -> None:
        """Marca que navegação para pendências foi chamada."""
        self.pending_called = True

    def go_to_tasks_today(self) -> None:
        """Marca que navegação para tarefas foi chamada."""
        self.tasks_called = True


@pytest.fixture
def fake_navigator():
    """Cria um fake navigator para testes."""
    return FakeNavigator()


@pytest.fixture
def controller(fake_navigator):
    """Cria um DashboardActionController com fake navigator."""
    return DashboardActionController(navigator=fake_navigator)


@pytest.fixture
def populated_state():
    """Cria um DashboardViewState populado para testes."""
    snapshot = DashboardSnapshot(
        active_clients=42,
        pending_obligations=5,
        tasks_today=3,
    )
    vm = DashboardViewModel(service=lambda org_id, today: snapshot)
    return vm.load(org_id="test-org", today=None)


@pytest.fixture
def empty_state():
    """Cria um DashboardViewState vazio para testes."""
    snapshot = DashboardSnapshot(
        active_clients=0,
        pending_obligations=0,
        tasks_today=0,
    )
    vm = DashboardViewModel(service=lambda org_id, today: snapshot)
    return vm.load(org_id="test-org", today=None)


# ============================================================================
# TESTES DE INICIALIZAÇÃO
# ============================================================================


class TestDashboardActionControllerInit:
    """Testes de inicialização do controller."""

    def test_init_with_navigator(self, fake_navigator):
        """Controller aceita navigator no construtor."""
        controller = DashboardActionController(navigator=fake_navigator)
        assert controller._navigator is fake_navigator

    def test_init_with_custom_logger(self, fake_navigator):
        """Controller aceita logger customizado."""
        mock_logger = Mock()
        controller = DashboardActionController(navigator=fake_navigator, logger=mock_logger)
        assert controller._logger is mock_logger


# ============================================================================
# TESTES DE handle_clients_card_click
# ============================================================================


class TestHandleClientsCardClick:
    """Testes para handle_clients_card_click."""

    def test_navigate_to_clients_with_populated_state(self, controller, fake_navigator, populated_state):
        """Com clientes ativos, deve navegar para tela de clientes."""
        controller.handle_clients_card_click(populated_state)
        assert fake_navigator.clients_called is True
        assert fake_navigator.pending_called is False
        assert fake_navigator.tasks_called is False

    def test_navigate_to_clients_with_empty_state(self, controller, fake_navigator, empty_state):
        """Mesmo sem clientes, deve navegar para tela de clientes."""
        controller.handle_clients_card_click(empty_state)
        assert fake_navigator.clients_called is True

    def test_raises_on_navigator_error(self, controller, populated_state):
        """Se navigator lançar erro, controller deve propagar como RuntimeError."""
        controller._navigator.go_to_clients = Mock(side_effect=Exception("Navigator error"))

        with pytest.raises(RuntimeError, match="Erro ao abrir tela de Clientes"):
            controller.handle_clients_card_click(populated_state)


# ============================================================================
# TESTES DE handle_pending_card_click
# ============================================================================


class TestHandlePendingCardClick:
    """Testes para handle_pending_card_click."""

    def test_navigate_to_pending_with_populated_state(self, controller, fake_navigator, populated_state):
        """Com pendências, deve navegar para tela de auditoria."""
        controller.handle_pending_card_click(populated_state)
        assert fake_navigator.pending_called is True
        assert fake_navigator.clients_called is False
        assert fake_navigator.tasks_called is False

    def test_navigate_to_pending_with_empty_state(self, controller, fake_navigator, empty_state):
        """Mesmo sem pendências, deve navegar para tela de auditoria."""
        controller.handle_pending_card_click(empty_state)
        assert fake_navigator.pending_called is True

    def test_raises_on_navigator_error(self, controller, populated_state):
        """Se navigator lançar erro, controller deve propagar como RuntimeError."""
        controller._navigator.go_to_pending = Mock(side_effect=Exception("Navigator error"))

        with pytest.raises(RuntimeError, match="Erro ao abrir tela de Auditoria"):
            controller.handle_pending_card_click(populated_state)


# ============================================================================
# TESTES DE handle_tasks_today_card_click
# ============================================================================


class TestHandleTasksTodayCardClick:
    """Testes para handle_tasks_today_card_click."""

    def test_navigate_to_tasks_with_populated_state(self, controller, fake_navigator, populated_state):
        """Com tarefas, deve navegar para interface de tarefas."""
        controller.handle_tasks_today_card_click(populated_state)
        assert fake_navigator.tasks_called is True
        assert fake_navigator.clients_called is False
        assert fake_navigator.pending_called is False

    def test_navigate_to_tasks_with_empty_state(self, controller, fake_navigator, empty_state):
        """Mesmo sem tarefas, deve navegar para interface de tarefas."""
        controller.handle_tasks_today_card_click(empty_state)
        assert fake_navigator.tasks_called is True

    def test_raises_on_navigator_error(self, controller, populated_state):
        """Se navigator lançar erro, controller deve propagar como RuntimeError."""
        controller._navigator.go_to_tasks_today = Mock(side_effect=Exception("Navigator error"))

        with pytest.raises(RuntimeError, match="Erro ao abrir tarefas"):
            controller.handle_tasks_today_card_click(populated_state)


# ============================================================================
# TESTES DE INTEGRAÇÃO
# ============================================================================


class TestDashboardActionControllerIntegration:
    """Testes de integração do controller."""

    def test_multiple_actions_independent(self, controller, fake_navigator, populated_state):
        """Múltiplas ações devem ser independentes."""
        # Clicar em clientes
        controller.handle_clients_card_click(populated_state)
        assert fake_navigator.clients_called is True

        # Reset para simular nova ação
        fake_navigator.clients_called = False

        # Clicar em pendências
        controller.handle_pending_card_click(populated_state)
        assert fake_navigator.pending_called is True
        assert fake_navigator.clients_called is False  # Não deve ter sido chamado novamente

    def test_controller_is_headless(self, controller):
        """Controller não deve ter dependências de Tkinter."""
        import sys

        # Verificar que módulos Tkinter não foram importados pelo controller
        controller_module = sys.modules.get("src.modules.hub.controllers.dashboard_actions")
        if controller_module:
            # Verificar que não há imports de tk/ttk no módulo
            module_dict = vars(controller_module)
            assert "tk" not in module_dict
            assert "tkinter" not in module_dict
            assert "ttkbootstrap" not in module_dict
