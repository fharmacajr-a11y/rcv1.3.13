# -*- coding: utf-8 -*-
"""Callbacks de dashboard e obrigações para HubScreen.

Extrai lógica de handlers de eventos do dashboard (cards, nova tarefa, nova obrigação)
para reduzir tamanho de hub_screen.py.
"""

from __future__ import annotations

from tkinter import messagebox
from typing import TYPE_CHECKING, Any, Callable, Optional

from src.modules.hub.views.hub_dashboard_callbacks_constants import (
    BANNER_CLIENT_PICK_OBLIGATIONS,
    MSG_APP_NOT_FOUND,
    MSG_ACTIVITY_VIEW_COMING_SOON,
    MSG_ERROR_OPEN_DIALOG,
    MSG_ERROR_OPEN_VIEW,
    MSG_ERROR_PROCESS_ACTION,
    MSG_ERROR_PROCESS_SELECTION,
    MSG_ERROR_START_FLOW,
    MSG_LOGIN_REQUIRED_OBLIGATIONS,
    MSG_LOGIN_REQUIRED_TASKS,
    TITLE_AUTH_REQUIRED,
    TITLE_ERROR,
    TITLE_IN_DEVELOPMENT,
)

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import DashboardViewState

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


def handle_new_task_click(
    parent: Any,
    get_org_id: Callable[[], Optional[str]],
    get_user_id: Callable[[], Optional[str]],
    on_success_callback: Callable[[], None],
) -> None:
    """Abre diálogo para criar nova tarefa.

    Args:
        parent: Widget pai para o diálogo
        get_org_id: Função para obter org_id atual
        get_user_id: Função para obter user_id atual
        on_success_callback: Callback chamado após criar tarefa com sucesso
    """
    try:
        # Obter org_id e user_id
        org_id = get_org_id()
        user_id = get_user_id()

        if not org_id or not user_id:
            messagebox.showwarning(
                TITLE_AUTH_REQUIRED,
                MSG_LOGIN_REQUIRED_TASKS,
                parent=parent,
            )
            return

        # Carregar lista de clientes
        clients: list = []
        try:
            from data.supabase_repo import list_clients_for_picker

            clients = list_clients_for_picker(org_id, limit=500)
        except Exception as e:  # noqa: BLE001
            logger.warning("Não foi possível carregar clientes: %s", e)

        # Abrir diálogo
        from src.modules.tasks.views import NovaTarefaDialog

        dialog = NovaTarefaDialog(
            parent=parent,
            org_id=org_id,
            user_id=user_id,
            on_success=on_success_callback,
            clients=clients,
        )
        dialog.deiconify()  # Mostra a janela

    except Exception as e:  # noqa: BLE001
        logger.exception("Erro ao abrir diálogo de nova tarefa")
        messagebox.showerror(
            TITLE_ERROR,
            MSG_ERROR_OPEN_DIALOG.format(error=e),
            parent=parent,
        )


def handle_new_obligation_click(
    parent: Any,
    get_org_id: Callable[[], Optional[str]],
    get_user_id: Callable[[], Optional[str]],
    get_main_app: Callable[[], Any],
    on_client_picked: Callable[[dict], None],
) -> None:
    """Abre modo seleção de Clientes e depois janela de obrigações do cliente selecionado.

    Args:
        parent: Widget pai para mensagens
        get_org_id: Função para obter org_id atual
        get_user_id: Função para obter user_id atual
        get_main_app: Função para obter referência ao app principal
        on_client_picked: Callback chamado quando cliente é selecionado (recebe dict)
    """
    try:
        # Obter org_id e user_id
        org_id = get_org_id()
        user_id = get_user_id()

        if not org_id or not user_id:
            messagebox.showwarning(
                TITLE_AUTH_REQUIRED,
                MSG_LOGIN_REQUIRED_OBLIGATIONS,
                parent=parent,
            )
            return

        # Abrir modo seleção de Clientes usando API explícita
        app = get_main_app()
        if not app:
            messagebox.showwarning(
                TITLE_ERROR,
                MSG_APP_NOT_FOUND,
                parent=parent,
            )
            return

        from src.modules.main_window.controller import navigate_to, start_client_pick_mode

        # Usar nova API com callback específico para Obrigações
        start_client_pick_mode(
            app,
            on_client_picked=on_client_picked,
            banner_text=BANNER_CLIENT_PICK_OBLIGATIONS,
            return_to=lambda: navigate_to(app, "hub"),
        )

    except Exception as e:  # noqa: BLE001
        logger.exception("Erro ao iniciar fluxo de nova obrigação")
        messagebox.showerror(
            TITLE_ERROR,
            MSG_ERROR_START_FLOW.format(error=e),
            parent=parent,
        )


def handle_view_all_activity_click(parent: Any) -> None:
    """Abre visualização completa da atividade da equipe.

    Args:
        parent: Widget pai para o diálogo
    """
    try:
        messagebox.showinfo(
            TITLE_IN_DEVELOPMENT,
            MSG_ACTIVITY_VIEW_COMING_SOON,
            parent=parent,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Erro ao abrir visualização de atividades")
        messagebox.showerror(
            TITLE_ERROR,
            MSG_ERROR_OPEN_VIEW.format(error=e),
            parent=parent,
        )


def handle_client_picked_for_obligation(
    client_data: dict,
    parent: Any,
    get_org_id: Callable[[], Optional[str]],
    get_user_id: Callable[[], Optional[str]],
    get_main_app: Callable[[], Any],
    on_refresh_callback: Callable[[], None],
) -> None:
    """Handler chamado quando cliente é selecionado no modo de seleção para obrigações.

    Args:
        client_data: Dicionário com dados do cliente selecionado
        parent: Widget pai para diálogos
        get_org_id: Função para obter org_id atual
        get_user_id: Função para obter user_id atual
        get_main_app: Função para obter referência ao app principal
        on_refresh_callback: Callback para refresh do hub após criação
    """
    try:
        org_id = get_org_id()
        user_id = get_user_id()

        if not org_id or not user_id:
            logger.warning("org_id ou user_id não disponível no callback de obrigações")
            return

        # Extrair dados do cliente
        client_id = client_data.get("id")
        if not client_id:
            logger.warning("Client data sem ID: %s", client_data)
            return

        # Converter para int se necessário
        if isinstance(client_id, str):
            try:
                client_id = int(client_id)
            except ValueError:
                logger.error("Não foi possível converter client_id '%s' para int", client_id)
                return

        # Montar nome do cliente para exibição
        client_name = client_data.get("razao_social") or client_data.get("nome") or f"Cliente {client_id}"

        # Abrir janela de obrigações
        from src.modules.clientes.views.client_obligations_window import show_client_obligations_window

        # Voltar para o Hub primeiro
        app = get_main_app()
        if app:
            from src.modules.main_window.controller import navigate_to

            navigate_to(app, "hub")

        # Depois abrir janela de obrigações
        show_client_obligations_window(
            parent=parent.winfo_toplevel(),  # type: ignore[arg-type]
            org_id=org_id,
            created_by=user_id,
            client_id=client_id,
            client_name=client_name,
            on_refresh_hub=on_refresh_callback,
        )

    except Exception as e:  # noqa: BLE001
        logger.exception("Erro ao processar cliente selecionado para obrigações")
        messagebox.showerror(
            TITLE_ERROR,
            MSG_ERROR_PROCESS_SELECTION.format(error=e),
            parent=parent,
        )


def handle_card_click(
    card_type: str,
    state: DashboardViewState,
    controller: Any,
    parent: Any,
) -> None:
    """Handler genérico para clique em cards do dashboard.

    Args:
        card_type: Tipo do card ('clients', 'pending', 'tasks')
        state: Estado atual do dashboard
        controller: Controller de ações do dashboard
        parent: Widget pai para mensagens de erro
    """
    try:
        if card_type == "clients":
            controller.handle_clients_card_click(state)
        elif card_type == "pending":
            controller.handle_pending_card_click(state)
        elif card_type == "tasks":
            controller.handle_tasks_today_card_click(state)
        else:
            logger.warning(f"Tipo de card desconhecido: {card_type}")
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Erro ao navegar a partir do card {card_type}")
        messagebox.showerror(
            TITLE_ERROR,
            MSG_ERROR_PROCESS_ACTION.format(error=e),
            parent=parent,
        )
