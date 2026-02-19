# -*- coding: utf-8 -*-
"""MF-22: Navigation Facade para HubScreen.

Este módulo centraliza todos os métodos públicos de navegação (go_to_*, open_*)
do HubScreen, transformando-o em um thin orchestrator.

Responsabilidades:
- Delegar navegação para HubNavigationHelper
- Manter API pública consistente
- Permitir logging de navegação se necessário

Benefícios:
- Reduz linhas em hub_screen.py (~20-30 linhas removidas)
- Centraliza lógica de navegação em uma façade
- Facilita testes de navegação isoladamente
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


class HubNavigationFacade:
    """MF-22: Centraliza navegação do HubScreen (go_to_*/open_*).

    Esta façade encapsula toda a lógica de navegação do Hub, delegando
    para o HubNavigationHelper. Mantém a API pública consistente enquanto
    remove responsabilidades diretas do HubScreen.

    Args:
        nav_helper: Instância de HubNavigationHelper (configurado via HubComponentFactory)
        debug_logger: Logger opcional para debug de navegação
    """

    def __init__(self, nav_helper: Any, debug_logger: Optional[Any] = None) -> None:
        """Inicializa façade de navegação.

        Args:
            nav_helper: HubNavigationHelper já configurado
            debug_logger: Logger opcional para debug (ex: _dlog do HubScreen)
        """
        self._nav_helper = nav_helper
        self._debug_logger = debug_logger

    # ==============================================================================
    # MÉTODOS go_to_* (navegação interna)
    # ==============================================================================

    def go_to_clients(self) -> None:
        """Navega para Clientes (MF-10, MF-22: via NavigationFacade)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: go_to_clients")
        self._nav_helper.go_to_clients()

    def go_to_pending(self) -> None:
        """Navega para Pendências Regulatórias/Auditoria (MF-10, MF-22)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: go_to_pending")
        self._nav_helper.go_to_pending()

    def go_to_tasks_today(self) -> None:
        """Abre tarefas de hoje (MF-10, MF-22)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: go_to_tasks_today")
        self._nav_helper.go_to_tasks_today()

    # ==============================================================================
    # MÉTODOS open_* (abertura de módulos)
    # ==============================================================================

    def open_clientes(self) -> None:
        """Abre módulo de Clientes (MF-10, MF-22)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: open_clientes")
        self._nav_helper.open_clientes()

    def open_fluxo_caixa(self) -> None:
        """Abre módulo de Fluxo de Caixa (MF-10, MF-22)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: open_fluxo_caixa")
        self._nav_helper.open_fluxo_caixa()

    def open_farmacia_popular(self) -> None:
        """Abre módulo de Farmácia Popular (MF-10, MF-22)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: open_farmacia_popular")
        self._nav_helper.open_farmacia_popular()

    def open_sngpc(self) -> None:
        """Abre módulo de Sngpc (MF-10, MF-22)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: open_sngpc")
        self._nav_helper.open_sngpc()

    def open_sifap(self) -> None:
        """Abre módulo de Sifap (MF-10, MF-22)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: open_sifap")
        self._nav_helper.open_sifap()

    def open_sites(self) -> None:
        """Abre módulo de Sites (MF-10, MF-22)."""
        if self._debug_logger:
            self._debug_logger("NavigationFacade: open_sites")
        self._nav_helper.open_sites()
