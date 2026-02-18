# -*- coding: utf-8 -*-
"""Testes unitários para hub_navigation_facade.py (MF-56).

Cobre:
- Delegação sem debug_logger
- Delegação com debug_logger
- Logger fallback

Estratégia:
- Headless (mock de nav_helper)
- Verificação de delegação 1:1
- Cobertura de todos os métodos go_to_* e open_*
"""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import src.modules.hub.views.hub_navigation_facade as hub_navigation_facade
from src.modules.hub.views.hub_navigation_facade import HubNavigationFacade


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: Delegação SEM debug_logger
# ═══════════════════════════════════════════════════════════════════════════════


class TestNavigationFacadeDelegationWithoutDebugLogger:
    """Testes de delegação sem debug_logger."""

    def test_go_to_clients_delegates_to_nav_helper(self) -> None:
        """go_to_clients deve delegar para nav_helper.go_to_clients."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.go_to_clients()

        nav_helper.go_to_clients.assert_called_once_with()

    def test_go_to_pending_delegates_to_nav_helper(self) -> None:
        """go_to_pending deve delegar para nav_helper.go_to_pending."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.go_to_pending()

        nav_helper.go_to_pending.assert_called_once_with()

    def test_go_to_tasks_today_delegates_to_nav_helper(self) -> None:
        """go_to_tasks_today deve delegar para nav_helper.go_to_tasks_today."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.go_to_tasks_today()

        nav_helper.go_to_tasks_today.assert_called_once_with()

    def test_open_clientes_delegates_to_nav_helper(self) -> None:
        """open_clientes deve delegar para nav_helper.open_clientes."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_clientes()

        nav_helper.open_clientes.assert_called_once_with()

    @pytest.mark.skip(reason="Ação 'senhas' removida – migração CTK")
    def test_open_senhas_delegates_to_nav_helper(self) -> None:
        """open_senhas deve delegar para nav_helper.open_senhas."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_senhas()

        nav_helper.open_senhas.assert_called_once_with()

    @pytest.mark.skip(reason="Ação 'auditoria' removida – migração CTK")
    def test_open_auditoria_delegates_to_nav_helper(self) -> None:
        """open_auditoria deve delegar para nav_helper.open_auditoria."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_auditoria()

        nav_helper.open_auditoria.assert_called_once_with()

    def test_open_fluxo_caixa_delegates_to_nav_helper(self) -> None:
        """open_fluxo_caixa deve delegar para nav_helper.open_fluxo_caixa."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_fluxo_caixa()

        nav_helper.open_fluxo_caixa.assert_called_once_with()

    def test_open_anvisa_delegates_to_nav_helper(self) -> None:
        """open_anvisa deve delegar para nav_helper.open_anvisa."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_anvisa()

        nav_helper.open_anvisa.assert_called_once_with()

    def test_open_farmacia_popular_delegates_to_nav_helper(self) -> None:
        """open_farmacia_popular deve delegar para nav_helper.open_farmacia_popular."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_farmacia_popular()

        nav_helper.open_farmacia_popular.assert_called_once_with()

    def test_open_sngpc_delegates_to_nav_helper(self) -> None:
        """open_sngpc deve delegar para nav_helper.open_sngpc."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_sngpc()

        nav_helper.open_sngpc.assert_called_once_with()

    def test_open_sifap_delegates_to_nav_helper(self) -> None:
        """open_sifap deve delegar para nav_helper.open_sifap."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_sifap()

        nav_helper.open_sifap.assert_called_once_with()

    def test_open_sites_delegates_to_nav_helper(self) -> None:
        """open_sites deve delegar para nav_helper.open_sites."""
        nav_helper = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=None)

        facade.open_sites()

        nav_helper.open_sites.assert_called_once_with()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: Delegação COM debug_logger
# ═══════════════════════════════════════════════════════════════════════════════


class TestNavigationFacadeDelegationWithDebugLogger:
    """Testes de delegação com debug_logger."""

    def test_go_to_clients_logs_and_delegates(self) -> None:
        """go_to_clients com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.go_to_clients()

        debug_logger.assert_called_once_with("NavigationFacade: go_to_clients")
        nav_helper.go_to_clients.assert_called_once_with()

    def test_go_to_pending_logs_and_delegates(self) -> None:
        """go_to_pending com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.go_to_pending()

        debug_logger.assert_called_once_with("NavigationFacade: go_to_pending")
        nav_helper.go_to_pending.assert_called_once_with()

    def test_go_to_tasks_today_logs_and_delegates(self) -> None:
        """go_to_tasks_today com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.go_to_tasks_today()

        debug_logger.assert_called_once_with("NavigationFacade: go_to_tasks_today")
        nav_helper.go_to_tasks_today.assert_called_once_with()

    def test_open_clientes_logs_and_delegates(self) -> None:
        """open_clientes com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_clientes()

        debug_logger.assert_called_once_with("NavigationFacade: open_clientes")
        nav_helper.open_clientes.assert_called_once_with()

    @pytest.mark.skip(reason="Ação 'senhas' removida – migração CTK")
    def test_open_senhas_logs_and_delegates(self) -> None:
        """open_senhas com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_senhas()

        debug_logger.assert_called_once_with("NavigationFacade: open_senhas")
        nav_helper.open_senhas.assert_called_once_with()

    @pytest.mark.skip(reason="Ação 'auditoria' removida – migração CTK")
    def test_open_auditoria_logs_and_delegates(self) -> None:
        """open_auditoria com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_auditoria()

        debug_logger.assert_called_once_with("NavigationFacade: open_auditoria")
        nav_helper.open_auditoria.assert_called_once_with()

    def test_open_fluxo_caixa_logs_and_delegates(self) -> None:
        """open_fluxo_caixa com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_fluxo_caixa()

        debug_logger.assert_called_once_with("NavigationFacade: open_fluxo_caixa")
        nav_helper.open_fluxo_caixa.assert_called_once_with()

    def test_open_anvisa_logs_and_delegates(self) -> None:
        """open_anvisa com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_anvisa()

        debug_logger.assert_called_once_with("NavigationFacade: open_anvisa")
        nav_helper.open_anvisa.assert_called_once_with()

    def test_open_farmacia_popular_logs_and_delegates(self) -> None:
        """open_farmacia_popular com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_farmacia_popular()

        debug_logger.assert_called_once_with("NavigationFacade: open_farmacia_popular")
        nav_helper.open_farmacia_popular.assert_called_once_with()

    def test_open_sngpc_logs_and_delegates(self) -> None:
        """open_sngpc com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_sngpc()

        debug_logger.assert_called_once_with("NavigationFacade: open_sngpc")
        nav_helper.open_sngpc.assert_called_once_with()

    def test_open_sifap_logs_and_delegates(self) -> None:
        """open_sifap com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_sifap()

        debug_logger.assert_called_once_with("NavigationFacade: open_sifap")
        nav_helper.open_sifap.assert_called_once_with()

    def test_open_sites_logs_and_delegates(self) -> None:
        """open_sites com debug_logger deve logar e delegar."""
        nav_helper = MagicMock()
        debug_logger = MagicMock()
        facade = HubNavigationFacade(nav_helper, debug_logger=debug_logger)

        facade.open_sites()

        debug_logger.assert_called_once_with("NavigationFacade: open_sites")
        nav_helper.open_sites.assert_called_once_with()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: Logger Fallback
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoggerFallback:
    """Testes para fallback de logger."""

    def test_logger_fallback_on_import_error(self) -> None:
        """Deve usar logging.getLogger quando src.core.logger falha."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any):
            if name == "src.core.logger":
                raise ImportError("src.core.logger not found")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            importlib.reload(hub_navigation_facade)

            # Após reload, get_logger deve ser o fallback
            logger_instance = hub_navigation_facade.get_logger("test_fallback")
            assert logger_instance.name == "test_fallback"

        # Restaurar módulo
        importlib.reload(hub_navigation_facade)
