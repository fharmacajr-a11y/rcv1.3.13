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

        Navega para a tela de Auditoria (Pendências), independente da contagem.

        Args:
            state: Estado atual do dashboard com dados dos cards.
        """
        try:
            self._logger.debug("DashboardActionController: Clique no card de Pendências")
            self._navigator.go_to_pending()
        except Exception as e:
            self._logger.exception("Erro ao navegar para Pendências a partir do card")
            raise RuntimeError(f"Erro ao abrir tela de Auditoria: {e}") from e

    def handle_tasks_today_card_click(self, state: DashboardViewState) -> None:
        """Handle de clique no card 'Tarefas Hoje'.

        Abre a interface de tarefas (por enquanto, abre diálogo de nova tarefa).
        No futuro pode abrir visualização filtrada de tarefas pendentes.

        Args:
            state: Estado atual do dashboard com dados dos cards.
        """
        try:
            self._logger.debug("DashboardActionController: Clique no card de Tarefas")
            self._navigator.go_to_tasks_today()
        except Exception as e:
            self._logger.exception("Erro ao abrir tarefas a partir do card")
            raise RuntimeError(f"Erro ao abrir tarefas: {e}") from e
