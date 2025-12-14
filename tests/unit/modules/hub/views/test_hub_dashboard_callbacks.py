# -*- coding: utf-8 -*-
"""Testes unitários para hub_dashboard_callbacks.py - callbacks de dashboard."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.hub.views.hub_dashboard_callbacks import (
    handle_client_picked_for_obligation,
    handle_new_obligation_click,
    handle_new_task_click,
    handle_view_all_activity_click,
)


class TestHandleNewTaskClick:
    """Testes para callback de criação de nova tarefa."""

    @pytest.fixture
    def mock_parent(self):
        """Mock do widget pai."""
        return MagicMock()

    @pytest.fixture
    def get_org_id(self):
        """Mock de getter de org_id."""
        return MagicMock(return_value="org-123")

    @pytest.fixture
    def get_user_id(self):
        """Mock de getter de user_id."""
        return MagicMock(return_value="user-456")

    @pytest.fixture
    def on_success_callback(self):
        """Mock de callback de sucesso."""
        return MagicMock()

    @patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
    def test_shows_warning_if_no_org_id(
        self,
        mock_messagebox,
        mock_parent,
        get_user_id,
        on_success_callback,
    ):
        """Deve mostrar warning se org_id não estiver disponível."""
        get_org_id = MagicMock(return_value=None)  # Sem org_id

        handle_new_task_click(
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            on_success_callback=on_success_callback,
        )

        # Deve ter mostrado warning
        mock_messagebox.showwarning.assert_called_once()
        assert "Autenticação Necessária" in mock_messagebox.showwarning.call_args[0][0]

        # Callback não deve ter sido chamado
        on_success_callback.assert_not_called()

    @patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
    def test_shows_warning_if_no_user_id(
        self,
        mock_messagebox,
        mock_parent,
        get_org_id,
        on_success_callback,
    ):
        """Deve mostrar warning se user_id não estiver disponível."""
        get_user_id = MagicMock(return_value=None)  # Sem user_id

        handle_new_task_click(
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            on_success_callback=on_success_callback,
        )

        # Deve ter mostrado warning
        mock_messagebox.showwarning.assert_called_once()
        assert "Autenticação Necessária" in mock_messagebox.showwarning.call_args[0][0]

    @patch("src.modules.tasks.views.NovaTarefaDialog")
    @patch("data.supabase_repo.list_clients_for_picker")
    def test_opens_dialog_with_valid_credentials(
        self,
        mock_list_clients,
        mock_dialog_class,
        mock_parent,
        get_org_id,
        get_user_id,
        on_success_callback,
    ):
        """Deve abrir diálogo de nova tarefa com credenciais válidas."""
        # Setup mocks
        mock_clients = [{"id": 1, "nome": "Cliente A"}]
        mock_list_clients.return_value = mock_clients
        mock_dialog = MagicMock()
        mock_dialog_class.return_value = mock_dialog

        handle_new_task_click(
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            on_success_callback=on_success_callback,
        )

        # Verificar que diálogo foi criado
        mock_dialog_class.assert_called_once_with(
            parent=mock_parent,
            org_id="org-123",
            user_id="user-456",
            on_success=on_success_callback,
            clients=mock_clients,
        )

        # Verificar que diálogo foi exibido
        mock_dialog.deiconify.assert_called_once()

    @patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
    @patch("data.supabase_repo.list_clients_for_picker")
    def test_handles_error_loading_clients_gracefully(
        self,
        mock_list_clients,
        mock_messagebox,
        mock_parent,
        get_org_id,
        get_user_id,
        on_success_callback,
    ):
        """Deve lidar com erro ao carregar clientes sem quebrar."""
        # Simular erro ao carregar clientes
        mock_list_clients.side_effect = Exception("DB Error")

        with patch("src.modules.tasks.views.NovaTarefaDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog_class.return_value = mock_dialog

            handle_new_task_click(
                parent=mock_parent,
                get_org_id=get_org_id,
                get_user_id=get_user_id,
                on_success_callback=on_success_callback,
            )

            # Diálogo deve ser criado mesmo com erro ao carregar clientes
            # (com lista vazia)
            assert mock_dialog_class.called
            call_kwargs = mock_dialog_class.call_args.kwargs
            assert call_kwargs["clients"] == []


class TestHandleNewObligationClick:
    """Testes para callback de criação de nova obrigação."""

    @pytest.fixture
    def mock_parent(self):
        return MagicMock()

    @pytest.fixture
    def get_org_id(self):
        return MagicMock(return_value="org-123")

    @pytest.fixture
    def get_user_id(self):
        return MagicMock(return_value="user-456")

    @pytest.fixture
    def get_main_app(self):
        return MagicMock(return_value=MagicMock())

    @pytest.fixture
    def on_client_picked(self):
        return MagicMock()

    @patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
    def test_shows_warning_if_no_org_id(
        self,
        mock_messagebox,
        mock_parent,
        get_user_id,
        get_main_app,
        on_client_picked,
    ):
        """Deve mostrar warning se org_id não estiver disponível."""
        get_org_id = MagicMock(return_value=None)

        handle_new_obligation_click(
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_client_picked=on_client_picked,
        )

        mock_messagebox.showwarning.assert_called_once()
        assert "Autenticação Necessária" in mock_messagebox.showwarning.call_args[0][0]

    @patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
    def test_shows_warning_if_no_user_id(
        self,
        mock_messagebox,
        mock_parent,
        get_org_id,
        get_main_app,
        on_client_picked,
    ):
        """Deve mostrar warning se user_id não estiver disponível."""
        get_user_id = MagicMock(return_value=None)

        handle_new_obligation_click(
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_client_picked=on_client_picked,
        )

        mock_messagebox.showwarning.assert_called_once()

    @patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
    def test_shows_warning_if_no_main_app(
        self,
        mock_messagebox,
        mock_parent,
        get_org_id,
        get_user_id,
        on_client_picked,
    ):
        """Deve mostrar warning se main_app não estiver disponível."""
        get_main_app = MagicMock(return_value=None)

        handle_new_obligation_click(
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_client_picked=on_client_picked,
        )

        mock_messagebox.showwarning.assert_called_once()
        assert "Aplicação principal não encontrada" in mock_messagebox.showwarning.call_args[0][1]

    @patch("src.modules.main_window.controller.start_client_pick_mode")
    @patch("src.modules.main_window.controller.navigate_to")
    def test_starts_client_pick_mode_with_valid_data(
        self,
        mock_navigate,
        mock_pick_mode,
        mock_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_client_picked,
    ):
        """Deve iniciar modo de seleção de cliente com dados válidos."""
        _ = get_main_app()  # Ensure app is initialized

        handle_new_obligation_click(
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_client_picked=on_client_picked,
        )

        # Verificar que start_client_pick_mode foi chamado
        mock_pick_mode.assert_called_once()
        call_kwargs = mock_pick_mode.call_args.kwargs

        assert call_kwargs["on_client_picked"] == on_client_picked
        assert "Modo seleção" in call_kwargs["banner_text"]
        assert callable(call_kwargs["return_to"])


class TestHandleViewAllActivityClick:
    """Testes para callback de visualização de atividades."""

    @patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
    def test_shows_info_message(self, mock_messagebox):
        """Deve mostrar mensagem informativa (feature em desenvolvimento)."""
        mock_parent = MagicMock()

        handle_view_all_activity_click(parent=mock_parent)

        # Deve mostrar info
        mock_messagebox.showinfo.assert_called_once()
        assert "Em Desenvolvimento" in mock_messagebox.showinfo.call_args[0][0]


class TestHandleClientPickedForObligation:
    """Testes para callback quando cliente é selecionado para obrigação."""

    @pytest.fixture
    def client_data(self):
        return {
            "id": 123,
            "razao_social": "Cliente Teste LTDA",
        }

    @pytest.fixture
    def mock_parent(self):
        parent = MagicMock()
        parent.winfo_toplevel.return_value = MagicMock()
        return parent

    @pytest.fixture
    def get_org_id(self):
        return MagicMock(return_value="org-123")

    @pytest.fixture
    def get_user_id(self):
        return MagicMock(return_value="user-456")

    @pytest.fixture
    def get_main_app(self):
        return MagicMock(return_value=MagicMock())

    @pytest.fixture
    def on_refresh_callback(self):
        return MagicMock()

    def test_returns_early_if_no_org_id(
        self,
        client_data,
        mock_parent,
        get_user_id,
        get_main_app,
        on_refresh_callback,
    ):
        """Deve retornar cedo se org_id não estiver disponível."""
        get_org_id = MagicMock(return_value=None)

        # Não deve gerar exceção
        handle_client_picked_for_obligation(
            client_data=client_data,
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_refresh_callback=on_refresh_callback,
        )

        # Callback não deve ser chamado
        on_refresh_callback.assert_not_called()

    def test_returns_early_if_no_user_id(
        self,
        client_data,
        mock_parent,
        get_org_id,
        get_main_app,
        on_refresh_callback,
    ):
        """Deve retornar cedo se user_id não estiver disponível."""
        get_user_id = MagicMock(return_value=None)

        handle_client_picked_for_obligation(
            client_data=client_data,
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_refresh_callback=on_refresh_callback,
        )

        on_refresh_callback.assert_not_called()

    def test_returns_early_if_no_client_id(
        self,
        mock_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh_callback,
    ):
        """Deve retornar cedo se client_data não contém ID."""
        client_data = {"nome": "Sem ID"}  # Sem "id"

        handle_client_picked_for_obligation(
            client_data=client_data,
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_refresh_callback=on_refresh_callback,
        )

        on_refresh_callback.assert_not_called()

    @patch("src.modules.clientes.views.client_obligations_window.show_client_obligations_window")
    @patch("src.modules.main_window.controller.navigate_to")
    def test_opens_obligations_window_with_valid_data(
        self,
        mock_navigate,
        mock_show_window,
        client_data,
        mock_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh_callback,
    ):
        """Deve abrir janela de obrigações com dados válidos."""
        mock_app = get_main_app()

        handle_client_picked_for_obligation(
            client_data=client_data,
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_refresh_callback=on_refresh_callback,
        )

        # Verificar navegação para hub
        mock_navigate.assert_called_once_with(mock_app, "hub")

        # Verificar abertura da janela de obrigações
        mock_show_window.assert_called_once()
        call_kwargs = mock_show_window.call_args.kwargs

        assert call_kwargs["org_id"] == "org-123"
        assert call_kwargs["created_by"] == "user-456"
        assert call_kwargs["client_id"] == 123
        assert call_kwargs["client_name"] == "Cliente Teste LTDA"
        assert call_kwargs["on_refresh_hub"] == on_refresh_callback

    @patch("src.modules.clientes.views.client_obligations_window.show_client_obligations_window")
    @patch("src.modules.main_window.controller.navigate_to")
    def test_converts_string_client_id_to_int(
        self,
        mock_navigate,
        mock_show_window,
        mock_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh_callback,
    ):
        """Deve converter client_id de string para int."""
        client_data = {"id": "456", "nome": "Cliente"}  # ID como string

        handle_client_picked_for_obligation(
            client_data=client_data,
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_refresh_callback=on_refresh_callback,
        )

        # Verificar que ID foi convertido para int
        call_kwargs = mock_show_window.call_args.kwargs
        assert call_kwargs["client_id"] == 456
        assert isinstance(call_kwargs["client_id"], int)

    def test_handles_invalid_client_id_string(
        self,
        mock_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh_callback,
    ):
        """Deve lidar com client_id string inválido (não conversível)."""
        client_data = {"id": "invalid", "nome": "Cliente"}

        # Não deve gerar exceção descontrolada
        handle_client_picked_for_obligation(
            client_data=client_data,
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_refresh_callback=on_refresh_callback,
        )

    @patch("src.modules.clientes.views.client_obligations_window.show_client_obligations_window")
    @patch("src.modules.main_window.controller.navigate_to")
    def test_uses_fallback_client_name(
        self,
        mock_navigate,
        mock_show_window,
        mock_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh_callback,
    ):
        """Deve usar nome fallback se razao_social e nome não disponíveis."""
        client_data = {"id": 789}  # Sem nome

        handle_client_picked_for_obligation(
            client_data=client_data,
            parent=mock_parent,
            get_org_id=get_org_id,
            get_user_id=get_user_id,
            get_main_app=get_main_app,
            on_refresh_callback=on_refresh_callback,
        )

        call_kwargs = mock_show_window.call_args.kwargs
        assert call_kwargs["client_name"] == "Cliente 789"
