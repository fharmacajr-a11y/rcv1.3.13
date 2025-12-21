# -*- coding: utf-8 -*-
# ruff: noqa: E731
"""Testes unitários para HubDashboardRenderer (MF-48).

Meta: >=95% coverage (ideal 100%).
Estratégia: testes headless com mocks, cobertura completa de render_dashboard e branches.
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_dashboard_view():
    """Mock do HubDashboardView."""
    view = MagicMock()
    view.render_dashboard_error = MagicMock()
    view.render_dashboard_data = MagicMock()
    view.render_loading = MagicMock()
    view.render_error = MagicMock()
    view.render_empty = MagicMock()
    return view


@pytest.fixture
def mock_callbacks(mock_dashboard_view):
    """Mock de DashboardRenderCallbacks que retorna mock_dashboard_view."""
    callbacks = MagicMock()
    callbacks.get_dashboard_view.return_value = mock_dashboard_view
    return callbacks


@pytest.fixture
def renderer(mock_callbacks):
    """Instância de HubDashboardRenderer com callbacks mock."""
    from src.modules.hub.views.hub_dashboard_renderer import HubDashboardRenderer

    return HubDashboardRenderer(callbacks=mock_callbacks)


def make_state(error_message: str | None = None, snapshot: Any = None) -> Any:
    """Helper para criar DashboardViewState usando SimpleNamespace.

    Nota: SimpleNamespace é usado como mock estrutural (duck typing).
    """
    return SimpleNamespace(error_message=error_message, snapshot=snapshot)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: render_dashboard - Roteamento de Cenários
# ══════════════════════════════════════════════════════════════════════════════


def test_render_dashboard_with_error_message(renderer, mock_dashboard_view):
    """Deve chamar render_dashboard_error quando state.error_message está presente."""
    state = make_state(error_message="Erro crítico", snapshot=None)

    renderer.render_dashboard(state)

    mock_dashboard_view.render_dashboard_error.assert_called_once_with("Erro crítico")
    mock_dashboard_view.render_empty.assert_not_called()
    mock_dashboard_view.render_dashboard_data.assert_not_called()


def test_render_dashboard_with_error_message_ignores_snapshot(renderer, mock_dashboard_view):
    """Erro tem prioridade: mesmo com snapshot, mostra erro."""
    snapshot = {"clientes": 10}
    state = make_state(error_message="Falha", snapshot=snapshot)

    renderer.render_dashboard(state)

    mock_dashboard_view.render_dashboard_error.assert_called_once_with("Falha")
    mock_dashboard_view.render_dashboard_data.assert_not_called()


def test_render_dashboard_empty_when_no_snapshot(renderer, mock_dashboard_view):
    """Deve chamar render_empty quando state.snapshot é None."""
    state = make_state(error_message=None, snapshot=None)

    renderer.render_dashboard(state)

    mock_dashboard_view.render_empty.assert_called_once()
    mock_dashboard_view.render_dashboard_error.assert_not_called()
    mock_dashboard_view.render_dashboard_data.assert_not_called()


def test_render_dashboard_with_data_calls_render_dashboard_data(renderer, mock_dashboard_view):
    """Deve chamar _render_dashboard_data quando snapshot está presente."""
    snapshot = {"clientes": 5, "tarefas": 3}
    state = make_state(error_message=None, snapshot=snapshot)

    renderer.render_dashboard(state)

    # Verifica que render_dashboard_data foi chamado
    mock_dashboard_view.render_dashboard_data.assert_called_once()
    # Verifica que state foi passado como primeiro argumento
    call_args = mock_dashboard_view.render_dashboard_data.call_args
    assert call_args[0][0] is state


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: _render_dashboard_data - Lambdas dos Cards
# ══════════════════════════════════════════════════════════════════════════════


def test_render_dashboard_data_with_all_callbacks(renderer, mock_dashboard_view):
    """Lambdas nos cards devem chamar os callbacks originais."""
    snapshot = {"clientes": 10}
    state = make_state(error_message=None, snapshot=snapshot)

    # Callbacks espias
    on_card_clients = MagicMock()
    on_card_pendencias = MagicMock()
    on_card_tarefas = MagicMock()

    renderer.render_dashboard(
        state,
        on_card_clients_click=on_card_clients,
        on_card_pendencias_click=on_card_pendencias,
        on_card_tarefas_click=on_card_tarefas,
    )

    # Capturar kwargs passados para render_dashboard_data
    call_kwargs = mock_dashboard_view.render_dashboard_data.call_args.kwargs

    # Executar as lambdas capturadas
    call_kwargs["on_card_clients_click"]("ignored")
    call_kwargs["on_card_pendencias_click"]("ignored")
    call_kwargs["on_card_tarefas_click"]("ignored")

    # Verificar que callbacks originais foram chamados
    on_card_clients.assert_called_once()
    on_card_pendencias.assert_called_once()
    on_card_tarefas.assert_called_once()


def test_render_dashboard_data_with_none_callbacks(renderer, mock_dashboard_view):
    """Lambdas com callback=None não devem explodir."""
    snapshot = {"clientes": 10}
    state = make_state(error_message=None, snapshot=snapshot)

    renderer.render_dashboard(
        state,
        on_card_clients_click=None,
        on_card_pendencias_click=None,
        on_card_tarefas_click=None,
    )

    # Capturar kwargs
    call_kwargs = mock_dashboard_view.render_dashboard_data.call_args.kwargs

    # Executar lambdas com callback=None (não deve explodir)
    result_clients = call_kwargs["on_card_clients_click"]("ignored")
    result_pendencias = call_kwargs["on_card_pendencias_click"]("ignored")
    result_tarefas = call_kwargs["on_card_tarefas_click"]("ignored")

    # Deve retornar None
    assert result_clients is None
    assert result_pendencias is None
    assert result_tarefas is None


def test_render_dashboard_data_passes_all_callbacks(renderer, mock_dashboard_view):
    """Deve passar todos os callbacks (on_new_task, on_new_obligation, on_view_all_activity)."""
    snapshot = {"tarefas": 5}
    state = make_state(error_message=None, snapshot=snapshot)

    on_new_task = MagicMock()
    on_new_obligation = MagicMock()
    on_view_all_activity = MagicMock()

    renderer.render_dashboard(
        state,
        on_new_task=on_new_task,
        on_new_obligation=on_new_obligation,
        on_view_all_activity=on_view_all_activity,
    )

    call_kwargs = mock_dashboard_view.render_dashboard_data.call_args.kwargs

    assert call_kwargs["on_new_task"] is on_new_task
    assert call_kwargs["on_new_obligation"] is on_new_obligation
    assert call_kwargs["on_view_all_activity"] is on_view_all_activity


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: Wrappers Simples
# ══════════════════════════════════════════════════════════════════════════════


def test_render_loading(renderer, mock_dashboard_view):
    """render_loading deve delegar para dashboard_view.render_loading."""
    renderer.render_loading()

    mock_dashboard_view.render_loading.assert_called_once()


def test_render_error(renderer, mock_dashboard_view):
    """render_error deve delegar para dashboard_view.render_error."""
    renderer.render_error("Mensagem de erro")

    mock_dashboard_view.render_error.assert_called_once_with("Mensagem de erro")


def test_render_error_without_message(renderer, mock_dashboard_view):
    """render_error sem mensagem deve passar None."""
    renderer.render_error(None)

    mock_dashboard_view.render_error.assert_called_once_with(None)


def test_render_empty(renderer, mock_dashboard_view):
    """render_empty deve delegar para dashboard_view.render_empty."""
    renderer.render_empty()

    mock_dashboard_view.render_empty.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: Exception Safety
# ══════════════════════════════════════════════════════════════════════════════


def test_render_dashboard_handles_exception_from_get_dashboard_view(mock_callbacks):
    """render_dashboard não deve propagar exceção se get_dashboard_view falhar."""
    from src.modules.hub.views.hub_dashboard_renderer import HubDashboardRenderer

    mock_callbacks.get_dashboard_view.side_effect = RuntimeError("View não disponível")

    renderer = HubDashboardRenderer(callbacks=mock_callbacks)
    renderer._logger = MagicMock()

    state = make_state(error_message=None, snapshot={"clientes": 5})

    # Não deve propagar a exceção
    renderer.render_dashboard(state)

    # Deve ter logado a exceção
    renderer._logger.exception.assert_called_once()
    assert "ERRO em render_dashboard" in str(renderer._logger.exception.call_args)


def test_render_dashboard_handles_exception_from_render_dashboard_data(mock_callbacks, mock_dashboard_view):
    """render_dashboard não deve propagar exceção se render_dashboard_data falhar."""
    from src.modules.hub.views.hub_dashboard_renderer import HubDashboardRenderer

    mock_dashboard_view.render_dashboard_data.side_effect = ValueError("Erro interno")
    mock_callbacks.get_dashboard_view.return_value = mock_dashboard_view

    renderer = HubDashboardRenderer(callbacks=mock_callbacks)
    renderer._logger = MagicMock()

    state = make_state(error_message=None, snapshot={"tarefas": 10})

    # Não deve propagar a exceção
    renderer.render_dashboard(state)

    # Deve ter logado a exceção
    renderer._logger.exception.assert_called_once()
    assert "ERRO em render_dashboard" in str(renderer._logger.exception.call_args)


def test_render_dashboard_handles_exception_from_render_dashboard_error(mock_callbacks, mock_dashboard_view):
    """render_dashboard não deve propagar exceção se render_dashboard_error falhar."""
    from src.modules.hub.views.hub_dashboard_renderer import HubDashboardRenderer

    mock_dashboard_view.render_dashboard_error.side_effect = Exception("Erro ao renderizar erro")
    mock_callbacks.get_dashboard_view.return_value = mock_dashboard_view

    renderer = HubDashboardRenderer(callbacks=mock_callbacks)
    renderer._logger = MagicMock()

    state = make_state(error_message="Erro original", snapshot=None)

    # Não deve propagar a exceção
    renderer.render_dashboard(state)

    # Deve ter logado a exceção
    renderer._logger.exception.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: Fallback do Logger (import branch)
# ══════════════════════════════════════════════════════════════════════════════


def test_fallback_logger_when_src_core_logger_fails():
    """Deve usar logging.getLogger quando src.core.logger falha."""
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "src.core.logger":
            raise ImportError("Forçando falha no import")
        return original_import(name, *args, **kwargs)

    # Remover módulo do cache
    if "src.modules.hub.views.hub_dashboard_renderer" in sys.modules:
        del sys.modules["src.modules.hub.views.hub_dashboard_renderer"]

    # Aplicar patch e recarregar módulo
    with patch("builtins.__import__", side_effect=mock_import):
        import src.modules.hub.views.hub_dashboard_renderer as reloaded_module

        importlib.reload(reloaded_module)

        # Testar get_logger
        logger = reloaded_module.get_logger("test_module")

        # Deve retornar um logger do logging padrão
        assert logger.name == "test_module"
        assert hasattr(logger, "debug")
        assert hasattr(logger, "error")

    # Restaurar módulo original
    importlib.reload(reloaded_module)
