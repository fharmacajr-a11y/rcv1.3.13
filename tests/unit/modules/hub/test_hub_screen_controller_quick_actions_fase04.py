# -*- coding: utf-8 -*-
"""Testes unitários para Quick Actions no HubScreenController (MF-17).

Cobertura:
- on_quick_action_clicked() - integração com QuickActionsController
- Validação de actions conhecidas e desconhecidas
- Error handling
- Case-insensitive e aliases
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest


# Fixtures locais (reutilizando padrão MF-15B/C)


@pytest.fixture
def fake_state():
    """Fixture de HubState para testes."""
    state = MagicMock()
    state.org_id = "org123"
    state.user_id = "user456"
    state.is_active = True
    state.cached_notes = []
    state.cached_authors = {}
    state.notes_last_refresh_ts = None
    state.is_notes_loaded = False
    state.is_dashboard_loaded = False

    return state


@pytest.fixture
def fake_dashboard_vm():
    """Fixture de DashboardViewModel mockado."""
    vm = MagicMock()
    vm.load = Mock(
        return_value=MagicMock(
            snapshot={"active_clients": 10},
            cards=[],
            error_message=None,
        )
    )
    vm.from_error = Mock(
        return_value=MagicMock(
            snapshot=None,
            cards=[],
            error_message="Erro de teste",
        )
    )
    return vm


@pytest.fixture
def fake_notes_vm():
    """Fixture de NotesViewModel mockado."""
    vm = MagicMock()
    vm.load = Mock(
        return_value=MagicMock(
            notes=[
                {"id": "n1", "body": "Nota 1"},
                {"id": "n2", "body": "Nota 2"},
            ],
        )
    )
    return vm


@pytest.fixture
def fake_quick_actions_vm():
    """Fixture de QuickActionsViewModel mockado."""
    vm = MagicMock()
    return vm


@pytest.fixture
def fake_view():
    """Fixture de View mockada (duck typing)."""
    view = MagicMock()
    view._get_org_id_safe = Mock(return_value="org123")
    view.update_dashboard = Mock()
    view.render_notes = Mock()
    view.update_notes_ui_state = Mock()
    return view


@pytest.fixture
def fake_async_runner():
    """Fixture de HubAsyncRunner mockado."""
    runner = MagicMock()

    def run_sync(func, on_success=None, on_error=None):
        """Executa função síncrona e chama callback."""
        try:
            result = func()
            if on_success:
                on_success(result)
        except Exception as exc:
            if on_error:
                on_error(exc)

    runner.run = Mock(side_effect=run_sync)
    return runner


@pytest.fixture
def fake_lifecycle():
    """Fixture de HubLifecycle mockado."""
    lifecycle = MagicMock()
    lifecycle.start = Mock()
    lifecycle.stop = Mock()
    return lifecycle


@pytest.fixture
def mock_quick_actions_controller():
    """Fixture de QuickActionsController mockado (MF-17)."""
    controller = MagicMock()
    # Por padrão, retorna True (action reconhecida)
    controller.handle_action_click = Mock(return_value=True)
    return controller


@pytest.fixture
def controller_with_mocks(
    fake_state,
    fake_dashboard_vm,
    fake_notes_vm,
    fake_quick_actions_vm,
    fake_view,
    fake_async_runner,
    fake_lifecycle,
    mock_quick_actions_controller,
):
    """Fixture com HubScreenController configurado com mocks."""
    from src.modules.hub.hub_screen_controller import HubScreenController

    controller = HubScreenController(
        state=fake_state,
        dashboard_vm=fake_dashboard_vm,
        notes_vm=fake_notes_vm,
        quick_actions_vm=fake_quick_actions_vm,
        async_runner=fake_async_runner,
        lifecycle=fake_lifecycle,
        view=fake_view,
        quick_actions_controller=mock_quick_actions_controller,
    )

    return controller


# ═══════════════════════════════════════════════════════════════════════
# Testes de on_quick_action_clicked - Integração com QuickActionsController
# ═══════════════════════════════════════════════════════════════════════


def test_quick_action_clientes_delega_para_controller(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Quick action 'clientes' delega para QuickActionsController."""
    controller = controller_with_mocks

    # Act
    controller.on_quick_action_clicked("clientes")

    # Assert
    mock_quick_actions_controller.handle_action_click.assert_called_once_with("clientes")


def test_quick_action_case_insensitive_normaliza_para_lowercase(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Quick actions normalizam para lowercase antes de delegar."""
    controller = controller_with_mocks

    # Act
    controller.on_quick_action_clicked("CLIENTES")

    # Assert - deve normalizar para lowercase
    mock_quick_actions_controller.handle_action_click.assert_called_once_with("clientes")


def test_quick_action_multiplas_chamadas_independentes(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Múltiplas quick actions delegam corretamente."""
    controller = controller_with_mocks

    # Act
    controller.on_quick_action_clicked("clientes")
    controller.on_quick_action_clicked("senhas")
    controller.on_quick_action_clicked("auditoria")

    # Assert
    assert mock_quick_actions_controller.handle_action_click.call_count == 3
    calls = [call[0][0] for call in mock_quick_actions_controller.handle_action_click.call_args_list]
    assert calls == ["clientes", "senhas", "auditoria"]


def test_quick_action_mesma_acao_multiplas_vezes(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Mesma quick action pode ser chamada múltiplas vezes."""
    controller = controller_with_mocks

    # Act
    controller.on_quick_action_clicked("clientes")
    controller.on_quick_action_clicked("clientes")
    controller.on_quick_action_clicked("clientes")

    # Assert
    assert mock_quick_actions_controller.handle_action_click.call_count == 3


def test_quick_action_desconhecida_trata_retorno_false(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Quick action desconhecida (retorno False) é tratada sem exceção."""
    controller = controller_with_mocks

    # Arrange - QuickActionsController retorna False (action não reconhecida)
    mock_quick_actions_controller.handle_action_click.return_value = False

    # Act - não deve lançar exceção
    controller.on_quick_action_clicked("modulo_inexistente")

    # Assert - foi delegado ao controller
    mock_quick_actions_controller.handle_action_click.assert_called_once_with("modulo_inexistente")


def test_quick_action_com_excecao_no_controller_nao_quebra(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Exceção no QuickActionsController não quebra o HubScreenController."""
    controller = controller_with_mocks

    # Arrange - fazer controller lançar exceção
    mock_quick_actions_controller.handle_action_click.side_effect = RuntimeError("Erro de teste")

    # Act - não deve propagar exceção
    controller.on_quick_action_clicked("senhas")

    # Assert - foi chamado (e falhou internamente, mas não propagou)
    mock_quick_actions_controller.handle_action_click.assert_called_once_with("senhas")


def test_quick_action_com_action_id_vazio_nao_quebra(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Action ID vazio ou None não quebra."""
    controller = controller_with_mocks

    # Act - não deve lançar exceção
    controller.on_quick_action_clicked("")
    controller.on_quick_action_clicked(None)

    # Assert - delegou ao controller (que pode tratar como quiser)
    assert mock_quick_actions_controller.handle_action_click.call_count == 2


def test_quick_action_alias_cashflow_normalizado(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Alias 'cashflow' é normalizado e delegado."""
    controller = controller_with_mocks

    # Act
    controller.on_quick_action_clicked("CASHFLOW")

    # Assert - deve normalizar para lowercase
    mock_quick_actions_controller.handle_action_click.assert_called_once_with("cashflow")


def test_quick_action_todas_actions_suportadas(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Todas as actions conhecidas são delegadas corretamente."""
    controller = controller_with_mocks

    # Act - testar todas as actions conhecidas
    actions = [
        "clientes",
        "senhas",
        "auditoria",
        "fluxo_caixa",
        "cashflow",
        "anvisa",
        "farmacia_popular",
        "sngpc",
        "sifap",
        "sites",
    ]

    for action in actions:
        controller.on_quick_action_clicked(action)

    # Assert - todas foram delegadas
    assert mock_quick_actions_controller.handle_action_click.call_count == len(actions)
