# -*- coding: utf-8 -*-
"""Testes de integração para Quick Actions do Hub (MF-20).

Estratégia de testes:
- Nível A: QuickActionsController + Navigator (integração direta)
  - Valida que cada action/module chama o método correto do Navigator
  - Cobertura de todas as actions principais e casos especiais (alias, desconhecidas)

- Nível B: HubScreenController + QuickActionsController + Navigator (fluxo completo)
  - Valida que eventos de UI (on_quick_action_clicked, on_module_clicked) chegam até o Navigator
  - Garante que a integração entre os componentes funciona de ponta a ponta

Nota: HubScreen (view Tkinter) não é instanciado diretamente nestes testes para evitar
dependências de GUI. O foco está na integração dos controllers e lógica de negócio.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.modules.hub.controllers.quick_actions_controller import (
    QuickActionsController,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures e helpers
# ═══════════════════════════════════════════════════════════════════════


class FakeNavigator:
    """Implementação fake do HubQuickActionsNavigatorProtocol para testes.

    Registra todas as chamadas aos métodos de navegação para verificação.
    """

    def __init__(self):
        self.calls = []

    def open_clientes(self) -> None:
        self.calls.append("open_clientes")

    def open_senhas(self) -> None:
        self.calls.append("open_senhas")

    def open_auditoria(self) -> None:
        self.calls.append("open_auditoria")

    def open_fluxo_caixa(self) -> None:
        self.calls.append("open_fluxo_caixa")

    def open_anvisa(self) -> None:
        self.calls.append("open_anvisa")

    def open_sngpc(self) -> None:
        self.calls.append("open_sngpc")

    def open_sites(self) -> None:
        self.calls.append("open_sites")


@pytest.fixture
def fake_navigator():
    """Fixture que fornece um fake navigator para testes."""
    return FakeNavigator()


@pytest.fixture
def quick_actions_controller(fake_navigator):
    """Fixture que fornece um QuickActionsController com fake navigator."""
    return QuickActionsController(navigator=fake_navigator)


# ═══════════════════════════════════════════════════════════════════════
# Nível A: Testes de integração QuickActionsController + Navigator
# ═══════════════════════════════════════════════════════════════════════


def test_quick_actions_controller_chama_navigator_para_clientes(quick_actions_controller, fake_navigator):
    """Teste: handle_action_click('clientes') chama navigator.open_clientes()."""
    # Act
    result = quick_actions_controller.handle_action_click("clientes")

    # Assert
    assert result is True
    assert "open_clientes" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_chama_navigator_para_senhas(quick_actions_controller, fake_navigator):
    """Teste: handle_action_click('senhas') chama navigator.open_senhas()."""
    # Act
    result = quick_actions_controller.handle_action_click("senhas")

    # Assert
    assert result is True
    assert "open_senhas" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_chama_navigator_para_auditoria(quick_actions_controller, fake_navigator):
    """Teste: handle_action_click('auditoria') chama navigator.open_auditoria()."""
    # Act
    result = quick_actions_controller.handle_action_click("auditoria")

    # Assert
    assert result is True
    assert "open_auditoria" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_chama_navigator_para_fluxo_caixa(quick_actions_controller, fake_navigator):
    """Teste: handle_action_click('fluxo_caixa') chama navigator.open_fluxo_caixa()."""
    # Act
    result = quick_actions_controller.handle_action_click("fluxo_caixa")

    # Assert
    assert result is True
    assert "open_fluxo_caixa" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_alias_cashflow_chama_navigator_open_fluxo_caixa(
    quick_actions_controller, fake_navigator
):
    """Teste: handle_action_click('cashflow') (alias) chama navigator.open_fluxo_caixa()."""
    # Act
    result = quick_actions_controller.handle_action_click("cashflow")

    # Assert
    assert result is True
    assert "open_fluxo_caixa" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_chama_navigator_para_anvisa(quick_actions_controller, fake_navigator):
    """Teste: handle_action_click('anvisa') chama navigator.open_anvisa()."""
    # Act
    result = quick_actions_controller.handle_action_click("anvisa")

    # Assert
    assert result is True
    assert "open_anvisa" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_chama_navigator_para_sngpc(quick_actions_controller, fake_navigator):
    """Teste: handle_action_click('sngpc') chama navigator.open_sngpc()."""
    # Act
    result = quick_actions_controller.handle_action_click("sngpc")

    # Assert
    assert result is True
    assert "open_sngpc" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_chama_navigator_para_sites(quick_actions_controller, fake_navigator):
    """Teste: handle_action_click('sites') chama navigator.open_sites() (MF-17)."""
    # Act
    result = quick_actions_controller.handle_action_click("sites")

    # Assert
    assert result is True
    assert "open_sites" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_action_desconhecida_retorna_false_sem_chamar_navigator(
    quick_actions_controller, fake_navigator
):
    """Teste: Action desconhecida retorna False e não chama navigator."""
    # Act
    result = quick_actions_controller.handle_action_click("modulo_inexistente")

    # Assert
    assert result is False
    assert len(fake_navigator.calls) == 0


def test_quick_actions_controller_handle_module_click_delega_para_handle_action_click(
    quick_actions_controller, fake_navigator
):
    """Teste: handle_module_click delega para handle_action_click (MF-18)."""
    # Act
    result = quick_actions_controller.handle_module_click("clientes")

    # Assert
    assert result is True
    assert "open_clientes" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_handle_module_click_normaliza_lowercase(quick_actions_controller, fake_navigator):
    """Teste: handle_module_click normaliza para lowercase antes de delegar."""
    # Act
    result = quick_actions_controller.handle_module_click("SENHAS")

    # Assert
    assert result is True
    assert "open_senhas" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_quick_actions_controller_handle_module_click_module_vazio_retorna_false(
    quick_actions_controller, fake_navigator
):
    """Teste: handle_module_click com module_id vazio retorna False."""
    # Act
    result = quick_actions_controller.handle_module_click("")

    # Assert
    assert result is False
    assert len(fake_navigator.calls) == 0


def test_quick_actions_controller_handle_module_click_module_none_retorna_false(
    quick_actions_controller, fake_navigator
):
    """Teste: handle_module_click com module_id None retorna False."""
    # Act
    result = quick_actions_controller.handle_module_click(None)

    # Assert
    assert result is False
    assert len(fake_navigator.calls) == 0


def test_quick_actions_controller_multiplas_actions_sequenciais(quick_actions_controller, fake_navigator):
    """Teste: Múltiplas actions em sequência chamam navigator corretamente."""
    # Act
    quick_actions_controller.handle_action_click("clientes")
    quick_actions_controller.handle_action_click("senhas")
    quick_actions_controller.handle_action_click("auditoria")

    # Assert
    assert len(fake_navigator.calls) == 3
    assert fake_navigator.calls == ["open_clientes", "open_senhas", "open_auditoria"]


def test_quick_actions_controller_todas_actions_principais_funcionam(quick_actions_controller, fake_navigator):
    """Teste: Todas as actions principais navegam corretamente."""
    # BUGFIX-HUB-UI-001: Removidos farmacia_popular e sifap
    actions = [
        ("clientes", "open_clientes"),
        ("senhas", "open_senhas"),
        ("auditoria", "open_auditoria"),
        ("fluxo_caixa", "open_fluxo_caixa"),
        ("cashflow", "open_fluxo_caixa"),  # alias
        ("anvisa", "open_anvisa"),
        ("sngpc", "open_sngpc"),
        ("sites", "open_sites"),
    ]

    # Act & Assert
    for action_id, expected_call in actions:
        # Reset calls
        fake_navigator.calls.clear()

        # Execute action
        result = quick_actions_controller.handle_action_click(action_id)

        # Verify
        assert result is True, f"Action '{action_id}' deveria retornar True"
        assert expected_call in fake_navigator.calls, f"Action '{action_id}' deveria chamar {expected_call}"
        assert len(fake_navigator.calls) == 1, f"Action '{action_id}' deveria chamar apenas um método"


# ═══════════════════════════════════════════════════════════════════════
# Nível B: Testes de integração com HubScreenController
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def fake_state():
    """Fixture de HubState mockado."""
    state = MagicMock()
    state.org_id = "org123"
    state.user_id = "user456"
    state.is_active = True
    return state


@pytest.fixture
def fake_view():
    """Fixture de View mockada."""
    view = MagicMock()
    return view


@pytest.fixture
def fake_async_runner():
    """Fixture de AsyncRunner mockado."""
    return MagicMock()


@pytest.fixture
def fake_lifecycle():
    """Fixture de Lifecycle mockado."""
    return MagicMock()


@pytest.fixture
def hub_screen_controller_with_integration(fake_state, fake_view, fake_async_runner, fake_lifecycle, fake_navigator):
    """Fixture com HubScreenController integrado com QuickActionsController real e fake navigator."""
    from src.modules.hub.hub_screen_controller import HubScreenController

    # Criar QuickActionsController com fake navigator
    quick_actions_controller = QuickActionsController(navigator=fake_navigator)

    # Criar ViewModels mockados
    dashboard_vm = MagicMock()
    notes_vm = MagicMock()
    quick_actions_vm = MagicMock()

    # Criar HubScreenController com QuickActionsController real
    controller = HubScreenController(
        state=fake_state,
        dashboard_vm=dashboard_vm,
        notes_vm=notes_vm,
        quick_actions_vm=quick_actions_vm,
        async_runner=fake_async_runner,
        lifecycle=fake_lifecycle,
        view=fake_view,
        quick_actions_controller=quick_actions_controller,
    )

    return controller


def test_hub_controller_quick_action_clientes_fluxo_completo_chama_navigator(
    hub_screen_controller_with_integration, fake_navigator
):
    """Teste: on_quick_action_clicked('clientes') chega até navigator.open_clientes()."""
    # Act
    hub_screen_controller_with_integration.on_quick_action_clicked("clientes")

    # Assert
    assert "open_clientes" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_hub_controller_module_clientes_fluxo_completo_chama_navigator(
    hub_screen_controller_with_integration, fake_navigator
):
    """Teste: on_module_clicked('clientes') chega até navigator.open_clientes()."""
    # Act
    hub_screen_controller_with_integration.on_module_clicked("clientes")

    # Assert
    assert "open_clientes" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_hub_controller_quick_action_e_module_mesma_action_usam_mesmo_caminho(
    hub_screen_controller_with_integration, fake_navigator
):
    """Teste: Quick action e module com mesmo ID chegam ao mesmo método do navigator."""
    # Act - quick action
    hub_screen_controller_with_integration.on_quick_action_clicked("senhas")
    primeira_chamada = fake_navigator.calls[0]

    # Reset
    fake_navigator.calls.clear()

    # Act - module
    hub_screen_controller_with_integration.on_module_clicked("senhas")
    segunda_chamada = fake_navigator.calls[0]

    # Assert
    assert primeira_chamada == segunda_chamada == "open_senhas"


def test_hub_controller_quick_action_sites_fluxo_completo(hub_screen_controller_with_integration, fake_navigator):
    """Teste: Quick action 'sites' (MF-17) chega até navigator.open_sites()."""
    # Act
    hub_screen_controller_with_integration.on_quick_action_clicked("sites")

    # Assert
    assert "open_sites" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_hub_controller_module_sites_fluxo_completo(hub_screen_controller_with_integration, fake_navigator):
    """Teste: Module click 'sites' (MF-17) chega até navigator.open_sites()."""
    # Act
    hub_screen_controller_with_integration.on_module_clicked("sites")

    # Assert
    assert "open_sites" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_hub_controller_quick_action_case_insensitive_chega_ao_navigator(
    hub_screen_controller_with_integration, fake_navigator
):
    """Teste: Quick action com uppercase é normalizada e chega ao navigator."""
    # Act
    hub_screen_controller_with_integration.on_quick_action_clicked("AUDITORIA")

    # Assert
    assert "open_auditoria" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_hub_controller_module_case_insensitive_chega_ao_navigator(
    hub_screen_controller_with_integration, fake_navigator
):
    """Teste: Module com uppercase é normalizado e chega ao navigator."""
    # Act
    hub_screen_controller_with_integration.on_module_clicked("ANVISA")

    # Assert
    assert "open_anvisa" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_hub_controller_alias_cashflow_fluxo_completo(hub_screen_controller_with_integration, fake_navigator):
    """Teste: Alias 'cashflow' via quick action chega a navigator.open_fluxo_caixa()."""
    # Act
    hub_screen_controller_with_integration.on_quick_action_clicked("cashflow")

    # Assert
    assert "open_fluxo_caixa" in fake_navigator.calls
    assert len(fake_navigator.calls) == 1


def test_hub_controller_todas_quick_actions_chegam_ao_navigator(hub_screen_controller_with_integration, fake_navigator):
    """Teste: Todas as quick actions principais chegam ao navigator corretamente."""
    # BUGFIX-HUB-UI-001: Removidos farmacia_popular e sifap
    actions = [
        ("clientes", "open_clientes"),
        ("senhas", "open_senhas"),
        ("auditoria", "open_auditoria"),
        ("fluxo_caixa", "open_fluxo_caixa"),
        ("anvisa", "open_anvisa"),
        ("sngpc", "open_sngpc"),
        ("sites", "open_sites"),
    ]

    for action_id, expected_call in actions:
        # Reset
        fake_navigator.calls.clear()

        # Act
        hub_screen_controller_with_integration.on_quick_action_clicked(action_id)

        # Assert
        assert expected_call in fake_navigator.calls, f"Quick action '{action_id}' deveria chamar {expected_call}"
        assert len(fake_navigator.calls) == 1


def test_hub_controller_todos_modules_chegam_ao_navigator(hub_screen_controller_with_integration, fake_navigator):
    """Teste: Todos os modules principais chegam ao navigator corretamente."""
    # BUGFIX-HUB-UI-001: Removidos farmacia_popular e sifap
    modules = [
        ("clientes", "open_clientes"),
        ("senhas", "open_senhas"),
        ("auditoria", "open_auditoria"),
        ("cashflow", "open_fluxo_caixa"),  # alias via module
        ("anvisa", "open_anvisa"),
        ("sngpc", "open_sngpc"),
        ("sites", "open_sites"),
    ]

    for module_id, expected_call in modules:
        # Reset
        fake_navigator.calls.clear()

        # Act
        hub_screen_controller_with_integration.on_module_clicked(module_id)

        # Assert
        assert expected_call in fake_navigator.calls, f"Module '{module_id}' deveria chamar {expected_call}"
        assert len(fake_navigator.calls) == 1
