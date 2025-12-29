# -*- coding: utf-8 -*-
"""Controller headless para ações de clique dos cards do Dashboard.

Este controller encapsula toda a lógica de navegação/ações quando o usuário
clica nos cards de indicadores do dashboard (Clientes, Pendências, Tarefas).

Segue o padrão MVVM:
- ViewModel (DashboardViewModel): lógica de apresentação (cores, textos, formatação)
- Controller (DashboardActionController): lógica de ações de usuário (navegação)
- View (HubScreen + dashboard_center): apenas layout e binding de eventos
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from src.modules.hub.viewmodels import DashboardViewState

try:
    from src.core.logger import get_logger
except Exception:

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


@runtime_checkable
class HubNavigatorProtocol(Protocol):
    """Protocol para navegação entre telas do HUB.

    Define a interface mínima que o DashboardActionController precisa
    para navegar entre diferentes telas/módulos do aplicativo.
    """

    def go_to_clients(self) -> None:
        """Navega para a tela de Clientes."""
        ...

    def go_to_pending(self) -> None:
        """Navega para a tela de Pendências Regulatórias (Auditoria)."""
        ...

    def go_to_tasks_today(self) -> None:
        """Abre interface para gerenciar tarefas de hoje."""
        ...


class DashboardActionController:
    """Controller headless para ações de clique nos cards do Dashboard.

    Responsabilidades:
    - Receber eventos de clique dos cards
    - Decidir a ação apropriada baseada no estado (DashboardViewState)
    - Delegar navegação para o HubNavigatorProtocol

    Não tem dependências de Tkinter - é totalmente headless e testável.
    """

    def __init__(
        self,
        navigator: HubNavigatorProtocol,
        logger: logging.Logger | None = None,
    ) -> None:
        """Inicializa o controller.

        Args:
            navigator: Implementação do protocolo de navegação.
            logger: Logger opcional (usa logger do módulo se não fornecido).
        """
        self._navigator = navigator
        self._logger = logger or globals()["logger"]

    def handle_clients_card_click(self, state: DashboardViewState) -> None:
        """Handle de clique no card 'Clientes Ativos'.

        Navega para a tela de Clientes, independente da contagem.

        Args:
            state: Estado atual do dashboard com dados dos cards.
        """
        try:
            self._logger.debug("DashboardActionController: Clique no card de Clientes")
            self._navigator.go_to_clients()
        except Exception as e:
            self._logger.exception("Erro ao navegar para Clientes a partir do card")
            raise RuntimeError(f"Erro ao abrir tela de Clientes: {e}") from e

    def handle_pending_card_click(self, state: DashboardViewState) -> None:
        """Handle de clique no card 'Pendências Regulatórias'.

        Em modo ANVISA-only: redireciona para open_anvisa (se disponível).
        Caso contrário, navega para a tela de Auditoria (Pendências).

        Args:
            state: Estado atual do dashboard com dados dos cards.
        """
        try:
            self._logger.debug("DashboardActionController: Clique no card de Pendências")

            # Se modo ANVISA-only, redirecionar para open_anvisa
            if state.snapshot and state.snapshot.anvisa_only:
                if hasattr(self._navigator, "open_anvisa"):
                    self._logger.debug("Modo ANVISA-only: redirecionando para open_anvisa")
                    getattr(self._navigator, "open_anvisa")()
                    return

            # Fluxo normal: abrir Auditoria
            self._navigator.go_to_pending()
        except Exception as e:
            self._logger.exception("Erro ao navegar para Pendências a partir do card")
            raise RuntimeError(f"Erro ao abrir tela de Auditoria: {e}") from e

    def handle_tasks_today_card_click(self, state: DashboardViewState) -> None:
        """Handle de clique no card 'Tarefas Hoje'.

        Em modo ANVISA-only:
        - Se houver 1 cliente: redireciona para histórico direto
        - Se houver 2+ clientes: abre picker modal
        - Caso contrário: redireciona para open_anvisa (se disponível)

        Fora do modo ANVISA-only: abre interface de tarefas (diálogo de nova tarefa).

        Args:
            state: Estado atual do dashboard com dados dos cards.
        """
        try:
            self._logger.debug("DashboardActionController: Clique no card de Tarefas")

            # Se modo ANVISA-only, determinar ação baseado em clientes únicos
            if state.snapshot and state.snapshot.anvisa_only:
                # Preferir clients_of_the_day (clientes únicos)
                raw_items: list[dict[str, object]] = []
                if state.snapshot.clients_of_the_day:
                    raw_items = list(state.snapshot.clients_of_the_day)
                elif state.snapshot.pending_tasks:
                    raw_items = list(state.snapshot.pending_tasks)

                # Extrair clientes únicos preservando ordem
                unique_client_ids: list[str] = []
                for item in raw_items:
                    try:
                        cid = str(item.get("client_id", "")).strip()
                    except Exception:
                        cid = ""
                    if cid and cid not in unique_client_ids:
                        unique_client_ids.append(cid)

                # Se houver exatamente 1 cliente, abrir histórico direto
                if len(unique_client_ids) == 1:
                    client_id = unique_client_ids[0]
                    if client_id and hasattr(self._navigator, "open_anvisa_history"):
                        self._logger.debug(f"Modo ANVISA-only com 1 cliente: abrindo histórico do cliente {client_id}")
                        getattr(self._navigator, "open_anvisa_history")(client_id)
                        return

                # Se houver múltiplos clientes, abrir picker
                if len(unique_client_ids) > 1 and hasattr(self._navigator, "open_anvisa_history_picker"):
                    self._logger.debug(f"Modo ANVISA-only com {len(unique_client_ids)} clientes: abrindo picker")
                    getattr(self._navigator, "open_anvisa_history_picker")(raw_items)
                    return

                # Fallback: abrir ANVISA normal
                if hasattr(self._navigator, "open_anvisa"):
                    self._logger.debug("Modo ANVISA-only: redirecionando para open_anvisa (fallback)")
                    getattr(self._navigator, "open_anvisa")()
                    return

            # Fluxo normal: abrir interface de tarefas
            self._navigator.go_to_tasks_today()
        except Exception as e:
            self._logger.exception("Erro ao abrir tarefas a partir do card")
            raise RuntimeError(f"Erro ao abrir tarefas: {e}") from e
