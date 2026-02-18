# -*- coding: utf-8 -*-
"""MF-61: Testes headless para hub_navigation.py.

Testa helper de navegação do HUB com mocks, sem Tk real.
Meta: 100% coverage (statements + branches).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

# Module under test
import src.modules.hub.views.hub_navigation as hub_nav


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def dummy_hub() -> SimpleNamespace:
    """Hub dummy para simular HubScreen."""
    return SimpleNamespace()


@pytest.fixture
def helper(dummy_hub: SimpleNamespace) -> hub_nav.HubNavigationHelper:
    """Helper de navegação com hub dummy."""
    return hub_nav.HubNavigationHelper(cast(Any, dummy_hub))


# =============================================================================
# TEST: HubNavigatorProtocol - Navegação principal
# =============================================================================


class TestGoToMethods:
    """Testes para métodos go_to_* (navegação principal)."""

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_go_to_clients_with_callback(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """go_to_clients chama open_clientes quando definido."""
        dummy_hub.open_clientes = MagicMock()
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper.go_to_clients()

        dummy_hub.open_clientes.assert_called_once()
        mock_logger.debug.assert_not_called()

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_go_to_clients_without_callback(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """go_to_clients loga quando open_clientes não definido."""
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper.go_to_clients()

        mock_logger.debug.assert_called_once()
        assert "open_clientes não definido" in mock_logger.debug.call_args[0][0]

    @pytest.mark.skip(reason="Ação 'auditoria' removida – migração CTK")
    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_go_to_pending_with_callback(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """go_to_pending chama open_auditoria quando definido."""
        dummy_hub.open_auditoria = MagicMock()
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper.go_to_pending()

        dummy_hub.open_auditoria.assert_called_once()
        mock_logger.debug.assert_not_called()

    @pytest.mark.skip(reason="Ação 'auditoria' removida – migração CTK")
    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_go_to_pending_without_callback(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """go_to_pending loga quando open_auditoria não definido."""
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper.go_to_pending()

        mock_logger.debug.assert_called_once()
        assert "open_auditoria não definido" in mock_logger.debug.call_args[0][0]

    def test_go_to_tasks_today_with_callback(self, dummy_hub: SimpleNamespace) -> None:
        """go_to_tasks_today chama _on_new_task quando definido."""
        dummy_hub._on_new_task = MagicMock()
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper.go_to_tasks_today()

        dummy_hub._on_new_task.assert_called_once()

    def test_go_to_tasks_today_without_callback(self, dummy_hub: SimpleNamespace) -> None:
        """go_to_tasks_today não explode quando _on_new_task não definido."""
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        # Não deve explodir
        helper.go_to_tasks_today()


# =============================================================================
# TEST: HubQuickActionsNavigatorProtocol - open_* delega para _invoke_nav_callback
# =============================================================================


class TestOpenMethods:
    """Testes para métodos open_* (delegação para _invoke_nav_callback)."""

    def test_open_clientes_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_clientes delega para _invoke_nav_callback('clientes')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_clientes()
            mock_invoke.assert_called_once_with("clientes")

    @pytest.mark.skip(reason="Ação 'senhas' removida – migração CTK")
    def test_open_senhas_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_senhas delega para _invoke_nav_callback('senhas')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_senhas()
            mock_invoke.assert_called_once_with("senhas")

    @pytest.mark.skip(reason="Ação 'auditoria' removida – migração CTK")
    def test_open_auditoria_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_auditoria delega para _invoke_nav_callback('auditoria')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_auditoria()
            mock_invoke.assert_called_once_with("auditoria")

    def test_open_fluxo_caixa_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_fluxo_caixa delega para _invoke_nav_callback('cashflow')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_fluxo_caixa()
            mock_invoke.assert_called_once_with("cashflow")

    def test_open_anvisa_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_anvisa delega para _invoke_nav_callback('anvisa')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_anvisa()
            mock_invoke.assert_called_once_with("anvisa")

    def test_open_farmacia_popular_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_farmacia_popular delega para _invoke_nav_callback('farmacia_popular')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_farmacia_popular()
            mock_invoke.assert_called_once_with("farmacia_popular")

    def test_open_sngpc_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_sngpc delega para _invoke_nav_callback('sngpc')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_sngpc()
            mock_invoke.assert_called_once_with("sngpc")

    def test_open_sifap_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_sifap delega para _invoke_nav_callback('sifap')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_sifap()
            mock_invoke.assert_called_once_with("sifap")

    def test_open_sites_delegates(self, helper: hub_nav.HubNavigationHelper) -> None:
        """open_sites delega para _invoke_nav_callback('sites')."""
        with patch.object(helper, "_invoke_nav_callback") as mock_invoke:
            helper.open_sites()
            mock_invoke.assert_called_once_with("sites")


# =============================================================================
# TEST: _invoke_nav_callback - 3 caminhos de cobertura
# =============================================================================


class TestInvokeNavCallback:
    """Testes para _invoke_nav_callback (cobertura de branches)."""

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_invoke_with_success(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """_invoke_nav_callback com invoke() retornando True."""
        mock_nav_callbacks = MagicMock()
        mock_nav_callbacks.invoke.return_value = True
        dummy_hub._nav_callbacks = mock_nav_callbacks
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper._invoke_nav_callback("clientes")

        mock_nav_callbacks.invoke.assert_called_once_with("clientes")
        mock_logger.debug.assert_not_called()

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_invoke_with_failure(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """_invoke_nav_callback com invoke() retornando False."""
        mock_nav_callbacks = MagicMock()
        mock_nav_callbacks.invoke.return_value = False
        dummy_hub._nav_callbacks = mock_nav_callbacks
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper._invoke_nav_callback("senhas")

        mock_nav_callbacks.invoke.assert_called_once_with("senhas")
        mock_logger.debug.assert_called_once()
        assert "senhas" in mock_logger.debug.call_args[0][0]
        assert "não definido" in mock_logger.debug.call_args[0][0]

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_invoke_without_nav_callbacks_none(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """_invoke_nav_callback quando _nav_callbacks é None."""
        dummy_hub._nav_callbacks = None
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper._invoke_nav_callback("auditoria")

        mock_logger.debug.assert_called_once()
        assert "_nav_callbacks não disponível" in mock_logger.debug.call_args[0][0]

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_invoke_without_nav_callbacks_missing(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """_invoke_nav_callback quando _nav_callbacks não existe (via getattr)."""
        # Não define _nav_callbacks em dummy_hub
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper._invoke_nav_callback("cashflow")

        mock_logger.debug.assert_called_once()
        assert "_nav_callbacks não disponível" in mock_logger.debug.call_args[0][0]

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_invoke_without_invoke_method(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """_invoke_nav_callback quando _nav_callbacks existe mas sem invoke()."""
        # Objeto truthy mas sem método invoke
        dummy_hub._nav_callbacks = object()
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper._invoke_nav_callback("anvisa")

        mock_logger.debug.assert_called_once()
        assert "_nav_callbacks não disponível" in mock_logger.debug.call_args[0][0]


# =============================================================================
# TEST: _call_callback (DEPRECATED mas precisa cobertura)
# =============================================================================


class TestCallCallback:
    """Testes para _call_callback (método deprecated)."""

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_call_callback_exists_and_callable(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """_call_callback chama callback quando existe e é callable."""
        dummy_hub.some_cb = MagicMock()
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper._call_callback("some_cb")

        dummy_hub.some_cb.assert_called_once()
        mock_logger.debug.assert_not_called()

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_call_callback_missing(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """_call_callback loga quando callback não existe."""
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper._call_callback("missing")

        mock_logger.debug.assert_called_once()
        assert "missing" in mock_logger.debug.call_args[0][0]
        assert "não definido ou não é callable" in mock_logger.debug.call_args[0][0]

    @patch("src.modules.hub.views.hub_navigation.logger")
    def test_call_callback_not_callable(self, mock_logger: MagicMock, dummy_hub: SimpleNamespace) -> None:
        """_call_callback loga quando callback existe mas não é callable."""
        dummy_hub.not_callable = "just a string"
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))

        helper._call_callback("not_callable")

        mock_logger.debug.assert_called_once()
        assert "not_callable" in mock_logger.debug.call_args[0][0]
        assert "não definido ou não é callable" in mock_logger.debug.call_args[0][0]


# =============================================================================
# TEST: Estrutura e inicialização
# =============================================================================


class TestStructure:
    """Testes de estrutura do módulo."""

    def test_module_has_logger(self) -> None:
        """Módulo tem logger configurado."""
        assert hasattr(hub_nav, "logger")
        assert hub_nav.logger.name == "src.modules.hub.views.hub_navigation"

    def test_helper_initialization(self, dummy_hub: SimpleNamespace) -> None:
        """HubNavigationHelper inicializa com hub_screen."""
        helper = hub_nav.HubNavigationHelper(cast(Any, dummy_hub))
        assert helper._hub is dummy_hub

    def test_module_docstring(self) -> None:
        """Módulo tem docstring."""
        assert hub_nav.__doc__ is not None
        assert "HubNavigation" in hub_nav.__doc__
