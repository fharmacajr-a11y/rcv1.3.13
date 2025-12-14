# -*- coding: utf-8 -*-
"""Testes unitários para HubDashboardRenderer (MF-17).

Valida:
- Renderização de estados do dashboard (loading, erro, dados, vazio)
- Delegação correta para HubDashboardView
- Callbacks de UI são conectados corretamente
- Protocol de callbacks funciona (desacoplamento)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.modules.hub.dashboard_service import DashboardSnapshot
from src.modules.hub.viewmodels.dashboard_vm import DashboardViewState
from src.modules.hub.views.hub_dashboard_renderer import (
    HubDashboardRenderer,
    DashboardRenderCallbacks,
)


class TestDashboardRenderCallbacks:
    """Testes para o Protocol de callbacks."""

    def test_can_create_mock_callbacks(self):
        """Deve permitir criar mock de callbacks para testes."""
        # Mock que implementa o Protocol
        mock_callbacks = MagicMock(spec=DashboardRenderCallbacks)
        mock_callbacks.get_dashboard_view.return_value = MagicMock()

        # Não deve falhar
        assert mock_callbacks is not None
        assert hasattr(mock_callbacks, "get_dashboard_view")


class TestHubDashboardRenderer:
    """Testes para HubDashboardRenderer."""

    @pytest.fixture
    def mock_dashboard_view(self):
        """Cria mock de HubDashboardView."""
        view = MagicMock()
        view.render_dashboard_error = MagicMock()
        view.render_dashboard_data = MagicMock()
        view.render_loading = MagicMock()
        view.render_error = MagicMock()
        view.render_empty = MagicMock()
        return view

    @pytest.fixture
    def mock_callbacks(self, mock_dashboard_view):
        """Cria mock de callbacks que retorna o mock da view."""
        callbacks = MagicMock()
        callbacks.get_dashboard_view.return_value = mock_dashboard_view
        return callbacks

    @pytest.fixture
    def renderer(self, mock_callbacks):
        """Cria instância do renderer com callbacks mock."""
        return HubDashboardRenderer(callbacks=mock_callbacks)

    def test_creates_renderer_with_callbacks(self, mock_callbacks):
        """Deve criar renderer com callbacks."""
        renderer = HubDashboardRenderer(callbacks=mock_callbacks)

        assert renderer is not None
        assert renderer._callbacks == mock_callbacks

    def test_render_dashboard_with_error_state(self, renderer, mock_dashboard_view):
        """Deve renderizar estado de erro."""
        state = DashboardViewState(
            error_message="Erro ao carregar dashboard",
            snapshot=None,
        )

        renderer.render_dashboard(state)

        # Deve ter chamado render_dashboard_error
        mock_dashboard_view.render_dashboard_error.assert_called_once_with("Erro ao carregar dashboard")
        # Não deve ter chamado render_dashboard_data
        mock_dashboard_view.render_dashboard_data.assert_not_called()

    def test_render_dashboard_with_no_snapshot_skips(self, renderer, mock_dashboard_view):
        """Deve pular renderização se não houver snapshot."""
        state = DashboardViewState(
            error_message=None,
            snapshot=None,
        )

        renderer.render_dashboard(state)

        # Não deve ter chamado métodos de renderização
        mock_dashboard_view.render_dashboard_error.assert_not_called()
        mock_dashboard_view.render_dashboard_data.assert_not_called()

    def test_render_dashboard_with_valid_data(self, renderer, mock_dashboard_view):
        """Deve renderizar dados do dashboard com snapshot válido."""
        snapshot = DashboardSnapshot(active_clients=10, pending_obligations=5)
        state = DashboardViewState(
            error_message=None,
            snapshot=snapshot,
        )

        # Callbacks mock
        on_new_task = MagicMock()
        on_new_obligation = MagicMock()

        renderer.render_dashboard(
            state,
            on_new_task=on_new_task,
            on_new_obligation=on_new_obligation,
        )

        # Deve ter chamado render_dashboard_data
        mock_dashboard_view.render_dashboard_data.assert_called_once()
        call_args = mock_dashboard_view.render_dashboard_data.call_args

        # Verificar state passado
        assert call_args[0][0] == state
        # Verificar callbacks
        assert call_args[1]["on_new_task"] == on_new_task
        assert call_args[1]["on_new_obligation"] == on_new_obligation

    def test_render_dashboard_passes_all_callbacks(self, renderer, mock_dashboard_view):
        """Deve passar todos os callbacks para a view."""
        snapshot = DashboardSnapshot()
        state = DashboardViewState(snapshot=snapshot)

        # Criar todos os callbacks
        callbacks = {
            "on_new_task": MagicMock(),
            "on_new_obligation": MagicMock(),
            "on_view_all_activity": MagicMock(),
            "on_card_clients_click": MagicMock(),
            "on_card_pendencias_click": MagicMock(),
            "on_card_tarefas_click": MagicMock(),
        }

        renderer.render_dashboard(state, **callbacks)

        # Verificar que view recebeu os callbacks
        call_kwargs = mock_dashboard_view.render_dashboard_data.call_args[1]
        assert call_kwargs["on_new_task"] == callbacks["on_new_task"]
        assert call_kwargs["on_new_obligation"] == callbacks["on_new_obligation"]
        assert call_kwargs["on_view_all_activity"] == callbacks["on_view_all_activity"]

    def test_render_loading_delegates_to_view(self, renderer, mock_dashboard_view):
        """Deve delegar render_loading para a view."""
        renderer.render_loading()

        mock_dashboard_view.render_loading.assert_called_once()

    def test_render_error_delegates_to_view(self, renderer, mock_dashboard_view):
        """Deve delegar render_error para a view."""
        renderer.render_error("Erro de teste")

        mock_dashboard_view.render_error.assert_called_once_with("Erro de teste")

    def test_render_empty_delegates_to_view(self, renderer, mock_dashboard_view):
        """Deve delegar render_empty para a view."""
        renderer.render_empty()

        mock_dashboard_view.render_empty.assert_called_once()

    def test_callbacks_are_optional(self, renderer, mock_dashboard_view):
        """Callbacks devem ser opcionais (pode passar None)."""
        snapshot = DashboardSnapshot()
        state = DashboardViewState(snapshot=snapshot)

        # Não deve lançar exceção com callbacks None
        renderer.render_dashboard(
            state,
            on_new_task=None,
            on_new_obligation=None,
            on_view_all_activity=None,
        )

        # Deve ter chamado a view
        mock_dashboard_view.render_dashboard_data.assert_called_once()

    def test_error_takes_precedence_over_snapshot(self, renderer, mock_dashboard_view):
        """Erro deve ter precedência sobre snapshot na renderização."""
        state = DashboardViewState(
            error_message="Erro crítico",
            snapshot=DashboardSnapshot(),  # Tem snapshot mas também erro
        )

        renderer.render_dashboard(state)

        # Deve renderizar erro, não dados
        mock_dashboard_view.render_dashboard_error.assert_called_once()
        mock_dashboard_view.render_dashboard_data.assert_not_called()
