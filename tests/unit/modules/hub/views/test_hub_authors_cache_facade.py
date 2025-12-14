# -*- coding: utf-8 -*-
"""Testes unitários para HubAuthorsCacheFacade (MF-31).

Foco:
- Testar que a facade delega corretamente para HubPollingService e HubStateManager
- Verificar que métodos de cache (refresh, clear, pending fetches) funcionam
- Validar tratamento de erros e logging
"""

import pytest
from unittest.mock import MagicMock

from src.modules.hub.views.hub_authors_cache_facade import HubAuthorsCacheFacade


class TestHubAuthorsCacheFacade:
    """Testes para HubAuthorsCacheFacade (MF-25, MF-31)."""

    @pytest.fixture
    def mock_polling_service(self):
        """Mock do HubPollingService."""
        service = MagicMock()
        service.refresh_authors_cache = MagicMock()
        return service

    @pytest.fixture
    def mock_state_manager(self):
        """Mock do HubStateManager."""
        manager = MagicMock()
        manager.clear_author_cache = MagicMock()
        manager.add_pending_name_fetch = MagicMock()
        manager.remove_pending_name_fetch = MagicMock()
        manager.set_names_cache_loaded = MagicMock()
        return manager

    @pytest.fixture
    def mock_get_org_id(self):
        """Mock do callback get_org_id."""
        return MagicMock(return_value="test-org-123")

    @pytest.fixture
    def mock_auth_ready(self):
        """Mock do callback auth_ready."""
        return MagicMock(return_value=True)

    @pytest.fixture
    def mock_debug_logger(self):
        """Mock do debug logger."""
        return MagicMock()

    @pytest.fixture
    def facade(
        self,
        mock_polling_service,
        mock_state_manager,
        mock_get_org_id,
        mock_auth_ready,
    ):
        """Facade sem debug logger."""
        return HubAuthorsCacheFacade(
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            get_org_id=mock_get_org_id,
            auth_ready_callback=mock_auth_ready,
            debug_logger=None,
        )

    @pytest.fixture
    def facade_with_debug(
        self,
        mock_polling_service,
        mock_state_manager,
        mock_get_org_id,
        mock_auth_ready,
        mock_debug_logger,
    ):
        """Facade com debug logger."""
        return HubAuthorsCacheFacade(
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            get_org_id=mock_get_org_id,
            auth_ready_callback=mock_auth_ready,
            debug_logger=mock_debug_logger,
        )

    # ==========================================================================
    # TESTES DE REFRESH DE CACHE
    # ==========================================================================

    def test_refresh_author_names_cache_sem_force(self, facade, mock_polling_service):
        """Testa refresh de cache sem forçar."""
        facade.refresh_author_names_cache(force=False)
        mock_polling_service.refresh_authors_cache.assert_called_once_with(force=False)

    def test_refresh_author_names_cache_com_force(self, facade, mock_polling_service):
        """Testa refresh de cache forçado."""
        facade.refresh_author_names_cache(force=True)
        mock_polling_service.refresh_authors_cache.assert_called_once_with(force=True)

    def test_refresh_author_names_cache_padrao_force_false(self, facade, mock_polling_service):
        """Testa que o padrão de force é False."""
        facade.refresh_author_names_cache()
        mock_polling_service.refresh_authors_cache.assert_called_once_with(force=False)

    def test_refresh_author_names_cache_trata_excecao(self, facade, mock_polling_service):
        """Testa que exceções em refresh são tratadas."""
        mock_polling_service.refresh_authors_cache.side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.refresh_author_names_cache(force=True)
        # Verifica que tentou chamar
        mock_polling_service.refresh_authors_cache.assert_called_once()

    # ==========================================================================
    # TESTES DE CLEAR DE CACHE
    # ==========================================================================

    def test_clear_author_cache_delega_para_state_manager(self, facade, mock_state_manager):
        """Testa que clear_author_cache delega para StateManager."""
        facade.clear_author_cache()
        mock_state_manager.clear_author_cache.assert_called_once_with()

    def test_clear_author_cache_trata_excecao(self, facade, mock_state_manager):
        """Testa que exceções em clear são tratadas."""
        mock_state_manager.clear_author_cache.side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.clear_author_cache()
        # Verifica que tentou chamar
        mock_state_manager.clear_author_cache.assert_called_once()

    # ==========================================================================
    # TESTES DE GERENCIAMENTO DE PENDÊNCIAS
    # ==========================================================================

    def test_add_pending_name_fetch_delega_para_state_manager(self, facade, mock_state_manager):
        """Testa que add_pending_name_fetch delega para StateManager."""
        facade.add_pending_name_fetch("teste@exemplo.com")
        mock_state_manager.add_pending_name_fetch.assert_called_once_with("teste@exemplo.com")

    def test_add_pending_name_fetch_trata_excecao(self, facade, mock_state_manager):
        """Testa que exceções em add_pending são tratadas."""
        mock_state_manager.add_pending_name_fetch.side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.add_pending_name_fetch("teste@exemplo.com")
        # Verifica que tentou chamar
        mock_state_manager.add_pending_name_fetch.assert_called_once()

    def test_remove_pending_name_fetch_delega_para_state_manager(self, facade, mock_state_manager):
        """Testa que remove_pending_name_fetch delega para StateManager."""
        facade.remove_pending_name_fetch("teste@exemplo.com")
        mock_state_manager.remove_pending_name_fetch.assert_called_once_with("teste@exemplo.com")

    def test_remove_pending_name_fetch_trata_excecao(self, facade, mock_state_manager):
        """Testa que exceções em remove_pending são tratadas."""
        mock_state_manager.remove_pending_name_fetch.side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.remove_pending_name_fetch("teste@exemplo.com")
        # Verifica que tentou chamar
        mock_state_manager.remove_pending_name_fetch.assert_called_once()

    # ==========================================================================
    # TESTES DE ESTADO DE CACHE CARREGADO
    # ==========================================================================

    def test_set_names_cache_loaded_true_delega_para_state_manager(self, facade, mock_state_manager):
        """Testa que set_names_cache_loaded(True) delega para StateManager."""
        facade.set_names_cache_loaded(True)
        mock_state_manager.set_names_cache_loaded.assert_called_once_with(True)

    def test_set_names_cache_loaded_false_delega_para_state_manager(self, facade, mock_state_manager):
        """Testa que set_names_cache_loaded(False) delega para StateManager."""
        facade.set_names_cache_loaded(False)
        mock_state_manager.set_names_cache_loaded.assert_called_once_with(False)

    def test_set_names_cache_loaded_trata_excecao(self, facade, mock_state_manager):
        """Testa que exceções em set_names_cache_loaded são tratadas."""
        mock_state_manager.set_names_cache_loaded.side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.set_names_cache_loaded(True)
        # Verifica que tentou chamar
        mock_state_manager.set_names_cache_loaded.assert_called_once()

    # ==========================================================================
    # TESTES DE DEBUG LOGGING
    # ==========================================================================

    def test_refresh_com_debug_logger_faz_log(self, facade_with_debug, mock_debug_logger, mock_polling_service):
        """Testa que refresh loga quando debug está habilitado."""
        facade_with_debug.refresh_author_names_cache(force=True)
        # Verifica que o logger foi chamado
        assert mock_debug_logger.called
        # Verifica que a mensagem contém informação relevante
        call_args_list = [call[0][0] for call in mock_debug_logger.call_args_list]
        assert any("force=True" in msg for msg in call_args_list)

    def test_clear_com_debug_logger_faz_log(self, facade_with_debug, mock_debug_logger, mock_state_manager):
        """Testa que clear loga quando debug está habilitado."""
        facade_with_debug.clear_author_cache()
        # Verifica que o logger foi chamado
        assert mock_debug_logger.called

    def test_operacoes_sem_debug_logger_nao_falham(self, facade):
        """Testa que operações funcionam sem debug logger."""
        # Não deve levantar exceção mesmo sem logger
        facade.refresh_author_names_cache()
        facade.clear_author_cache()
        facade.add_pending_name_fetch("test@exemplo.com")
        facade.remove_pending_name_fetch("test@exemplo.com")
        facade.set_names_cache_loaded(True)
