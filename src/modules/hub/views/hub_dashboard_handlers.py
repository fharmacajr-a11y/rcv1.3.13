# -*- coding: utf-8 -*-
"""Hub Dashboard Handlers - Extração dos callbacks de dashboard.

═══════════════════════════════════════════════════════════════════════════════
MF-13: Extrair Dashboard Handlers
═══════════════════════════════════════════════════════════════════════════════

Este módulo centraliza os handlers de dashboard que anteriormente estavam
implementados como métodos privados em HubScreen. A extração permite:

1. Reduzir tamanho e complexidade de hub_screen.py
2. Melhorar testabilidade (funções puras, sem dependência de Tkinter)
3. Separar concerns: HubScreen orquestra, handlers executam ações
4. Facilitar manutenção e evolução da lógica de dashboard

HANDLERS EXTRAÍDOS:
- handle_new_task_click_v2        → Criar nova tarefa
- handle_new_obligation_click_v2  → Criar nova obrigação
- handle_view_all_activity_click_v2 → Ver todas as atividades
- handle_card_clients_click       → Card Clientes Ativos
- handle_card_pendencias_click    → Card Pendências Regulatórias
- handle_card_tarefas_click       → Card Tarefas Hoje
- handle_client_picked_for_obligation_v2 → Callback após picker de cliente

NOTA: Estes handlers são "v2" porque delegam para funções já existentes em
hub_dashboard_callbacks.py. O HubScreen mantém wrappers finos (_on_*) para
compatibilidade com binds de UI e testes existentes.

DEPENDÊNCIAS:
- hub_dashboard_callbacks.py (onde está a lógica real de negócio)
- DashboardViewModel (para acessar state)
- DashboardActionController (para ações de navegação)

STATUS: Criado na MF-13 (Dezembro/2025)
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from src.modules.hub.views.hub_dashboard_callbacks import (
    handle_card_click,
    handle_client_picked_for_obligation,
    handle_new_obligation_click,
    handle_new_task_click,
    handle_view_all_activity_click,
)

if TYPE_CHECKING:
    from src.modules.hub.controllers import DashboardActionController
    from src.modules.hub.viewmodels import DashboardViewModel


def handle_new_task_click_v2(
    *,
    parent: Any,
    get_org_id: Callable[[], str | None],
    get_user_id: Callable[[], str | None],
    on_success_callback: Callable[[], None],
) -> None:
    """MF-13: Handler extraído do HubScreen._on_new_task.

    Abre diálogo para criar nova tarefa, delegando para handle_new_task_click.

    Args:
        parent: Widget pai (para posicionar diálogo)
        get_org_id: Callable que retorna org_id atual
        get_user_id: Callable que retorna user_id atual
        on_success_callback: Callback executado após sucesso (ex: _load_dashboard)
    """
    handle_new_task_click(
        parent=parent,
        get_org_id=get_org_id,
        get_user_id=get_user_id,
        on_success_callback=on_success_callback,
    )


def handle_new_obligation_click_v2(
    *,
    parent: Any,
    get_org_id: Callable[[], str | None],
    get_user_id: Callable[[], str | None],
    get_main_app: Callable[[], Any],
    on_client_picked: Callable[[dict], None],
) -> None:
    """MF-13: Handler extraído do HubScreen._on_new_obligation.

    Abre modo seleção de Clientes e depois janela de obrigações.

    Args:
        parent: Widget pai
        get_org_id: Callable que retorna org_id atual
        get_user_id: Callable que retorna user_id atual
        get_main_app: Callable que retorna referência ao MainWindow
        on_client_picked: Callback executado quando cliente é escolhido
    """
    handle_new_obligation_click(
        parent=parent,
        get_org_id=get_org_id,
        get_user_id=get_user_id,
        get_main_app=get_main_app,
        on_client_picked=on_client_picked,
    )


def handle_view_all_activity_click_v2(
    *,
    parent: Any,
) -> None:
    """MF-13: Handler extraído do HubScreen._on_view_all_activity.

    Abre visualização completa da atividade da equipe.

    Args:
        parent: Widget pai
    """
    handle_view_all_activity_click(parent=parent)


def handle_card_clients_click(
    *,
    dashboard_vm: DashboardViewModel,
    dashboard_actions: DashboardActionController,
    parent: Any,
) -> None:
    """MF-13: Handler extraído do HubScreen._on_card_clients_click.

    Handler de clique no card 'Clientes Ativos'.

    Args:
        dashboard_vm: ViewModel do dashboard (para acessar state)
        dashboard_actions: Controller de ações do dashboard
        parent: Widget pai
    """
    handle_card_click(
        card_type="clients",
        state=dashboard_vm.state,
        controller=dashboard_actions,
        parent=parent,
    )


def handle_card_pendencias_click(
    *,
    dashboard_vm: DashboardViewModel,
    dashboard_actions: DashboardActionController,
    parent: Any,
) -> None:
    """MF-13: Handler extraído do HubScreen._on_card_pendencias_click.

    Handler de clique no card 'Pendências Regulatórias'.

    Args:
        dashboard_vm: ViewModel do dashboard (para acessar state)
        dashboard_actions: Controller de ações do dashboard
        parent: Widget pai
    """
    handle_card_click(
        card_type="pending",
        state=dashboard_vm.state,
        controller=dashboard_actions,
        parent=parent,
    )


def handle_card_tarefas_click(
    *,
    dashboard_vm: DashboardViewModel,
    dashboard_actions: DashboardActionController,
    parent: Any,
) -> None:
    """MF-13: Handler extraído do HubScreen._on_card_tarefas_click.

    Handler de clique no card 'Tarefas Hoje'.

    Args:
        dashboard_vm: ViewModel do dashboard (para acessar state)
        dashboard_actions: Controller de ações do dashboard
        parent: Widget pai
    """
    handle_card_click(
        card_type="tasks",
        state=dashboard_vm.state,
        controller=dashboard_actions,
        parent=parent,
    )


def handle_client_picked_for_obligation_v2(
    *,
    client_data: dict,
    parent: Any,
    get_org_id: Callable[[], str | None],
    get_user_id: Callable[[], str | None],
    get_main_app: Callable[[], Any],
    on_refresh_callback: Callable[[], None],
) -> None:
    """MF-13: Handler extraído do HubScreen._handle_client_picked_for_obligation.

    Callback chamado quando cliente é selecionado no modo pick.

    Args:
        client_data: Dados do cliente selecionado
        parent: Widget pai
        get_org_id: Callable que retorna org_id (usa atributos temporários)
        get_user_id: Callable que retorna user_id (usa atributos temporários)
        get_main_app: Callable que retorna referência ao MainWindow
        on_refresh_callback: Callback para refresh após sucesso
    """
    handle_client_picked_for_obligation(
        client_data=client_data,
        parent=parent,
        get_org_id=get_org_id,
        get_user_id=get_user_id,
        get_main_app=get_main_app,
        on_refresh_callback=on_refresh_callback,
    )
