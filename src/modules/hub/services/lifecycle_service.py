# -*- coding: utf-8 -*-
"""Serviço headless para lifecycle do HubScreen.

CLEANAPP-HUB-LEGACY-01: Substitui lógica de src/modules/hub/actions.py

Este serviço consolida:
- Lógica de on_show (inicialização quando tela fica visível)
- Coordenação de live-sync, render de notas, refresh de cache

Migrado de:
- src/modules/hub/actions.py (on_show)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Protocol
    from src.modules.hub.state import HubState

    class HubScreenProtocol(Protocol):
        """Protocolo para HubScreen.

        MF-39: Atualizado para usar state.author_cache em vez de _author_names_cache.
        MF-40: state como property para compatibilidade com HubScreen.
        """

        @property
        def state(self) -> HubState: ...

        _last_org_for_names: Any
        notes_history: Any

        def _start_live_sync(self) -> None: ...

        def render_notes(self, notes: Any, force: bool = False) -> None: ...

        def _refresh_author_names_cache_async(self, force: bool = False) -> None: ...


logger = logging.getLogger(__name__)


def handle_screen_shown(screen: HubScreenProtocol) -> None:
    """Handler chamado quando a tela do Hub fica visível (navegação de volta).

    Garante:
    - Live-sync ativo
    - Renderização imediata dos dados em cache (se histórico vazio)
    - Reset e refresh do cache de autores

    Args:
        screen: Instância do HubScreen
    """
    # 1) Iniciar live-sync
    try:
        screen._start_live_sync()
    except Exception as e:
        logger.warning(f"Erro ao iniciar live-sync no on_show: {e}")

    # 2) Renderizar notas em cache se histórico vazio
    try:
        is_empty = screen.notes_history.index("end-1c") == "1.0"
    except Exception:
        is_empty = True

    if is_empty and screen.state.notes_last_data:
        try:
            screen.render_notes(screen.state.notes_last_data, force=True)
        except Exception as e:
            logger.warning(f"Erro ao renderizar notas no on_show: {e}")

    # 3) Resetar e atualizar cache de autores
    try:
        # MF-19: Usar método público do HubScreen (que usa StateManager)
        screen.clear_author_cache()
        screen._last_org_for_names = None
        screen._refresh_author_names_cache_async(force=True)
    except Exception as e:
        logger.warning(f"Erro ao atualizar cache de nomes no on_show: {e}")
