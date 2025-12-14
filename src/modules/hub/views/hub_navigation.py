# -*- coding: utf-8 -*-
"""HubNavigation - Métodos de navegação entre módulos do HUB.

Este módulo contém os métodos de navegação que eram anteriormente parte
do HubScreen. Extraído em MF-10 para reduzir tamanho e complexidade.

Implementa os protocolos:
- HubNavigatorProtocol (go_to_clients, go_to_pending, go_to_tasks_today)
- HubQuickActionsNavigatorProtocol (open_*: módulos específicos)

Responsabilidades:
- Expor métodos públicos de navegação
- Delegar para callbacks armazenados no HubScreen
- Fornecer fallbacks e logging quando callbacks ausentes
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.hub.views.hub_screen import HubScreen

logger = logging.getLogger(__name__)


class HubNavigationHelper:
    """Helper para métodos de navegação do HubScreen.

    Mantém referência ao HubScreen para acessar callbacks
    e delegar operações.
    """

    def __init__(self, hub_screen: HubScreen) -> None:
        """Inicializa helper com referência ao HubScreen.

        Args:
            hub_screen: Instância do HubScreen (self)
        """
        self._hub = hub_screen

    # ═══════════════════════════════════════════════════════════════════════
    # HubNavigatorProtocol - Navegação para telas principais
    # ═══════════════════════════════════════════════════════════════════════

    def go_to_clients(self) -> None:
        """Navega para a tela de Clientes."""
        callback = getattr(self._hub, "open_clientes", None)
        if callback:
            callback()
        else:
            logger.debug("HubNavigationHelper: Callback open_clientes não definido")

    def go_to_pending(self) -> None:
        """Navega para a tela de Pendências Regulatórias/Auditoria."""
        callback = getattr(self._hub, "open_auditoria", None)
        if callback:
            callback()
        else:
            logger.debug("HubNavigationHelper: Callback open_auditoria não definido")

    def go_to_tasks_today(self) -> None:
        """Abre interface de tarefas de hoje."""
        # Por enquanto, abre o diálogo de nova tarefa
        # No futuro, pode abrir visualização filtrada de tarefas
        on_new_task = getattr(self._hub, "_on_new_task", None)
        if on_new_task:
            on_new_task()

    # ═══════════════════════════════════════════════════════════════════════
    # HubQuickActionsNavigatorProtocol - Abertura de módulos específicos
    # ═══════════════════════════════════════════════════════════════════════

    def open_clientes(self) -> None:
        """Abre módulo de Clientes (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("clientes")

    def open_senhas(self) -> None:
        """Abre módulo de Senhas (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("senhas")

    def open_auditoria(self) -> None:
        """Abre módulo de Auditoria (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("auditoria")

    def open_fluxo_caixa(self) -> None:
        """Abre módulo de Fluxo de Caixa (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("cashflow")

    def open_anvisa(self) -> None:
        """Abre módulo de Anvisa (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("anvisa")

    def open_farmacia_popular(self) -> None:
        """Abre módulo de Farmácia Popular (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("farmacia_popular")

    def open_sngpc(self) -> None:
        """Abre módulo de Sngpc (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("sngpc")

    def open_sifap(self) -> None:
        """Abre módulo de Sifap (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("sifap")

    def open_sites(self) -> None:
        """Abre módulo de Sites (MF-16: usa _nav_callbacks)."""
        self._invoke_nav_callback("sites")

    # ═══════════════════════════════════════════════════════════════════════
    # Helper privado
    # ═══════════════════════════════════════════════════════════════════════

    def _invoke_nav_callback(self, module_name: str) -> None:
        """Invoca callback de navegação via HubNavigationCallbacks (MF-16).

        Args:
            module_name: Nome do módulo (ex: 'clientes', 'senhas', etc.)
        """
        nav_callbacks = getattr(self._hub, "_nav_callbacks", None)
        if nav_callbacks and hasattr(nav_callbacks, "invoke"):
            success = nav_callbacks.invoke(module_name)
            if not success:
                logger.debug(f"HubNavigationHelper: Callback para '{module_name}' não definido")
        else:
            logger.debug("HubNavigationHelper: _nav_callbacks não disponível")

    def _call_callback(self, callback_attr: str) -> None:
        """Invoca callback se existir (DEPRECATED: MF-16 - usar _invoke_nav_callback).

        Args:
            callback_attr: Nome do atributo de callback no HubScreen
        """
        callback = getattr(self._hub, callback_attr, None)
        if callable(callback):
            callback()
        else:
            logger.debug(f"HubNavigationHelper: {callback_attr} não definido ou não é callable")
