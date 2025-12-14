# -*- coding: utf-8 -*-
"""HubLifecycleManager: facade/wrapper para gerenciamento de lifecycle do Hub.

MF-28: Este módulo encapsula o HubLifecycle existente, fornecendo uma API
simplificada de start/stop para o HubScreen, completando a decomposição do
monolito em componentes especializados.

Responsabilidades:
- Encapsular instância de HubLifecycle
- Fornecer API pública unificada (start/stop)
- Manter controle de estado de polling
- Isolar HubScreen da complexidade interna de timers

Não contém lógica de negócio - delega para HubLifecycle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.modules.hub.views.hub_screen import HubScreen

from src.modules.hub.hub_lifecycle import HubLifecycle


class HubLifecycleManager:
    """Manager/facade para lifecycle do Hub (timers, polling, live sync).

    Encapsula HubLifecycle e fornece API simplificada para HubScreen.

    Uso:
        manager = HubLifecycleManager(tk_root=hub_screen, logger=logger)
        manager.start()  # Inicia todos os timers/polling
        manager.stop()   # Para todos os timers/polling
    """

    def __init__(
        self,
        tk_root: "HubScreen",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Inicializa o manager de lifecycle.

        Args:
            tk_root: Referência ao HubScreen (para tk.after e callbacks)
            logger: Logger opcional para debug/erro
        """
        self._tk_root = tk_root
        self._logger = logger
        self._polling_active = False

        # HubLifecycle: gerenciamento real de timers/polling
        self._lifecycle = HubLifecycle(tk_root=tk_root, logger=logger)

    def start(self) -> None:
        """Inicia o lifecycle do Hub: timers, polling, live sync.

        Idempotente: chamar múltiplas vezes não causa side-effects.
        """
        if self._polling_active:
            if self._logger:
                self._logger.debug("[HubLifecycleManager] Lifecycle já ativo, ignorando start()")
            return

        self._polling_active = True

        if self._logger:
            self._logger.debug("[HubLifecycleManager] Iniciando lifecycle")

        # Delegar para HubLifecycle
        self._lifecycle.start()

    def stop(self) -> None:
        """Para o lifecycle do Hub: cancela todos os timers e live sync.

        Idempotente: chamar múltiplas vezes não causa side-effects.
        """
        if not self._polling_active:
            return

        self._polling_active = False

        if self._logger:
            self._logger.debug("[HubLifecycleManager] Parando lifecycle")

        # Delegar para HubLifecycle
        try:
            self._lifecycle.stop()
        except Exception as e:
            if self._logger:
                self._logger.warning(f"[HubLifecycleManager] Erro ao parar lifecycle: {e}")

    @property
    def is_active(self) -> bool:
        """Indica se o lifecycle está ativo."""
        return self._polling_active

    @property
    def lifecycle(self) -> HubLifecycle:
        """Acesso ao HubLifecycle interno (para casos avançados)."""
        return self._lifecycle
