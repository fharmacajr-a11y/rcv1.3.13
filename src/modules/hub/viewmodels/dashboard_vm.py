# -*- coding: utf-8 -*-
"""ViewModel para o Dashboard do HUB.

Implementa o padrão MVVM, encapsulando toda a lógica de apresentação do dashboard
de forma headless (sem depender de Tkinter). A View (HubScreen) apenas consome
o state e renderiza.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Callable, Optional

from src.modules.hub.dashboard_service import DashboardSnapshot, get_dashboard_snapshot

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


@dataclass(frozen=True)
class DashboardCardView:
    """Representação de um card de indicador pronto para UI.

    Attributes:
        label: Texto do label (ex: "Clientes", "Pendências").
        value: Valor numérico do indicador.
        value_text: Texto formatado do valor (pode incluir ícones/warnings).
        bootstyle: Estilo do card (ex: "info", "success", "danger", "warning").
        description: Descrição adicional (opcional, para tooltips futuros).
    """

    label: str
    value: int
    value_text: str
    bootstyle: str
    description: str = ""


@dataclass(frozen=True)
class DashboardViewState:
    """Estado imutável do Dashboard ViewModel.

    Attributes:
        is_loading: Se está carregando dados.
        error_message: Mensagem de erro (None se sem erro).
        snapshot: Snapshot de dados brutos (None se não carregado ou erro).
        card_clientes: Card de Clientes Ativos.
        card_pendencias: Card de Pendências Regulatórias.
        card_tarefas: Card de Tarefas Hoje.
    """

    is_loading: bool = False
    error_message: Optional[str] = None
    snapshot: Optional[DashboardSnapshot] = None
    card_clientes: Optional[DashboardCardView] = None
    card_pendencias: Optional[DashboardCardView] = None
    card_tarefas: Optional[DashboardCardView] = None


class DashboardViewModel:
    """ViewModel headless para o Dashboard do HUB.

    Encapsula a lógica de:
    - Carregar DashboardSnapshot via service
    - Formatar cards de indicadores (textos, cores, estilos)
    - Gerenciar estado de loading/erro

    A View (HubScreen) apenas observa o state e renderiza.
    """

    def __init__(
        self,
        service: Callable[..., DashboardSnapshot] = get_dashboard_snapshot,
    ) -> None:
        """Inicializa o ViewModel.

        Args:
            service: Função de service para carregar snapshot (injetável para testes).
                Assinatura esperada: (org_id: str, today: date | None = None) -> DashboardSnapshot
        """
        self._service = service
        self._state = DashboardViewState()

    @property
    def state(self) -> DashboardViewState:
        """Estado atual do Dashboard (imutável)."""
        return self._state

    def start_loading(self) -> DashboardViewState:
        """Cria estado de loading inicial.

        Returns:
            Estado com is_loading=True e campos limpos.
        """
        self._state = DashboardViewState(is_loading=True)
        return self._state

    def from_error(self, message: str) -> DashboardViewState:
        """Cria estado de erro.

        Args:
            message: Mensagem de erro a ser exibida.

        Returns:
            Estado com error_message preenchido e is_loading=False.
        """
        self._state = DashboardViewState(
            is_loading=False,
            error_message=message,
        )
        return self._state

    def load(self, org_id: str, today: date | None = None) -> DashboardViewState:
        """Carrega snapshot e monta cards de indicadores.

        Este método é headless (sem Tkinter) e pode rodar em thread separada.

        Args:
            org_id: ID da organização.
            today: Data de referência (opcional, usa date.today() se None).

        Returns:
            Novo estado do Dashboard (com snapshot e cards ou erro).
        """
        # Marca como loading
        self._state = replace(
            self._state,
            is_loading=True,
            error_message=None,
        )

        try:
            # Buscar snapshot via service
            snapshot = self._service(org_id=org_id, today=today)

            # Montar cards de indicadores
            card_clientes = self._make_card_clientes(snapshot)
            card_pendencias = self._make_card_pendencias(snapshot)
            card_tarefas = self._make_card_tarefas(snapshot)

            # Atualizar estado com sucesso
            self._state = DashboardViewState(
                is_loading=False,
                error_message=None,
                snapshot=snapshot,
                card_clientes=card_clientes,
                card_pendencias=card_pendencias,
                card_tarefas=card_tarefas,
            )

        except Exception as exc:  # noqa: BLE001
            # Atualizar estado com erro
            logger.error("Erro ao carregar dashboard: %s", exc)
            self._state = DashboardViewState(
                is_loading=False,
                error_message="Não foi possível carregar o dashboard. Tente novamente mais tarde.",
                snapshot=None,
                card_clientes=None,
                card_pendencias=None,
                card_tarefas=None,
            )

        return self._state

    # ========================================================================
    # BUILDERS DE CARDS (Lógica de Apresentação)
    # ========================================================================

    def _make_card_clientes(self, snapshot: DashboardSnapshot) -> DashboardCardView:
        """Monta card de Clientes Ativos.

        Regras:
        - Label: "Clientes"
        - Valor: snapshot.active_clients
        - Estilo: sempre "info" (azul neutro)
        - Texto: número simples sem decoração

        Args:
            snapshot: Snapshot de dados do dashboard.

        Returns:
            Card de Clientes Ativos pronto para renderização.
        """
        active_clients = getattr(snapshot, "active_clients", 0)
        return DashboardCardView(
            label="Clientes",
            value=active_clients,
            value_text=str(active_clients),
            bootstyle="info",
            description="Clientes ativos (não deletados) na organização",
        )

    def _make_card_pendencias(self, snapshot: DashboardSnapshot) -> DashboardCardView:
        """Monta card de Pendências Regulatórias.

        Regras:
        - Label: "Pendências"
        - Valor: snapshot.pending_obligations
        - Estilo:
          - "success" (verde) se 0 pendências
          - "danger" (vermelho) se >0 pendências
        - Texto:
          - "0" se 0 pendências
          - "{N} ⚠" se >0 pendências (com ícone de alerta)

        Args:
            snapshot: Snapshot de dados do dashboard.

        Returns:
            Card de Pendências pronto para renderização.
        """
        count = getattr(snapshot, "pending_obligations", 0)

        if count == 0:
            bootstyle = "success"
            value_text = "0"
            description = "Nenhuma pendência regulatória"
        else:
            bootstyle = "danger"
            value_text = f"{count} ⚠"
            description = f"{count} pendência{'s' if count > 1 else ''} regulatória{'s' if count > 1 else ''}"

        return DashboardCardView(
            label="Pendências",
            value=count,
            value_text=value_text,
            bootstyle=bootstyle,
            description=description,
        )

    def _make_card_tarefas(self, snapshot: DashboardSnapshot) -> DashboardCardView:
        """Monta card de Tarefas Hoje.

        Regras:
        - Label: "Tarefas hoje"
        - Valor: snapshot.tasks_today
        - Estilo:
          - "success" (verde) se 0 tarefas
          - "warning" (amarelo) se >0 tarefas
        - Texto: número simples sem decoração

        Args:
            snapshot: Snapshot de dados do dashboard.

        Returns:
            Card de Tarefas Hoje pronto para renderização.
        """
        count = getattr(snapshot, "tasks_today", 0)

        if count == 0:
            bootstyle = "success"
            description = "Nenhuma tarefa pendente para hoje"
        else:
            bootstyle = "warning"
            description = f"{count} tarefa{'s' if count > 1 else ''} pendente{'s' if count > 1 else ''} para hoje"

        return DashboardCardView(
            label="Tarefas hoje",
            value=count,
            value_text=str(count),
            bootstyle=bootstyle,
            description=description,
        )
