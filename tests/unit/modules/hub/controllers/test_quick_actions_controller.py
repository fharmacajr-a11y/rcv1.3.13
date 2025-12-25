# -*- coding: utf-8 -*-
"""Testes headless para QuickActionsController."""

from __future__ import annotations

import pytest

from src.modules.hub.controllers.quick_actions_controller import (
    QuickActionsController,
    HubQuickActionsNavigatorProtocol,
)


class FakeNavigator:
    """Fake navigator para testes (implementa HubQuickActionsNavigatorProtocol)."""

    def __init__(self):
        """Inicializa flags de navegação."""
        self.clientes_opened = False
        self.senhas_opened = False
        self.auditoria_opened = False
        self.fluxo_caixa_opened = False
        self.anvisa_opened = False
        self.sngpc_opened = False
        self.sites_opened = False  # MF-39: adicionar sites

    def open_clientes(self) -> None:
        """Marca que Clientes foi aberto."""
        self.clientes_opened = True

    def open_senhas(self) -> None:
        """Marca que Senhas foi aberto."""
        self.senhas_opened = True

    def open_auditoria(self) -> None:
        """Marca que Auditoria foi aberto."""
        self.auditoria_opened = True

    def open_fluxo_caixa(self) -> None:
        """Marca que Fluxo de Caixa foi aberto."""
        self.fluxo_caixa_opened = True

    def open_anvisa(self) -> None:
        """Marca que Anvisa foi aberto."""
        self.anvisa_opened = True

    def open_sngpc(self) -> None:
        """Marca que Sngpc foi aberto."""
        self.sngpc_opened = True

    def open_sites(self) -> None:
        """Marca que Sites foi aberto."""
        self.sites_opened = True  # MF-39: adicionar sites

    def reset(self):
        """Reseta todas as flags."""
        self.clientes_opened = False
        self.senhas_opened = False
        self.auditoria_opened = False
        self.fluxo_caixa_opened = False
        self.anvisa_opened = False
        self.sngpc_opened = False
        self.sites_opened = False  # MF-39: adicionar sites


@pytest.fixture
def fake_navigator():
    """Fake navigator para testes."""
    return FakeNavigator()


@pytest.fixture
def controller(fake_navigator):
    """Controller configurado com fake navigator."""
    return QuickActionsController(navigator=fake_navigator)


class TestQuickActionsController:
    """Testes para QuickActionsController."""

    def test_handle_clientes_click(self, controller, fake_navigator):
        """Deve chamar open_clientes ao clicar em 'clientes'."""
        controller.handle_action_click("clientes")

        assert fake_navigator.clientes_opened is True
        assert fake_navigator.senhas_opened is False
        assert fake_navigator.auditoria_opened is False

    def test_handle_senhas_click(self, controller, fake_navigator):
        """Deve chamar open_senhas ao clicar em 'senhas'."""
        controller.handle_action_click("senhas")

        assert fake_navigator.senhas_opened is True
        assert fake_navigator.clientes_opened is False

    def test_handle_auditoria_click(self, controller, fake_navigator):
        """Deve chamar open_auditoria ao clicar em 'auditoria'."""
        controller.handle_action_click("auditoria")

        assert fake_navigator.auditoria_opened is True
        assert fake_navigator.clientes_opened is False

    def test_handle_fluxo_caixa_click(self, controller, fake_navigator):
        """Deve chamar open_fluxo_caixa ao clicar em 'fluxo_caixa'."""
        controller.handle_action_click("fluxo_caixa")

        assert fake_navigator.fluxo_caixa_opened is True
        assert fake_navigator.auditoria_opened is False

    def test_handle_anvisa_click(self, controller, fake_navigator):
        """Deve chamar open_anvisa ao clicar em 'anvisa'."""
        controller.handle_action_click("anvisa")

        assert fake_navigator.anvisa_opened is True
        assert fake_navigator.sngpc_opened is False

    def test_handle_sngpc_click(self, controller, fake_navigator):
        """Deve chamar open_sngpc ao clicar em 'sngpc'."""
        controller.handle_action_click("sngpc")

        assert fake_navigator.sngpc_opened is True
        assert fake_navigator.anvisa_opened is False

    def test_handle_unknown_action(self, controller, fake_navigator):
        """Deve ignorar ação desconhecida sem crash."""
        # Não deve crashar
        controller.handle_action_click("unknown_action")

        # Nenhum método deve ter sido chamado
        assert fake_navigator.clientes_opened is False
        assert fake_navigator.senhas_opened is False
        assert fake_navigator.auditoria_opened is False
        assert fake_navigator.fluxo_caixa_opened is False
        assert fake_navigator.anvisa_opened is False
        assert fake_navigator.sngpc_opened is False

    def test_handle_multiple_clicks(self, controller, fake_navigator):
        """Deve permitir múltiplos cliques em sequência."""
        controller.handle_action_click("clientes")
        assert fake_navigator.clientes_opened is True

        fake_navigator.reset()

        controller.handle_action_click("anvisa")
        assert fake_navigator.anvisa_opened is True
        assert fake_navigator.clientes_opened is False

    def test_navigator_protocol_compliance(self, fake_navigator):
        """Fake navigator deve implementar HubQuickActionsNavigatorProtocol."""
        # Verifica que FakeNavigator é compatível com o Protocol
        assert isinstance(fake_navigator, HubQuickActionsNavigatorProtocol)
