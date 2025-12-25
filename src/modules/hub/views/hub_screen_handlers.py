# -*- coding: utf-8 -*-
"""hub_screen_handlers.py - Handlers, bindings e eventos do HUB.

MVC-REFAC-001: Handlers separados do arquivo principal.
Mantém compatibilidade total via wrappers em hub_screen.py.

Responsabilidades:
- Configurar bindings de teclado (Ctrl+D, Ctrl+L)
- Iniciar timers e lifecycle do HUB
- Handlers de eventos (não callbacks de negócio)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


if TYPE_CHECKING:
    from src.modules.hub.views.hub_screen import HubScreen


logger = get_logger(__name__)


def setup_bindings(screen: HubScreen) -> None:
    """Configura atalhos de teclado (Ctrl+D para diagnóstico, Ctrl+L para reload cache).

    Args:
        screen: Instância do HubScreen
    """
    # Configurar atalhos (apenas uma vez)
    binds_ready = getattr(screen, "_binds_ready", False)
    if not binds_ready:
        # Ctrl+D para diagnóstico
        screen.bind_all("<Control-d>", screen._show_debug_info)
        screen.bind_all("<Control-D>", screen._show_debug_info)

        # Ctrl+L para recarregar cache de nomes (teste)
        screen.bind_all(
            "<Control-l>",
            lambda e: screen._refresh_author_names_cache_async(force=True),
        )
        screen.bind_all(
            "<Control-L>",
            lambda e: screen._refresh_author_names_cache_async(force=True),
        )
        screen._binds_ready = True


def start_timers(screen: HubScreen) -> None:
    """Inicia lifecycle do HUB (MF-28, MF-24: via LifecycleFacade).

    Args:
        screen: Instância do HubScreen
    """
    # CRÍTICO: Marcar controller como ativo ANTES de iniciar timers
    screen._hub_controller.start()
    # Iniciar lifecycle (timers, polling, etc)
    screen._lifecycle_facade.start_timers()
