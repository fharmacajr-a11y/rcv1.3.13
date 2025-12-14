# -*- coding: utf-8 -*-
"""MF-17: Dashboard Renderer - Responsável pela renderização do dashboard.

Este módulo encapsula toda a lógica de renderização do dashboard,
reduzindo a complexidade do HubScreen e melhorando a separação de responsabilidades.

Extraído de hub_screen.py na MF-17 (Dezembro 2025).

Responsabilidades:
- Renderizar estado do dashboard (loading, erro, dados, vazio)
- Atualizar UI do dashboard baseado em DashboardViewState
- Coordenar callbacks de UI (botões, cards, ações)
- NÃO contém lógica de negócio (sem chamadas a services/repos/timers)

Design:
- Usa Protocol para desacoplar do HubScreen concreto
- Recebe callbacks via interface mínima
- Delega renderização visual para HubDashboardView
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    from src.modules.hub.viewmodels.dashboard_vm import DashboardViewState
    from src.modules.hub.views.hub_dashboard_view import HubDashboardView

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)


logger = get_logger(__name__)


class DashboardRenderCallbacks(Protocol):
    """Interface mínima que o renderer precisa da view principal.

    MF-17: Evita acoplamento direto com HubScreen.
    Permite testar o renderer com mocks.
    """

    def get_dashboard_view(self) -> "HubDashboardView":
        """Retorna a instância do HubDashboardView."""
        ...


class HubDashboardRenderer:
    """Responsável por renderizar o dashboard na UI.

    MF-17: Extraído de hub_screen.py para reduzir complexidade.

    Este renderer:
    - Recebe estado do dashboard (DashboardViewState)
    - Atualiza a UI via HubDashboardView
    - Não contém lógica de negócio
    - Foca apenas em renderização visual

    Benefícios:
    - Reduz tamanho do hub_screen.py
    - Melhora testabilidade (pode mockar callbacks)
    - Clarifica responsabilidades
    - Facilita manutenção futura
    """

    def __init__(self, callbacks: DashboardRenderCallbacks) -> None:
        """Inicializa o renderer.

        Args:
            callbacks: Interface com métodos necessários para renderização
        """
        self._callbacks = callbacks
        self._logger = logger

    def render_dashboard(
        self,
        state: "DashboardViewState",
        *,
        on_new_task: Callable[[], None] | None = None,
        on_new_obligation: Callable[[], None] | None = None,
        on_view_all_activity: Callable[[], None] | None = None,
        on_card_clients_click: Callable[[], None] | None = None,
        on_card_pendencias_click: Callable[[], None] | None = None,
        on_card_tarefas_click: Callable[[], None] | None = None,
    ) -> None:
        """Renderiza o estado completo do dashboard.

        MF-17: Método principal de renderização.
        Decide qual renderização aplicar baseado no estado.

        Args:
            state: Estado do DashboardViewModel com snapshot e cards formatados
            on_new_task: Callback para criar nova tarefa
            on_new_obligation: Callback para criar nova obrigação
            on_view_all_activity: Callback para visualizar toda atividade
            on_card_clients_click: Callback para clique no card de clientes
            on_card_pendencias_click: Callback para clique no card de pendências
            on_card_tarefas_click: Callback para clique no card de tarefas
        """
        try:
            self._logger.debug("[HubDashboardRenderer] render_dashboard INICIANDO")
            self._logger.debug(
                f"[HubDashboardRenderer] Estado - error_message: {bool(state.error_message)}, snapshot: {bool(state.snapshot)}"
            )

            # Obter view do dashboard
            dashboard_view = self._callbacks.get_dashboard_view()
            self._logger.debug(f"[HubDashboardRenderer] dashboard_view obtido: {dashboard_view is not None}")

            # Cenário 1: ERRO - mostrar mensagem de erro
            if state.error_message:
                self._logger.error("[HubDashboardRenderer] Dashboard em estado de erro: %s", state.error_message)
                dashboard_view.render_dashboard_error(state.error_message)
                return

            # Cenário 2: VAZIO - mostrar estado vazio
            if not state.snapshot:
                self._logger.warning("[HubDashboardRenderer] Dashboard sem snapshot disponível (estado vazio)")
                dashboard_view.render_empty()
                return

            # Cenário 3: DADOS - renderizar dashboard com snapshot válido
            self._logger.debug("[HubDashboardRenderer] Renderizando dashboard com snapshot válido")
            self._render_dashboard_data(
                dashboard_view,
                state,
                on_new_task=on_new_task,
                on_new_obligation=on_new_obligation,
                on_view_all_activity=on_view_all_activity,
                on_card_clients_click=on_card_clients_click,
                on_card_pendencias_click=on_card_pendencias_click,
                on_card_tarefas_click=on_card_tarefas_click,
            )
            self._logger.debug("[HubDashboardRenderer] render_dashboard CONCLUÍDO")
        except Exception as e:
            self._logger.exception(f"[HubDashboardRenderer] ERRO em render_dashboard: {e}")

    def _render_dashboard_data(
        self,
        dashboard_view: "HubDashboardView",
        state: "DashboardViewState",
        *,
        on_new_task: Callable[[], None] | None = None,
        on_new_obligation: Callable[[], None] | None = None,
        on_view_all_activity: Callable[[], None] | None = None,
        on_card_clients_click: Callable[[], None] | None = None,
        on_card_pendencias_click: Callable[[], None] | None = None,
        on_card_tarefas_click: Callable[[], None] | None = None,
    ) -> None:
        """Renderiza dados do dashboard (cards, atividades).

        MF-17: Delega para HubDashboardView.render_dashboard_data.

        Args:
            dashboard_view: Instância do HubDashboardView
            state: DashboardViewState com dados formatados
            on_new_task: Callback para criar nova tarefa
            on_new_obligation: Callback para criar nova obrigação
            on_view_all_activity: Callback para visualizar toda atividade
            on_card_clients_click: Callback para clique no card de clientes
            on_card_pendencias_click: Callback para clique no card de pendências
            on_card_tarefas_click: Callback para clique no card de tarefas
        """
        self._logger.debug("[HubDashboardRenderer] Chamando dashboard_view.render_dashboard_data...")
        # Delegar para HubDashboardView
        dashboard_view.render_dashboard_data(
            state,
            on_new_task=on_new_task,
            on_new_obligation=on_new_obligation,
            on_view_all_activity=on_view_all_activity,
            on_card_clients_click=lambda s: on_card_clients_click() if on_card_clients_click else None,
            on_card_pendencias_click=lambda s: on_card_pendencias_click() if on_card_pendencias_click else None,
            on_card_tarefas_click=lambda s: on_card_tarefas_click() if on_card_tarefas_click else None,
        )

    def render_loading(self) -> None:
        """Renderiza estado de loading no dashboard.

        MF-17: Wrapper para dashboard_view.render_loading.
        """
        dashboard_view = self._callbacks.get_dashboard_view()
        dashboard_view.render_loading()

    def render_error(self, message: str | None = None) -> None:
        """Renderiza estado de erro no dashboard.

        MF-17: Wrapper para dashboard_view.render_error.

        Args:
            message: Mensagem de erro opcional
        """
        dashboard_view = self._callbacks.get_dashboard_view()
        dashboard_view.render_error(message)

    def render_empty(self) -> None:
        """Renderiza estado vazio no dashboard.

        MF-17: Wrapper para dashboard_view.render_empty.
        """
        dashboard_view = self._callbacks.get_dashboard_view()
        dashboard_view.render_empty()
