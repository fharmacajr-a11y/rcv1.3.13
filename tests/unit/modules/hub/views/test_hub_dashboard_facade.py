# -*- coding: utf-8 -*-
"""Testes unitários para HubDashboardFacade (MF-31).

Foco:
- Testar que a facade delega corretamente para handlers de dashboard
- Verificar que callbacks (tasks, obligations, cards) chamam métodos corretos
- Validar fluxo de obrigações (pick client)
"""

import pytest
from unittest.mock import MagicMock, patch

from src.modules.hub.views.hub_dashboard_facade import HubDashboardFacade


class TestHubDashboardFacade:
    """Testes para HubDashboardFacade (MF-22, MF-31)."""

    @pytest.fixture
    def mock_parent(self):
        """Mock do widget pai (HubScreen)."""
        parent = MagicMock()
        parent._pending_obligation_org_id = None
        parent._pending_obligation_user_id = None
        return parent

    @pytest.fixture
    def mock_dashboard_vm(self):
        """Mock do DashboardViewModel."""
        return MagicMock()

    @pytest.fixture
    def mock_dashboard_actions(self):
        """Mock do DashboardActionController."""
        return MagicMock()

    @pytest.fixture
    def mock_renderer(self):
        """Mock do HubDashboardRenderer."""
        return MagicMock()

    @pytest.fixture
    def mock_state_manager(self):
        """Mock do HubStateManager."""
        return MagicMock()

    @pytest.fixture
    def mock_get_org_id(self):
        """Mock do callback get_org_id."""
        return MagicMock(return_value="test-org-123")

    @pytest.fixture
    def mock_get_user_id(self):
        """Mock do callback get_user_id."""
        return MagicMock(return_value="test-user-456")

    @pytest.fixture
    def mock_get_main_app(self):
        """Mock do callback get_main_app."""
        return MagicMock(return_value=MagicMock())

    @pytest.fixture
    def mock_on_refresh(self):
        """Mock do callback on_refresh."""
        return MagicMock()

    @pytest.fixture
    def facade(
        self,
        mock_parent,
        mock_dashboard_vm,
        mock_dashboard_actions,
        mock_renderer,
        mock_state_manager,
        mock_get_org_id,
        mock_get_user_id,
        mock_get_main_app,
        mock_on_refresh,
    ):
        """Facade sem debug logger."""
        return HubDashboardFacade(
            parent=mock_parent,
            dashboard_vm=mock_dashboard_vm,
            dashboard_actions=mock_dashboard_actions,
            renderer=mock_renderer,
            state_manager=mock_state_manager,
            get_org_id=mock_get_org_id,
            get_user_id=mock_get_user_id,
            get_main_app=mock_get_main_app,
            on_refresh_callback=mock_on_refresh,
            debug_logger=None,
        )

    # ==========================================================================
    # TESTES DE AÇÕES DO DASHBOARD
    # ==========================================================================

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_new_task_click_v2")
    def test_on_new_task_chama_handler(
        self, mock_handler, facade, mock_parent, mock_get_org_id, mock_get_user_id, mock_on_refresh
    ):
        """Testa que on_new_task chama o handler correto."""
        facade.on_new_task()

        mock_handler.assert_called_once_with(
            parent=mock_parent,
            get_org_id=mock_get_org_id,
            get_user_id=mock_get_user_id,
            on_success_callback=mock_on_refresh,
        )

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_new_obligation_click_v2")
    def test_on_new_obligation_chama_handler(
        self,
        mock_handler,
        facade,
        mock_parent,
        mock_get_org_id,
        mock_get_user_id,
        mock_get_main_app,
    ):
        """Testa que on_new_obligation chama o handler correto."""
        facade.on_new_obligation()

        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        assert call_args[1]["parent"] == mock_parent
        assert call_args[1]["get_org_id"] == mock_get_org_id
        assert call_args[1]["get_user_id"] == mock_get_user_id
        assert call_args[1]["get_main_app"] == mock_get_main_app
        assert "on_client_picked" in call_args[1]

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_new_obligation_click_v2")
    def test_on_new_obligation_armazena_ids_no_parent(
        self, mock_handler, facade, mock_parent, mock_get_org_id, mock_get_user_id
    ):
        """Testa que on_new_obligation armazena org_id e user_id no parent."""
        facade.on_new_obligation()

        # Verifica que IDs foram armazenados no parent
        assert mock_parent._pending_obligation_org_id == "test-org-123"
        assert mock_parent._pending_obligation_user_id == "test-user-456"

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_view_all_activity_click_v2")
    def test_on_view_all_activity_chama_handler(self, mock_handler, facade, mock_parent):
        """Testa que on_view_all_activity chama o handler correto."""
        facade.on_view_all_activity()

        mock_handler.assert_called_once_with(parent=mock_parent)

    # ==========================================================================
    # TESTES DE CALLBACKS DE CARDS
    # ==========================================================================

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_card_clients_click")
    def test_on_card_clients_click_chama_handler(
        self, mock_handler, facade, mock_dashboard_vm, mock_dashboard_actions, mock_parent
    ):
        """Testa que on_card_clients_click chama o handler correto."""
        facade.on_card_clients_click()

        mock_handler.assert_called_once_with(
            dashboard_vm=mock_dashboard_vm,
            dashboard_actions=mock_dashboard_actions,
            parent=mock_parent,
        )

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_card_pendencias_click")
    def test_on_card_pendencias_click_chama_handler(
        self, mock_handler, facade, mock_dashboard_vm, mock_dashboard_actions, mock_parent
    ):
        """Testa que on_card_pendencias_click chama o handler correto."""
        facade.on_card_pendencias_click()

        mock_handler.assert_called_once_with(
            dashboard_vm=mock_dashboard_vm,
            dashboard_actions=mock_dashboard_actions,
            parent=mock_parent,
        )

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_card_tarefas_click")
    def test_on_card_tarefas_click_chama_handler(
        self, mock_handler, facade, mock_dashboard_vm, mock_dashboard_actions, mock_parent
    ):
        """Testa que on_card_tarefas_click chama o handler correto."""
        facade.on_card_tarefas_click()

        mock_handler.assert_called_once_with(
            dashboard_vm=mock_dashboard_vm,
            dashboard_actions=mock_dashboard_actions,
            parent=mock_parent,
        )

    # ==========================================================================
    # TESTES DE CALLBACK DE CLIENTE SELECIONADO
    # ==========================================================================

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_client_picked_for_obligation_v2")
    def test_on_client_picked_for_obligation_chama_handler(
        self, mock_handler, facade, mock_parent, mock_get_main_app, mock_on_refresh
    ):
        """Testa que on_client_picked_for_obligation chama o handler correto."""
        client_data = {"id": "client-123", "nome": "Cliente Teste"}

        # Simular IDs armazenados (como seria feito pelo on_new_obligation)
        mock_parent._pending_obligation_org_id = "test-org-123"
        mock_parent._pending_obligation_user_id = "test-user-456"

        facade.on_client_picked_for_obligation(client_data)

        mock_handler.assert_called_once()
        call_args = mock_handler.call_args[1]
        assert call_args["client_data"] == client_data
        assert call_args["parent"] == mock_parent
        assert call_args["get_main_app"] == mock_get_main_app
        assert call_args["on_refresh_callback"] == mock_on_refresh

        # Verifica que os lambdas retornam os IDs corretos
        assert call_args["get_org_id"]() == "test-org-123"
        assert call_args["get_user_id"]() == "test-user-456"

    # ==========================================================================
    # TESTES DE DEBUG LOGGING
    # ==========================================================================

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_new_task_click_v2")
    def test_on_new_task_com_debug_logger(
        self,
        mock_handler,
        mock_parent,
        mock_dashboard_vm,
        mock_dashboard_actions,
        mock_renderer,
        mock_state_manager,
        mock_get_org_id,
        mock_get_user_id,
        mock_get_main_app,
        mock_on_refresh,
    ):
        """Testa que on_new_task loga quando debug está habilitado."""
        mock_debug_logger = MagicMock()
        facade_with_debug = HubDashboardFacade(
            parent=mock_parent,
            dashboard_vm=mock_dashboard_vm,
            dashboard_actions=mock_dashboard_actions,
            renderer=mock_renderer,
            state_manager=mock_state_manager,
            get_org_id=mock_get_org_id,
            get_user_id=mock_get_user_id,
            get_main_app=mock_get_main_app,
            on_refresh_callback=mock_on_refresh,
            debug_logger=mock_debug_logger,
        )

        facade_with_debug.on_new_task()

        # Verifica que o logger foi chamado
        mock_debug_logger.assert_called_once()
        call_msg = mock_debug_logger.call_args[0][0]
        assert "on_new_task" in call_msg

    @patch("src.modules.hub.views.hub_dashboard_facade.handle_card_clients_click")
    def test_todos_callbacks_logam_com_debug(
        self,
        mock_handler,
        mock_parent,
        mock_dashboard_vm,
        mock_dashboard_actions,
        mock_renderer,
        mock_state_manager,
        mock_get_org_id,
        mock_get_user_id,
        mock_get_main_app,
        mock_on_refresh,
    ):
        """Testa que callbacks fazem log quando debug está habilitado."""
        mock_debug_logger = MagicMock()
        facade_with_debug = HubDashboardFacade(
            parent=mock_parent,
            dashboard_vm=mock_dashboard_vm,
            dashboard_actions=mock_dashboard_actions,
            renderer=mock_renderer,
            state_manager=mock_state_manager,
            get_org_id=mock_get_org_id,
            get_user_id=mock_get_user_id,
            get_main_app=mock_get_main_app,
            on_refresh_callback=mock_on_refresh,
            debug_logger=mock_debug_logger,
        )

        facade_with_debug.on_card_clients_click()

        # Verifica que o logger foi chamado
        assert mock_debug_logger.called
        call_msg = mock_debug_logger.call_args[0][0]
        assert "on_card_clients_click" in call_msg
