# -*- coding: utf-8 -*-
"""Testes unitários para Module Clicks no HubScreenController (MF-18/MF-19).

Cobertura:
- on_module_clicked() - integração com QuickActionsController.handle_module_click
- Validação de módulos conhecidos e desconhecidos
- Error handling
- Case-insensitive
- MF-19: Sem fallback - toda navegação 100% centralizada no QuickActionsController
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest


# Fixtures locais (reutilizando padrão MF-17)


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
    """Fixture de QuickActionsController mockado (MF-18)."""
    controller = MagicMock()
    # Por padrão, retorna True (módulo reconhecido)
    controller.handle_module_click = Mock(return_value=True)
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
# Testes de on_module_clicked - Integração com QuickActionsController
# ═══════════════════════════════════════════════════════════════════════


def test_module_clientes_delega_para_quick_actions_controller(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Module click 'clientes' delega para QuickActionsController."""
    controller = controller_with_mocks

    # Act
    controller.on_module_clicked("clientes")

    # Assert
    mock_quick_actions_controller.handle_module_click.assert_called_once_with("clientes")


def test_module_case_insensitive_normaliza_para_lowercase(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Module clicks normalizam para lowercase antes de delegar."""
    controller = controller_with_mocks

    # Act
    controller.on_module_clicked("CLIENTES")

    # Assert - deve normalizar para lowercase
    mock_quick_actions_controller.handle_module_click.assert_called_once_with("clientes")


def test_module_multiplos_clicks_independentes(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Múltiplos module clicks delegam corretamente."""
    controller = controller_with_mocks

    # Act
    controller.on_module_clicked("clientes")
    controller.on_module_clicked("senhas")
    controller.on_module_clicked("auditoria")

    # Assert
    assert mock_quick_actions_controller.handle_module_click.call_count == 3
    calls = [call[0][0] for call in mock_quick_actions_controller.handle_module_click.call_args_list]
    assert calls == ["clientes", "senhas", "auditoria"]


def test_module_mesmo_modulo_multiplas_vezes(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Mesmo módulo pode ser clicado múltiplas vezes."""
    controller = controller_with_mocks

    # Act
    controller.on_module_clicked("clientes")
    controller.on_module_clicked("clientes")
    controller.on_module_clicked("clientes")

    # Assert
    assert mock_quick_actions_controller.handle_module_click.call_count == 3


def test_module_desconhecido_trata_retorno_false(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Módulo desconhecido (retorno False) é tratado sem exceção."""
    controller = controller_with_mocks

    # Arrange - QuickActionsController retorna False (módulo não reconhecido)
    mock_quick_actions_controller.handle_module_click.return_value = False

    # Act - não deve lançar exceção
    controller.on_module_clicked("modulo_inexistente")

    # Assert - foi delegado ao controller
    mock_quick_actions_controller.handle_module_click.assert_called_once_with("modulo_inexistente")


def test_module_com_excecao_no_controller_nao_quebra(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Exceção no QuickActionsController não quebra o HubScreenController."""
    controller = controller_with_mocks

    # Arrange - fazer controller lançar exceção
    mock_quick_actions_controller.handle_module_click.side_effect = RuntimeError("Erro de teste")

    # Act - não deve propagar exceção
    controller.on_module_clicked("senhas")

    # Assert - foi chamado (e falhou internamente, mas não propagou)
    mock_quick_actions_controller.handle_module_click.assert_called_once_with("senhas")


def test_module_com_module_id_vazio_nao_quebra(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Module ID vazio não quebra."""
    controller = controller_with_mocks

    # Act - não deve lançar exceção nem chamar o controller
    controller.on_module_clicked("")

    # Assert - não deve ter delegado ao controller (validação antecipada)
    mock_quick_actions_controller.handle_module_click.assert_not_called()


def test_module_com_module_id_none_nao_quebra(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Module ID None não quebra."""
    controller = controller_with_mocks

    # Act - não deve lançar exceção nem chamar o controller
    controller.on_module_clicked(None)

    # Assert - não deve ter delegado ao controller (validação antecipada)
    mock_quick_actions_controller.handle_module_click.assert_not_called()


def test_module_todos_modulos_suportados(controller_with_mocks, mock_quick_actions_controller):
    """Teste: Todos os módulos conhecidos são delegados corretamente."""
    controller = controller_with_mocks

    # Act - testar todos os módulos conhecidos
    modules = ["clientes", "senhas", "auditoria", "cashflow", "anvisa", "farmacia_popular", "sngpc", "sifap", "sites"]

    for module in modules:
        controller.on_module_clicked(module)

    # Assert - todos foram delegados
    assert mock_quick_actions_controller.handle_module_click.call_count == len(modules)
