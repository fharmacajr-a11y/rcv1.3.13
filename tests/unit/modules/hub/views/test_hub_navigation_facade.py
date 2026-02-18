# -*- coding: utf-8 -*-
"""Testes unitários para HubNavigationFacade (MF-31).

Foco:
- Testar que a facade delega corretamente para HubNavigationHelper
- Verificar que todos os métodos go_to_* e open_* chamam os métodos corretos
- Validar comportamento de debug logging opcional
"""

import pytest
from unittest.mock import MagicMock

from src.modules.hub.views.hub_navigation_facade import HubNavigationFacade


class TestHubNavigationFacade:
    """Testes para HubNavigationFacade (MF-22, MF-31)."""

    @pytest.fixture
    def mock_nav_helper(self):
        """Mock do HubNavigationHelper."""
        helper = MagicMock()
        helper.go_to_clients = MagicMock()
        helper.go_to_pending = MagicMock()
        helper.go_to_tasks_today = MagicMock()
        helper.open_clientes = MagicMock()
        helper.open_fluxo_caixa = MagicMock()
        helper.open_anvisa = MagicMock()
        helper.open_farmacia_popular = MagicMock()
        helper.open_sngpc = MagicMock()
        helper.open_sifap = MagicMock()
        helper.open_sites = MagicMock()
        return helper

    @pytest.fixture
    def mock_debug_logger(self):
        """Mock do debug logger."""
        return MagicMock()

    @pytest.fixture
    def facade_without_debug(self, mock_nav_helper):
        """Facade sem debug logger."""
        return HubNavigationFacade(nav_helper=mock_nav_helper, debug_logger=None)

    @pytest.fixture
    def facade_with_debug(self, mock_nav_helper, mock_debug_logger):
        """Facade com debug logger."""
        return HubNavigationFacade(nav_helper=mock_nav_helper, debug_logger=mock_debug_logger)

    # ==========================================================================
    # TESTES DE go_to_* (navegação interna)
    # ==========================================================================

    def test_go_to_clients_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que go_to_clients delega para helper."""
        facade_without_debug.go_to_clients()
        mock_nav_helper.go_to_clients.assert_called_once_with()

    def test_go_to_clients_com_debug_logger(self, facade_with_debug, mock_nav_helper, mock_debug_logger):
        """Testa que go_to_clients loga quando debug está habilitado."""
        facade_with_debug.go_to_clients()
        mock_nav_helper.go_to_clients.assert_called_once_with()
        mock_debug_logger.assert_called_once()
        # Verifica que a mensagem de log contém informação relevante
        call_args = mock_debug_logger.call_args[0][0]
        assert "go_to_clients" in call_args

    def test_go_to_pending_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que go_to_pending delega para helper."""
        facade_without_debug.go_to_pending()
        mock_nav_helper.go_to_pending.assert_called_once_with()

    def test_go_to_tasks_today_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que go_to_tasks_today delega para helper."""
        facade_without_debug.go_to_tasks_today()
        mock_nav_helper.go_to_tasks_today.assert_called_once_with()

    # ==========================================================================
    # TESTES DE open_* (abertura de módulos)
    # ==========================================================================

    def test_open_clientes_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_clientes delega para helper."""
        facade_without_debug.open_clientes()
        mock_nav_helper.open_clientes.assert_called_once_with()

    @pytest.mark.skip(reason="Ação 'senhas' removida – migração CTK")
    def test_open_senhas_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_senhas delega para helper."""
        facade_without_debug.open_senhas()
        mock_nav_helper.open_senhas.assert_called_once_with()

    @pytest.mark.skip(reason="Ação 'auditoria' removida – migração CTK")
    def test_open_auditoria_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_auditoria delega para helper."""
        facade_without_debug.open_auditoria()
        mock_nav_helper.open_auditoria.assert_called_once_with()

    def test_open_fluxo_caixa_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_fluxo_caixa delega para helper."""
        facade_without_debug.open_fluxo_caixa()
        mock_nav_helper.open_fluxo_caixa.assert_called_once_with()

    def test_open_anvisa_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_anvisa delega para helper."""
        facade_without_debug.open_anvisa()
        mock_nav_helper.open_anvisa.assert_called_once_with()

    def test_open_farmacia_popular_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_farmacia_popular delega para helper."""
        facade_without_debug.open_farmacia_popular()
        mock_nav_helper.open_farmacia_popular.assert_called_once_with()

    def test_open_sngpc_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_sngpc delega para helper."""
        facade_without_debug.open_sngpc()
        mock_nav_helper.open_sngpc.assert_called_once_with()

    def test_open_sifap_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_sifap delega para helper."""
        facade_without_debug.open_sifap()
        mock_nav_helper.open_sifap.assert_called_once_with()

    def test_open_sites_delega_para_helper(self, facade_without_debug, mock_nav_helper):
        """Testa que open_sites delega para helper."""
        facade_without_debug.open_sites()
        mock_nav_helper.open_sites.assert_called_once_with()

    # ==========================================================================
    # TESTES DE COMPORTAMENTO (debug logger)
    # ==========================================================================

    def test_todos_metodos_open_logam_com_debug(self, facade_with_debug, mock_debug_logger):
        """Testa que todos os métodos open_* fazem log quando debug está habilitado."""
        metodos_open = [
            "open_clientes",
            "open_fluxo_caixa",
            "open_anvisa",
            "open_farmacia_popular",
            "open_sngpc",
            "open_sifap",
            "open_sites",
        ]

        for metodo in metodos_open:
            mock_debug_logger.reset_mock()
            getattr(facade_with_debug, metodo)()
            mock_debug_logger.assert_called_once()
            call_msg = mock_debug_logger.call_args[0][0]
            assert metodo in call_msg

    def test_sem_debug_logger_nao_tenta_logar(self, facade_without_debug, mock_nav_helper):
        """Testa que sem debug logger, não há tentativa de log."""
        # Não deve levantar exceção mesmo sem logger
        facade_without_debug.go_to_clients()
        facade_without_debug.open_fluxo_caixa()
        # Verifica que helper foi chamado normalmente
        mock_nav_helper.go_to_clients.assert_called_once()
        mock_nav_helper.open_fluxo_caixa.assert_called_once()
