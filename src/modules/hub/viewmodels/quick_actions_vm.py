# -*- coding: utf-8 -*-
"""ViewModel headless para Atalhos Rápidos do HUB (Quick Actions).

Este ViewModel encapsula toda a lógica de apresentação dos atalhos do HUB:
- Decide quais atalhos aparecem
- Atribui labels, descrições, ícones
- Aplica feature flags / permissões (is_enabled)
- Define a ordem de exibição

Segue o padrão MVVM:
- ViewModel: lógica de apresentação (este arquivo)
- Controller: lógica de ações (quick_actions_controller.py)
- View: apenas layout e binding de eventos (hub_screen.py/_build_modules_panel)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

try:
    from src.core.logger import get_logger
except Exception:

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


@dataclass(frozen=True)
class QuickActionItemView:
    """Representa um atalho rápido do HUB (imutável)."""

    id: str  # ex: "clientes", "anvisa", "auditoria"
    label: str  # texto exibido no botão
    description: str | None = None  # tooltip ou texto auxiliar
    icon_name: str | None = None  # ícone padronizado (futuro)
    bootstyle: str | None = None  # estilo ttkbootstrap do botão
    is_enabled: bool = True  # habilitado/desabilitado
    order: int = 0  # para ordenação estável
    category: str = "default"  # categoria do atalho (bloco no menu)


@dataclass(frozen=True)
class QuickActionsViewState:
    """Estado imutável da tela de atalhos rápidos."""

    actions: list[QuickActionItemView] = field(default_factory=list)
    is_loading: bool = False
    error_message: str | None = None


class QuickActionsViewModel:
    """ViewModel headless para lógica de apresentação dos atalhos do HUB.

    IMPORTANTE: Os IDs de actions aqui devem permanecer alinhados com
    QuickActionsController.get_supported_action_ids(). O Controller é a
    fonte de verdade para quais actions existem; este ViewModel define
    apenas como elas aparecem na UI (labels, ícones, ordem, etc).

    Navegação é 100% responsabilidade do QuickActionsController.
    """

    def __init__(
        self,
        features_service: Any | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Inicializa o QuickActionsViewModel.

        Args:
            features_service: Serviço de feature flags (opcional, stub por enquanto).
            logger: Logger para diagnóstico.
        """
        self._features_service = features_service
        self._logger = logger or get_logger(__name__)

    def build_state(
        self,
        org_id: str | None = None,
        _user_profile: str | None = None,  # noqa: ARG002 (reservado para permissões futuras)
    ) -> QuickActionsViewState:
        """Constrói o estado dos atalhos do HUB.

        Args:
            org_id: ID da organização (para feature flags futuras).
            _user_profile: Perfil do usuário (para permissões futuras).

        Returns:
            QuickActionsViewState com a lista de atalhos disponíveis.
        """
        try:
            # Define a lista de atalhos padrão do HUB
            # Ordem e categorias seguem a estrutura atual em _build_modules_panel
            actions = [
                # Bloco 1: Cadastros / Acesso
                QuickActionItemView(
                    id="clientes",
                    label="Clientes",
                    description="Gerenciar cadastro de clientes",
                    order=10,
                    category="cadastros",
                ),
                # Bloco 2: Gestão
                QuickActionItemView(
                    id="fluxo_caixa",
                    label="Fluxo de Caixa",
                    description="Gestão financeira e fluxo de caixa",
                    order=40,
                    category="gestao",
                ),
                # Bloco 3: Regulatório / Programas
                QuickActionItemView(
                    id="anvisa",
                    label="Anvisa",
                    description="Regulatório Anvisa",
                    order=50,
                    category="regulatorio",
                ),
                QuickActionItemView(
                    id="sngpc",
                    label="Sngpc",
                    description="Sistema Nacional de Gerenciamento de Produtos Controlados",
                    order=60,
                    category="regulatorio",
                ),
                QuickActionItemView(
                    id="sites",
                    label="Sites",
                    description="Links úteis e sites de referência",
                    order=90,
                    category="utilidades",
                ),
            ]

            # Aplicar feature flags / permissões (futuro)
            # Por enquanto, todos habilitados
            if self._features_service:
                # Exemplo de lógica futura:
                # for action in actions:
                #     if not self._features_service.is_enabled(action.id, org_id):
                #         action = replace(action, is_enabled=False)
                pass

            # Ordenar por order
            actions_sorted = sorted(actions, key=lambda a: a.order)

            return QuickActionsViewState(
                actions=actions_sorted,
                is_loading=False,
                error_message=None,
            )

        except Exception as e:
            self._logger.exception("Erro ao construir estado de atalhos")
            return QuickActionsViewState(
                actions=[],
                is_loading=False,
                error_message=f"Erro ao carregar atalhos: {e}",
            )
