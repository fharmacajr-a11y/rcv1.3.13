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
        self.open_anvisa_called = False
        self.open_anvisa_history_called = False
        self.open_anvisa_history_client_id = None
        self.open_anvisa_history_picker_called = False
        self.open_anvisa_history_picker_items = None

    def go_to_clients(self) -> None:
        """Marca que navegação para clientes foi chamada."""
        self.clients_called = True

    def go_to_pending(self) -> None:
        """Marca que navegação para pendências foi chamada."""
        self.pending_called = True

    def go_to_tasks_today(self) -> None:
        """Marca que navegação para tarefas foi chamada."""
        self.tasks_called = True

    def open_anvisa(self) -> None:
        """Marca que abertura da tela ANVISA foi chamada."""
        self.open_anvisa_called = True

    def open_anvisa_history(self, client_id: str) -> None:
        """Marca que abertura do histórico ANVISA foi chamada."""
        self.open_anvisa_history_called = True
        self.open_anvisa_history_client_id = client_id

    def open_anvisa_history_picker(self, items: list) -> None:
        """Marca que abertura do picker de histórico ANVISA foi chamada."""
        self.open_anvisa_history_picker_called = True
        self.open_anvisa_history_picker_items = items


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


# ============================================================================
# TESTES DE MODO ANVISA-ONLY
# ============================================================================


class TestAnvisaOnlyMode:
    """Testes para modo ANVISA-only (redirecionamento para open_anvisa)."""

    def test_pending_card_click_anvisa_only_redirects_to_anvisa(self, fake_navigator):
        """Com anvisa_only=True, clique em Pendências deve chamar open_anvisa."""
        # Criar snapshot com anvisa_only=True
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=3,
            anvisa_only=True,
        )
        vm = DashboardViewModel(service=lambda org_id, today: snapshot)
        state = vm.load(org_id="test-org", today=None)

        controller = DashboardActionController(navigator=fake_navigator)

        # Clicar no card de pendências
        controller.handle_pending_card_click(state)

        # Deve ter chamado open_anvisa ao invés de go_to_pending
        assert fake_navigator.open_anvisa_called is True
        assert fake_navigator.pending_called is False
        assert fake_navigator.clients_called is False
        assert fake_navigator.tasks_called is False

    def test_tasks_today_card_click_anvisa_only_redirects_to_anvisa(self, fake_navigator):
        """Com anvisa_only=True, clique em Tarefas deve chamar open_anvisa."""
        # Criar snapshot com anvisa_only=True
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=3,
            anvisa_only=True,
        )
        vm = DashboardViewModel(service=lambda org_id, today: snapshot)
        state = vm.load(org_id="test-org", today=None)

        controller = DashboardActionController(navigator=fake_navigator)

        # Clicar no card de tarefas
        controller.handle_tasks_today_card_click(state)

        # Deve ter chamado open_anvisa ao invés de go_to_tasks_today
        assert fake_navigator.open_anvisa_called is True
        assert fake_navigator.tasks_called is False
        assert fake_navigator.clients_called is False
        assert fake_navigator.pending_called is False

    def test_pending_card_normal_mode_uses_go_to_pending(self, fake_navigator):
        """Com anvisa_only=False, clique em Pendências deve chamar go_to_pending."""
        # Criar snapshot com anvisa_only=False
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=3,
            anvisa_only=False,
        )
        vm = DashboardViewModel(service=lambda org_id, today: snapshot)
        state = vm.load(org_id="test-org", today=None)

        controller = DashboardActionController(navigator=fake_navigator)

        # Clicar no card de pendências
        controller.handle_pending_card_click(state)

        # Deve ter chamado go_to_pending (fluxo normal)
        assert fake_navigator.pending_called is True
        assert fake_navigator.open_anvisa_called is False

    def test_tasks_today_card_normal_mode_uses_go_to_tasks(self, fake_navigator):
        """Com anvisa_only=False, clique em Tarefas deve chamar go_to_tasks_today."""
        # Criar snapshot com anvisa_only=False
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=3,
            anvisa_only=False,
        )
        vm = DashboardViewModel(service=lambda org_id, today: snapshot)
        state = vm.load(org_id="test-org", today=None)

        controller = DashboardActionController(navigator=fake_navigator)

        # Clicar no card de tarefas
        controller.handle_tasks_today_card_click(state)

        # Deve ter chamado go_to_tasks_today (fluxo normal)
        assert fake_navigator.tasks_called is True
        assert fake_navigator.open_anvisa_called is False

    def test_tasks_today_card_anvisa_only_with_one_task_opens_history(self, fake_navigator):
        """Com anvisa_only=True e 1 tarefa, clique deve abrir histórico do cliente."""
        # Criar snapshot com anvisa_only=True, 1 tarefa
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=1,
            anvisa_only=True,
            pending_tasks=[
                {
                    "client_id": "123",
                    "client_name": "Cliente Teste",
                    "title": "AFE (Hoje)",
                    "priority": "high",
                }
            ],
        )
        vm = DashboardViewModel(service=lambda org_id, today: snapshot)
        state = vm.load(org_id="test-org", today=None)

        controller = DashboardActionController(navigator=fake_navigator)

        # Clicar no card de tarefas
        controller.handle_tasks_today_card_click(state)

        # Deve ter chamado open_anvisa_history com o client_id correto
        assert fake_navigator.open_anvisa_history_called is True
        assert fake_navigator.open_anvisa_history_client_id == "123"
        assert fake_navigator.open_anvisa_called is False
        assert fake_navigator.tasks_called is False

    def test_tasks_today_card_anvisa_only_with_multiple_tasks_opens_anvisa(self, fake_navigator):
        """Com anvisa_only=True e múltiplas tarefas de clientes diferentes, clique deve abrir picker."""
        # Criar snapshot com anvisa_only=True, múltiplas tarefas de clientes diferentes
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=3,
            anvisa_only=True,
            pending_tasks=[
                {"client_id": "123", "client_name": "Cliente 1", "title": "AFE"},
                {"client_id": "456", "client_name": "Cliente 2", "title": "AE"},
            ],
        )
        vm = DashboardViewModel(service=lambda org_id, today: snapshot)
        state = vm.load(org_id="test-org", today=None)

        controller = DashboardActionController(navigator=fake_navigator)

        # Clicar no card de tarefas
        controller.handle_tasks_today_card_click(state)

        # Deve ter chamado open_anvisa_history_picker (2 clientes)
        assert fake_navigator.open_anvisa_history_picker_called is True
        assert fake_navigator.open_anvisa_called is False
        assert fake_navigator.open_anvisa_history_called is False
        assert fake_navigator.tasks_called is False

    def test_tasks_today_card_anvisa_only_multiple_clients_opens_picker(self, fake_navigator):
        """Com anvisa_only=True e múltiplos clientes, clique deve abrir picker."""
        # Criar snapshot com anvisa_only=True, múltiplos clientes
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=3,
            anvisa_only=True,
            clients_of_the_day=[
                {"client_id": "123", "client_name": "Cliente 1", "obligation_kinds": ["AFE"]},
                {"client_id": "456", "client_name": "Cliente 2", "obligation_kinds": ["AE"]},
            ],
            pending_tasks=[
                {"client_id": "123", "client_name": "Cliente 1", "title": "AFE"},
                {"client_id": "456", "client_name": "Cliente 2", "title": "AE"},
            ],
        )
        vm = DashboardViewModel(service=lambda org_id, today: snapshot)
        state = vm.load(org_id="test-org", today=None)

        controller = DashboardActionController(navigator=fake_navigator)

        # Clicar no card de tarefas
        controller.handle_tasks_today_card_click(state)

        # Deve ter chamado open_anvisa_history_picker
        assert fake_navigator.open_anvisa_history_picker_called is True
        assert fake_navigator.open_anvisa_history_picker_items is not None
        assert len(fake_navigator.open_anvisa_history_picker_items) == 2
        assert fake_navigator.open_anvisa_called is False
        assert fake_navigator.open_anvisa_history_called is False
        assert fake_navigator.tasks_called is False

    def test_tasks_today_card_anvisa_only_same_client_multiple_tasks_opens_history(self, fake_navigator):
        """Com anvisa_only=True e várias tarefas do mesmo cliente, clique deve abrir histórico direto."""
        # Criar snapshot com anvisa_only=True, múltiplas tarefas mas 1 cliente
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=3,
            anvisa_only=True,
            clients_of_the_day=[
                {"client_id": "123", "client_name": "Cliente 1", "obligation_kinds": ["AFE", "AE"]},
            ],
            pending_tasks=[
                {"client_id": "123", "client_name": "Cliente 1", "title": "AFE"},
                {"client_id": "123", "client_name": "Cliente 1", "title": "AE"},
                {"client_id": "123", "client_name": "Cliente 1", "title": "CBPF"},
            ],
        )
        vm = DashboardViewModel(service=lambda org_id, today: snapshot)
        state = vm.load(org_id="test-org", today=None)

        controller = DashboardActionController(navigator=fake_navigator)

        # Clicar no card de tarefas
        controller.handle_tasks_today_card_click(state)

        # Deve ter chamado open_anvisa_history com o client_id correto
        assert fake_navigator.open_anvisa_history_called is True
        assert fake_navigator.open_anvisa_history_client_id == "123"
        assert fake_navigator.open_anvisa_history_picker_called is False
        assert fake_navigator.open_anvisa_called is False
        assert fake_navigator.tasks_called is False


# ============================================================================
# TESTES MF46: Cobertura de import fallback (linhas 22-25)
# ============================================================================


class TestGetLoggerFallback:
    """Testes para validar que o logger do módulo funciona corretamente."""

    def test_get_logger_returns_valid_logger(self):
        """get_logger deve retornar um logger válido com métodos padrão."""
        from src.modules.hub.controllers.dashboard_actions import get_logger

        test_logger = get_logger("test_module_mf46")
        assert test_logger is not None
        assert hasattr(test_logger, "debug")
        assert hasattr(test_logger, "info")
        assert hasattr(test_logger, "warning")
        assert hasattr(test_logger, "error")

    def test_module_logger_is_valid(self):
        """O logger do módulo deve ser válido e funcional."""
        from src.modules.hub.controllers.dashboard_actions import logger

        assert logger is not None
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "exception")


# ============================================================================
# TESTES MF47: Cobertura do except no import (linhas 22-25)
# ============================================================================


class TestGetLoggerImportFallback:
    """Testes para cobrir o except do import em linhas 22-25."""

    def test_dashboard_actions_get_logger_fallback_executes_on_import_error(self, monkeypatch):
        """get_logger deve usar logging.getLogger quando src.core.logger falha (linhas 22-25)."""
        import builtins
        import importlib
        import logging
        import sys

        target = "src.modules.hub.controllers.dashboard_actions"

        # Garantir reload limpo
        sys.modules.pop(target, None)

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "src.core.logger":
                raise ImportError("boom")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        mod = importlib.import_module(target)
        # Aqui o except deve ter sido executado e get_logger definido via logging.getLogger
        lg = mod.get_logger("test_mf47_fallback")
        assert isinstance(lg, logging.Logger)

        # Cleanup explícito
        sys.modules.pop(target, None)
