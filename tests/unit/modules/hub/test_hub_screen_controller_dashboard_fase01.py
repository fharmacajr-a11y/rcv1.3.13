# -*- coding: utf-8 -*-
"""Testes unitários para HubScreenController - Foco em Dashboard (MF-15-B).

Valida:
- Carregamento de dados de dashboard via ViewModel
- Atualização de UI via View
- Handlers de eventos de cards do dashboard
- Cooldown de refresh de dashboard
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.hub.hub_screen_controller import HubScreenController
from src.modules.hub.state import HubState


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def fake_state():
    """HubState com dados mínimos para testes de dashboard."""
    state = HubState()
    state.org_id = "test-org-123"
    state.user_id = "test-user-456"
    state.user_email = "test@example.com"
    state.user_role = "admin"
    state.is_active = True
    return state


@pytest.fixture
def fake_dashboard_vm():
    """Mock de DashboardViewModel com load() async.

    MF-29: Usa AsyncMock para load() para simular coroutine awaitable corretamente.
    """
    vm = MagicMock()

    # Simular DashboardViewState de sucesso
    fake_state = MagicMock()
    fake_state.snapshot = {"clients_count": 10, "pending_count": 5}
    fake_state.error_message = None

    # MF-29: load() deve retornar coroutine awaitable (AsyncMock)
    vm.load = AsyncMock(return_value=fake_state)
    vm.from_error = MagicMock(return_value=MagicMock(error_message="Erro simulado", snapshot=None))

    return vm


@pytest.fixture
def fake_notes_vm():
    """Mock de NotesViewModel (não usado em testes de dashboard)."""
    return MagicMock()


@pytest.fixture
def fake_quick_actions_vm():
    """Mock de QuickActionsViewModel."""
    return MagicMock()


@pytest.fixture
def fake_view():
    """Mock de HubScreenView com métodos de atualização de UI."""
    view = MagicMock()
    view.update_dashboard = MagicMock()
    view.show_loading = MagicMock()
    view.hide_loading = MagicMock()
    view.update_notes_ui_state = MagicMock()
    return view


@pytest.fixture
def fake_async_runner():
    """Mock de HubAsyncRunner que executa callbacks síncronamente para testes."""
    runner = MagicMock()

    def run_sync(func, on_success=None, on_error=None):
        """Executa func (coroutine) síncronamente e chama callback apropriado."""
        try:
            # Executar coroutine com asyncio.run
            coro = func()
            result = asyncio.run(coro)
            if on_success:
                on_success(result)
        except Exception as exc:
            if on_error:
                on_error(exc)

    runner.run = MagicMock(side_effect=run_sync)
    return runner


@pytest.fixture
def fake_lifecycle():
    """Mock de HubLifecycle."""
    lifecycle = MagicMock()
    lifecycle.start = MagicMock()
    lifecycle.stop = MagicMock()
    lifecycle.schedule_dashboard_load = MagicMock()
    return lifecycle


@pytest.fixture
def fake_quick_actions_controller():
    """Fake QuickActionsController para testes (MF-39)."""
    controller = MagicMock()
    controller.handle_action_click = MagicMock()
    return controller


@pytest.fixture
def controller_with_mocks(
    fake_state,
    fake_dashboard_vm,
    fake_notes_vm,
    fake_quick_actions_vm,
    fake_async_runner,
    fake_lifecycle,
    fake_view,
    fake_quick_actions_controller,
):
    """Controller completo com todos os mocks configurados."""
    controller = HubScreenController(
        state=fake_state,
        dashboard_vm=fake_dashboard_vm,
        notes_vm=fake_notes_vm,
        quick_actions_vm=fake_quick_actions_vm,
        async_runner=fake_async_runner,
        lifecycle=fake_lifecycle,
        view=fake_view,
        quick_actions_controller=fake_quick_actions_controller,
        logger=logging.getLogger("test"),
    )
    return controller


# ═══════════════════════════════════════════════════════════════════════
# TESTES: Lifecycle
# ═══════════════════════════════════════════════════════════════════════


def test_controller_start_marks_state_active(controller_with_mocks):
    """start() marca state.is_active=True e delega para lifecycle."""
    controller = controller_with_mocks
    controller.state.is_active = False

    controller.start()

    assert controller.state.is_active is True
    controller.lifecycle.start.assert_called_once()


def test_controller_stop_marks_state_inactive(controller_with_mocks):
    """stop() marca state.is_active=False e delega para lifecycle."""
    controller = controller_with_mocks
    controller.state.is_active = True

    controller.stop()

    assert controller.state.is_active is False
    controller.lifecycle.stop.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════
# TESTES: Dashboard - Carregamento de Dados
# ═══════════════════════════════════════════════════════════════════════


def test_load_dashboard_data_async_happy_path(controller_with_mocks, fake_dashboard_vm):
    """load_dashboard_data_async carrega dados e atualiza View."""
    controller = controller_with_mocks

    # Executar carregamento
    controller.load_dashboard_data_async()

    # Verificar que async_runner.run foi chamado
    controller.async_runner.run.assert_called_once()

    # Verificar que view.update_dashboard foi chamado com estado
    controller.view.update_dashboard.assert_called_once()

    # Verificar que state.is_dashboard_loaded foi marcado
    assert controller.state.is_dashboard_loaded is True


def test_load_dashboard_data_async_sem_org_id(controller_with_mocks):
    """load_dashboard_data_async não carrega se org_id ausente."""
    controller = controller_with_mocks
    controller.state.org_id = None

    # View mock também retorna None para _get_org_id_safe (duck typing)
    controller.view._get_org_id_safe = MagicMock(return_value=None)

    controller.load_dashboard_data_async()

    # Não deve chamar async_runner
    controller.async_runner.run.assert_not_called()

    # Não deve atualizar view
    controller.view.update_dashboard.assert_not_called()


def test_load_dashboard_data_async_error_handling(controller_with_mocks, fake_dashboard_vm):
    """load_dashboard_data_async trata erros e exibe estado de erro."""
    controller = controller_with_mocks

    # Simular erro no ViewModel
    async def fake_load_error(org_id: str, today: Any) -> Any:
        raise ValueError("Erro simulado de teste")

    fake_dashboard_vm.load = MagicMock(return_value=fake_load_error("", None))

    # Executar carregamento
    controller.load_dashboard_data_async()

    # Verificar que view.update_dashboard foi chamado com error_state
    controller.view.update_dashboard.assert_called_once()

    # Verificar que from_error foi chamado
    fake_dashboard_vm.from_error.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════
# TESTES: Dashboard - Refresh com Cooldown
# ═══════════════════════════════════════════════════════════════════════


def test_refresh_dashboard_when_active(controller_with_mocks):
    """refresh_dashboard executa quando state.is_active=True."""
    controller = controller_with_mocks
    controller.state.is_active = True

    controller.refresh_dashboard()

    # Deve chamar load_dashboard_data_async
    controller.async_runner.run.assert_called_once()


def test_refresh_dashboard_when_inactive(controller_with_mocks):
    """refresh_dashboard ignora quando state.is_active=False."""
    controller = controller_with_mocks
    controller.state.is_active = False

    controller.refresh_dashboard()

    # Não deve carregar dados
    controller.async_runner.run.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# TESTES: Dashboard - Event Handlers de Cards
# ═══════════════════════════════════════════════════════════════════════


def test_on_card_clicked_clients(controller_with_mocks):
    """on_card_clicked('clients') delega para on_card_clients_click."""
    controller = controller_with_mocks

    with patch.object(controller, "on_card_clients_click") as mock_handler:
        controller.on_card_clicked("clients")
        mock_handler.assert_called_once()


def test_on_card_clicked_pending(controller_with_mocks):
    """on_card_clicked('pending') delega para on_card_pendencias_click."""
    controller = controller_with_mocks

    with patch.object(controller, "on_card_pendencias_click") as mock_handler:
        controller.on_card_clicked("pending")
        mock_handler.assert_called_once()


def test_on_card_clicked_tasks(controller_with_mocks):
    """on_card_clicked('tasks') delega para on_card_tarefas_click."""
    controller = controller_with_mocks

    with patch.object(controller, "on_card_tarefas_click") as mock_handler:
        controller.on_card_clicked("tasks")
        mock_handler.assert_called_once()


def test_on_card_clicked_unknown_type(controller_with_mocks):
    """on_card_clicked com tipo desconhecido apenas loga warning."""
    controller = controller_with_mocks

    # Não deve lançar exceção
    controller.on_card_clicked("unknown_card_type")


# ═══════════════════════════════════════════════════════════════════════
# TESTES: Dashboard - Navegação de Módulos
# ═══════════════════════════════════════════════════════════════════════


def test_on_module_clicked_clientes(controller_with_mocks, fake_quick_actions_controller):
    """on_module_clicked('clientes') delega para QuickActionsController."""
    controller = controller_with_mocks

    controller.on_module_clicked("clientes")

    # MF-40: Verificar que delegou para QuickActionsController (MF-18/MF-19)
    fake_quick_actions_controller.handle_module_click.assert_called_once_with("clientes")


def test_on_module_clicked_auditoria(controller_with_mocks, fake_quick_actions_controller):
    """on_module_clicked('auditoria') delega para QuickActionsController."""
    controller = controller_with_mocks

    controller.on_module_clicked("auditoria")

    # MF-40: Verificar que delegou para QuickActionsController (MF-18/MF-19)
    fake_quick_actions_controller.handle_module_click.assert_called_once_with("auditoria")


def test_on_module_clicked_unknown_module(controller_with_mocks, fake_quick_actions_controller):
    """on_module_clicked com módulo desconhecido apenas loga."""
    controller = controller_with_mocks

    # Não deve lançar exceção
    controller.on_module_clicked("modulo_inexistente")

    # MF-40: QuickActionsController deve ter sido chamado
    fake_quick_actions_controller.handle_module_click.assert_called_once_with("modulo_inexistente")


# ═══════════════════════════════════════════════════════════════════════
# TESTES: Dashboard - State Synchronization
# ═══════════════════════════════════════════════════════════════════════

# MF-40: Testes de _update_dashboard_ui_from_state removidos.
# Esse método foi movido para hub_async_tasks_service (MF-31) e é testado lá.
# O controller apenas delega, testamos a delegação nos testes de load_dashboard_data_async.
