# -*- coding: utf-8 -*-
"""Testes unitários para HubLifecycleFacade (MF-31).

Foco:
- Testar que a facade delega corretamente para serviços de lifecycle
- Verificar operações de polling (start/stop)
- Validar operações de live sync
- Testar on_show com callbacks corretos
"""

import pytest
from unittest.mock import MagicMock

from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade


class TestHubLifecycleFacade:
    """Testes para HubLifecycleFacade (MF-24, MF-31)."""

    @pytest.fixture
    def mock_parent(self):
        """Mock do widget pai (HubScreen)."""
        parent = MagicMock()
        parent.notes_history = []
        return parent

    @pytest.fixture
    def mock_lifecycle_manager(self):
        """Mock do HubLifecycleManager."""
        manager = MagicMock()
        manager.start = MagicMock()
        manager.stop = MagicMock()
        return manager

    @pytest.fixture
    def mock_lifecycle_impl(self):
        """Mock do HubLifecycleImpl."""
        impl = MagicMock()
        impl.start_live_sync = MagicMock()
        impl.stop_live_sync = MagicMock()
        return impl

    @pytest.fixture
    def mock_polling_service(self):
        """Mock do HubPollingService."""
        return MagicMock()

    @pytest.fixture
    def mock_state_manager(self):
        """Mock do HubStateManager."""
        manager = MagicMock()
        manager.set_polling_active = MagicMock()
        return manager

    @pytest.fixture
    def mock_callbacks(self):
        """Mock de todos os callbacks necessários."""
        return {
            "auth_ready": MagicMock(return_value=True),
            "get_org_id": MagicMock(return_value="test-org-123"),
            "get_email": MagicMock(return_value="test@example.com"),
            "start_live_sync": MagicMock(),
            "render_notes": MagicMock(),
            "refresh_author_cache": MagicMock(),
            "clear_author_cache": MagicMock(),
        }

    @pytest.fixture
    def facade(
        self,
        mock_parent,
        mock_lifecycle_manager,
        mock_lifecycle_impl,
        mock_polling_service,
        mock_state_manager,
        mock_callbacks,
    ):
        """Facade sem debug logger."""
        return HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=mock_lifecycle_manager,
            lifecycle_impl=mock_lifecycle_impl,
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            auth_ready_callback=mock_callbacks["auth_ready"],
            get_org_id=mock_callbacks["get_org_id"],
            get_email=mock_callbacks["get_email"],
            start_live_sync_callback=mock_callbacks["start_live_sync"],
            render_notes_callback=mock_callbacks["render_notes"],
            refresh_author_cache_callback=mock_callbacks["refresh_author_cache"],
            clear_author_cache_callback=mock_callbacks["clear_author_cache"],
            debug_logger=None,
        )

    # ==========================================================================
    # TESTES DE LIVE SYNC
    # ==========================================================================

    def test_start_live_sync_impl_delega_para_lifecycle_impl(self, facade, mock_lifecycle_impl):
        """Testa que start_live_sync_impl delega para lifecycle_impl."""
        facade.start_live_sync_impl()
        mock_lifecycle_impl.start_live_sync.assert_called_once_with()

    def test_stop_live_sync_impl_delega_para_lifecycle_impl(self, facade, mock_lifecycle_impl):
        """Testa que stop_live_sync_impl delega para lifecycle_impl."""
        facade.stop_live_sync_impl()
        mock_lifecycle_impl.stop_live_sync.assert_called_once_with()

    def test_start_live_sync_alias_chama_impl(self, facade, mock_lifecycle_impl):
        """Testa que start_live_sync é um alias para start_live_sync_impl."""
        facade.start_live_sync()
        mock_lifecycle_impl.start_live_sync.assert_called_once_with()

    def test_start_live_sync_impl_trata_excecao(self, facade, mock_lifecycle_impl):
        """Testa que exceções em start_live_sync_impl são tratadas."""
        mock_lifecycle_impl.start_live_sync.side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.start_live_sync_impl()
        # Verifica que tentou chamar
        mock_lifecycle_impl.start_live_sync.assert_called_once()

    def test_stop_live_sync_impl_trata_excecao(self, facade, mock_lifecycle_impl):
        """Testa que exceções em stop_live_sync_impl são tratadas."""
        mock_lifecycle_impl.stop_live_sync.side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.stop_live_sync_impl()
        # Verifica que tentou chamar
        mock_lifecycle_impl.stop_live_sync.assert_called_once()

    # ==========================================================================
    # TESTES DE POLLING
    # ==========================================================================

    def test_start_polling_ativa_estado_e_inicia_manager(self, facade, mock_state_manager, mock_lifecycle_manager):
        """Testa que start_polling ativa polling e inicia lifecycle manager."""
        facade.start_polling()

        mock_state_manager.set_polling_active.assert_called_once_with(True)
        mock_lifecycle_manager.start.assert_called_once_with()

    def test_stop_polling_desativa_estado_e_para_manager(self, facade, mock_state_manager, mock_lifecycle_manager):
        """Testa que stop_polling desativa polling e para lifecycle manager."""
        facade.stop_polling()

        mock_state_manager.set_polling_active.assert_called_once_with(False)
        mock_lifecycle_manager.stop.assert_called_once_with()

    def test_start_polling_com_lifecycle_manager_none(
        self, mock_parent, mock_lifecycle_impl, mock_polling_service, mock_state_manager, mock_callbacks
    ):
        """Testa que start_polling funciona com lifecycle_manager=None."""
        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=None,  # None é permitido
            lifecycle_impl=mock_lifecycle_impl,
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            auth_ready_callback=mock_callbacks["auth_ready"],
            get_org_id=mock_callbacks["get_org_id"],
            get_email=mock_callbacks["get_email"],
            start_live_sync_callback=mock_callbacks["start_live_sync"],
            render_notes_callback=mock_callbacks["render_notes"],
            refresh_author_cache_callback=mock_callbacks["refresh_author_cache"],
            clear_author_cache_callback=mock_callbacks["clear_author_cache"],
        )

        # Não deve levantar exceção
        facade.start_polling()
        # Deve apenas alterar estado
        mock_state_manager.set_polling_active.assert_called_once_with(True)

    def test_start_polling_trata_excecao(self, facade, mock_state_manager):
        """Testa que exceções em start_polling são tratadas."""
        mock_state_manager.set_polling_active.side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.start_polling()
        # Verifica que tentou chamar
        mock_state_manager.set_polling_active.assert_called_once()

    # ==========================================================================
    # TESTES DE ON_SHOW
    # ==========================================================================

    def test_on_show_inicia_live_sync(self, facade, mock_callbacks):
        """Testa que on_show inicia live sync."""
        facade.on_show()
        mock_callbacks["start_live_sync"].assert_called_once_with()

    def test_on_show_com_historico_vazio_renderiza_cache(self, facade, mock_parent, mock_callbacks, mock_state_manager):
        """Testa que on_show renderiza cache quando histórico está vazio."""
        mock_parent.notes_history = []
        mock_state = MagicMock()
        mock_state.notes_last_data = [{"id": "1", "text": "Nota teste"}]
        mock_state_manager.state = mock_state

        facade.on_show()

        # Verifica que render_notes foi chamado com dados do cache
        # MF-27: callback deve ser chamado sem keyword args
        assert mock_callbacks["render_notes"].called

    def test_on_show_limpa_e_atualiza_cache_autores(self, facade, mock_callbacks):
        """Testa que on_show limpa e atualiza cache de autores."""
        facade.on_show()

        mock_callbacks["clear_author_cache"].assert_called_once_with()
        # MF-27: callback deve ser chamado sem keyword args
        assert mock_callbacks["refresh_author_cache"].called

    def test_on_show_trata_excecao(self, facade, mock_callbacks):
        """Testa que exceções em on_show são tratadas."""
        mock_callbacks["start_live_sync"].side_effect = Exception("Erro de teste")
        # Não deve propagar exceção
        facade.on_show()
        # Verifica que tentou chamar
        mock_callbacks["start_live_sync"].assert_called_once()

    # ==========================================================================
    # TESTES DE TIMERS E SCHEDULING
    # ==========================================================================

    def test_start_timers_delega_para_lifecycle_manager(self, facade, mock_lifecycle_manager):
        """Testa que start_timers delega para lifecycle_manager."""
        facade.start_timers()
        mock_lifecycle_manager.start.assert_called_once_with()

    def test_schedule_poll_delega_para_polling_service(self, facade, mock_polling_service):
        """Testa que schedule_poll delega para polling_service."""
        facade.schedule_poll(5000)
        mock_polling_service.schedule_next_poll.assert_called_once_with(delay_ms=5000)

    # ==========================================================================
    # TESTES DE DEBUG LOGGING
    # ==========================================================================

    def test_operacoes_com_debug_logger(
        self,
        mock_parent,
        mock_lifecycle_manager,
        mock_lifecycle_impl,
        mock_polling_service,
        mock_state_manager,
        mock_callbacks,
    ):
        """Testa que operações fazem log quando debug está habilitado."""
        mock_debug_logger = MagicMock()
        facade_with_debug = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=mock_lifecycle_manager,
            lifecycle_impl=mock_lifecycle_impl,
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            auth_ready_callback=mock_callbacks["auth_ready"],
            get_org_id=mock_callbacks["get_org_id"],
            get_email=mock_callbacks["get_email"],
            start_live_sync_callback=mock_callbacks["start_live_sync"],
            render_notes_callback=mock_callbacks["render_notes"],
            refresh_author_cache_callback=mock_callbacks["refresh_author_cache"],
            clear_author_cache_callback=mock_callbacks["clear_author_cache"],
            debug_logger=mock_debug_logger,
        )

        facade_with_debug.start_polling()

        # Verifica que logger foi chamado (via _log_debug)
        assert mock_debug_logger.called
