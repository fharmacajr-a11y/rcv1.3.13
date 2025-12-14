# -*- coding: utf-8 -*-
"""MF-22: Dashboard Facade para HubScreen.

Este módulo centraliza todos os callbacks de dashboard (_on_*) do HubScreen,
transformando-o em um thin orchestrator.

Responsabilidades:
- Coordenar handlers de dashboard (handle_new_task, handle_card_*, etc.)
- Integrar com HubDashboardRenderer para atualizações de UI
- Gerenciar estado via HubStateManager
- Manter API de callbacks consistente

Benefícios:
- Reduz linhas em hub_screen.py (~50-70 linhas removidas)
- Centraliza lógica de dashboard em uma façade
- Facilita testes de dashboard isoladamente
- Melhora separação de concerns
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    pass

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


from src.modules.hub.views.hub_dashboard_handlers import (
    handle_new_task_click_v2,
    handle_new_obligation_click_v2,
    handle_view_all_activity_click_v2,
    handle_card_clients_click,
    handle_card_pendencias_click,
    handle_card_tarefas_click,
    handle_client_picked_for_obligation_v2,
)

logger = get_logger(__name__)


class HubDashboardFacade:
    """MF-22: Centraliza interações de dashboard do HubScreen.

    Esta façade encapsula toda a lógica de callbacks de dashboard,
    delegando para handlers especializados e coordenando com renderer.

    Args:
        parent: Widget pai (HubScreen) para posicionar diálogos
        dashboard_vm: ViewModel de dashboard (para acessar state)
        dashboard_actions: Controller de ações de dashboard
        renderer: HubDashboardRenderer para atualizações de UI
        state_manager: HubStateManager para mutações de estado
        get_org_id: Callable que retorna org_id atual
        get_user_id: Callable que retorna user_id atual
        get_main_app: Callable que retorna app principal
        on_refresh_callback: Callback para refresh após operações (ex: _load_dashboard)
        debug_logger: Logger opcional para debug
    """

    def __init__(
        self,
        parent: Any,
        dashboard_vm: Any,
        dashboard_actions: Any,
        renderer: Any,
        state_manager: Any,
        get_org_id: Callable[[], Optional[str]],
        get_user_id: Callable[[], Optional[str]],
        get_main_app: Callable[[], Any],
        on_refresh_callback: Callable[[], None],
        debug_logger: Optional[Any] = None,
    ) -> None:
        """Inicializa façade de dashboard.

        Args:
            parent: Widget pai (HubScreen)
            dashboard_vm: DashboardViewModel
            dashboard_actions: DashboardActionController
            renderer: HubDashboardRenderer
            state_manager: HubStateManager
            get_org_id: Callable para obter org_id
            get_user_id: Callable para obter user_id
            get_main_app: Callable para obter app principal
            on_refresh_callback: Callback de refresh (ex: _load_dashboard)
            debug_logger: Logger opcional para debug
        """
        self._parent = parent
        self._dashboard_vm = dashboard_vm
        self._dashboard_actions = dashboard_actions
        self._renderer = renderer
        self._state = state_manager
        self._get_org_id = get_org_id
        self._get_user_id = get_user_id
        self._get_main_app = get_main_app
        self._on_refresh = on_refresh_callback
        self._debug_logger = debug_logger

    # ==============================================================================
    # CALLBACKS DE AÇÕES DO DASHBOARD
    # ==============================================================================

    def on_new_task(self) -> None:
        """Abre diálogo para criar nova tarefa (MF-13, MF-22)."""
        if self._debug_logger:
            self._debug_logger("DashboardFacade: on_new_task")

        handle_new_task_click_v2(
            parent=self._parent,
            get_org_id=self._get_org_id,
            get_user_id=self._get_user_id,
            on_success_callback=self._on_refresh,
        )

    def on_new_obligation(self) -> None:
        """Abre seleção de Clientes e janela de obrigações (MF-13, MF-22)."""
        if self._debug_logger:
            self._debug_logger("DashboardFacade: on_new_obligation")

        # Salvar IDs para uso no callback (compatibilidade com lógica existente)
        org_id = self._get_org_id()
        user_id = self._get_user_id()

        if org_id and user_id:
            # Armazenar no parent para callback posterior
            self._parent._pending_obligation_org_id = org_id
            self._parent._pending_obligation_user_id = user_id

        handle_new_obligation_click_v2(
            parent=self._parent,
            get_org_id=self._get_org_id,
            get_user_id=self._get_user_id,
            get_main_app=self._get_main_app,
            on_client_picked=self.on_client_picked_for_obligation,
        )

    def on_view_all_activity(self) -> None:
        """Abre visualização completa da atividade da equipe (MF-13, MF-22)."""
        if self._debug_logger:
            self._debug_logger("DashboardFacade: on_view_all_activity")

        handle_view_all_activity_click_v2(parent=self._parent)

    # ==============================================================================
    # CALLBACKS DE CARDS
    # ==============================================================================

    def on_card_clients_click(self) -> None:
        """Handler de clique no card 'Clientes Ativos' (MF-13, MF-22)."""
        if self._debug_logger:
            self._debug_logger("DashboardFacade: on_card_clients_click")

        handle_card_clients_click(
            dashboard_vm=self._dashboard_vm,
            dashboard_actions=self._dashboard_actions,
            parent=self._parent,
        )

    def on_card_pendencias_click(self) -> None:
        """Handler de clique no card 'Pendências Regulatórias' (MF-13, MF-22)."""
        if self._debug_logger:
            self._debug_logger("DashboardFacade: on_card_pendencias_click")

        handle_card_pendencias_click(
            dashboard_vm=self._dashboard_vm,
            dashboard_actions=self._dashboard_actions,
            parent=self._parent,
        )

    def on_card_tarefas_click(self) -> None:
        """Handler de clique no card 'Tarefas Hoje' (MF-13, MF-22)."""
        if self._debug_logger:
            self._debug_logger("DashboardFacade: on_card_tarefas_click")

        handle_card_tarefas_click(
            dashboard_vm=self._dashboard_vm,
            dashboard_actions=self._dashboard_actions,
            parent=self._parent,
        )

    # ==============================================================================
    # CALLBACK DE CLIENTE SELECIONADO
    # ==============================================================================

    def on_client_picked_for_obligation(self, client_data: dict) -> None:
        """Callback quando cliente é selecionado para criar obrigação (MF-13, MF-22).

        Args:
            client_data: Dados do cliente selecionado
        """
        if self._debug_logger:
            self._debug_logger("DashboardFacade: on_client_picked_for_obligation")

        handle_client_picked_for_obligation_v2(
            client_data=client_data,
            parent=self._parent,
            get_org_id=lambda: getattr(self._parent, "_pending_obligation_org_id", None),
            get_user_id=lambda: getattr(self._parent, "_pending_obligation_user_id", None),
            get_main_app=self._get_main_app,
            on_refresh_callback=self._on_refresh,
        )
