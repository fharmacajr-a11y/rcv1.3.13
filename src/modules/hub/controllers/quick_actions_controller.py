# -*- coding: utf-8 -*-
"""Controller headless para ações dos Atalhos Rápidos do HUB.

Este controller encapsula toda a lógica de ações quando o usuário
interage com os atalhos do HUB (cliques nos botões de módulos).

Segue o padrão MVVM:
- ViewModel (QuickActionsViewModel): lógica de apresentação (lista, labels, ordem)
- Controller (QuickActionsController): lógica de ações de usuário (navegação)
- View (HubScreen/_build_modules_panel): apenas layout e binding de eventos
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

try:
    from src.core.logger import get_logger
except Exception:

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


@runtime_checkable
class HubQuickActionsNavigatorProtocol(Protocol):
    """Protocol para navegação entre módulos do HUB.

    Define a interface mínima que o QuickActionsController precisa
    para navegar entre os módulos sem depender de Tkinter diretamente.
    """

    def open_clientes(self) -> None:
        """Abre o módulo de Clientes."""
        ...

    def open_fluxo_caixa(self) -> None:
        """Abre o módulo de Fluxo de Caixa."""
        ...

    def open_anvisa(self) -> None:
        """Abre o módulo de Anvisa."""
        ...

    def open_sngpc(self) -> None:
        """Abre o módulo de Sngpc."""
        ...

    def open_sites(self) -> None:
        """Abre o módulo de Sites."""
        ...


@dataclass
class QuickActionsController:
    """Controller headless para ações de atalhos do HUB."""

    navigator: HubQuickActionsNavigatorProtocol
    logger: logging.Logger | None = None

    def get_supported_action_ids(self) -> tuple[str, ...]:
        """Retorna a lista de IDs canônicos de actions suportadas.

        Esta é a fonte de verdade para quais actions existem no sistema.
        Não inclui aliases (ex: "cashflow" é alias de "fluxo_caixa").

        Returns:
            Tupla com os IDs canônicos de todas as actions suportadas.

        Note:
            QuickActionsViewModel deve manter seus IDs alinhados com esta lista.
        """
        return (
            "clientes",
            "fluxo_caixa",
            "anvisa",
            "sngpc",
            "sites",
        )

    def handle_action_click(self, action_id: str) -> bool:
        """Manipula clique em um atalho do HUB.

        Args:
            action_id: ID do atalho clicado (ex: "clientes", "anvisa", etc).

        Returns:
            True se a ação foi reconhecida e tratada, False caso contrário.
        """
        _logger = self.logger or get_logger(__name__)

        try:
            # Dispatch para o método apropriado do navigator
            if action_id == "clientes":
                self.navigator.open_clientes()
            elif action_id in ("fluxo_caixa", "cashflow"):  # Suporte a alias
                self.navigator.open_fluxo_caixa()
            elif action_id == "anvisa":
                self.navigator.open_anvisa()
            elif action_id == "sngpc":
                self.navigator.open_sngpc()
            elif action_id == "sites":
                self.navigator.open_sites()
            else:
                _logger.warning("Ação rápida desconhecida: %s", action_id)
                return False

            return True

        except Exception:  # noqa: BLE001
            _logger.exception("Erro ao executar ação rápida %s", action_id)
            # Não propaga exceção para evitar crash da UI
            raise  # Re-raise para permitir tratamento no controller

    def handle_module_click(self, module_id: str | None) -> bool:
        """Manipula clique em um módulo do HUB.

        MF-18: Centraliza a lógica de navegação de módulos, reutilizando
        o mapeamento já existente em handle_action_click.

        Args:
            module_id: ID do módulo clicado (ex: "clientes", "senhas", etc).

        Returns:
            True se o módulo foi reconhecido e tratado, False caso contrário.
        """
        # Tratamento de entrada vazia/None
        if not module_id:
            _logger = self.logger or get_logger(__name__)
            _logger.warning("Module ID vazio ou None")
            return False

        # Normalizar para lowercase
        module_id_lower = module_id.lower()

        # Delegar para handle_action_click (reuso de lógica)
        # Module IDs são equivalentes aos action IDs
        return self.handle_action_click(module_id_lower)
