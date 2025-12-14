# -*- coding: utf-8 -*-
"""Hub Lifecycle Implementation - Extração da lógica de lifecycle do HubScreen.

═══════════════════════════════════════════════════════════════════════════════
MF-15: Extrair Lifecycle Implementation
═══════════════════════════════════════════════════════════════════════════════

Este módulo centraliza a implementação de lifecycle do HUB, anteriormente
espalhada em HubScreen:

RESPONSABILIDADES:
- Iniciar/parar live sync (Realtime + polling fallback)
- Iniciar timers "home" com segurança (verificar auth)
- Coordenar com HubPollingService para polling de notas
- Gerenciar estado de lifecycle (cache de autores, flags)

BENEFÍCIOS DA EXTRAÇÃO:
1. Reduz complexidade de hub_screen.py (~40 linhas)
2. Centraliza lógica de lifecycle em um único lugar
3. Facilita testes unitários (serviço isolado)
4. Melhora separação de concerns (HubScreen = UI, Service = lifecycle logic)

ARQUITETURA:
- HubLifecycleImpl coordena quando/como iniciar lifecycle
- HubScreenController executa ações (setup_realtime, stop_realtime)
- HubPollingService gerencia polling de notas e cache
- HubLifecycle agenda timers periódicos

DEPENDÊNCIAS:
- HubScreenController (para realtime)
- HubPollingService (para polling)
- HubState (para armazenar estado)

STATUS: Criado na MF-15 (Dezembro/2025)
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.modules.hub.state import HubState
    from src.modules.hub.hub_screen_controller import HubScreenController
    from src.modules.hub.services.hub_polling_service import HubPollingService


class HubLifecycleCallbacks(Protocol):
    """Protocolo para callbacks necessários pelo serviço de lifecycle.

    MF-15: Define interface mínima que HubScreen deve implementar.
    """

    @property
    def state(self) -> HubState:
        """Estado do HUB (contém flags de lifecycle, cache, etc.)."""
        ...

    @property
    def _hub_controller(self) -> HubScreenController:
        """Controller (para executar setup/stop realtime)."""
        ...

    @property
    def _polling_service(self) -> HubPollingService:
        """Polling service (para iniciar/parar polling)."""
        ...

    def _auth_ready(self) -> bool:
        """Verifica se autenticação está pronta."""
        ...

    def _update_notes_ui_state(self) -> None:
        """Atualiza estado da UI de notas (botão, placeholder)."""
        ...


logger = logging.getLogger(__name__)


class HubLifecycleImpl:
    """Serviço de implementação de lifecycle do HUB.

    MF-15: Centraliza lógica de lifecycle que estava em HubScreen.

    Responsabilidades:
    - Iniciar live sync (realtime + polling fallback)
    - Parar live sync
    - Iniciar timers home com segurança (verificar auth)

    NÃO faz:
    - Agendamento de timers (delega para HubLifecycle)
    - Polling em si (delega para HubPollingService)
    - Setup realtime (delega para HubScreenController)
    """

    def __init__(self, callbacks: HubLifecycleCallbacks) -> None:
        """Inicializa o serviço de lifecycle.

        Args:
            callbacks: Objeto que implementa HubLifecycleCallbacks (normalmente HubScreen)
        """
        self._callbacks = callbacks
        self._logger = logger

    def start_live_sync(self) -> None:
        """Inicia sync de notas: Realtime + fallback polling.

        MF-15: Extraído de HubScreen._start_live_sync_impl.

        Ações:
        1. Chama controller para setup realtime
        2. Polling fallback é gerenciado automaticamente pelo realtime
        """
        try:
            self._log_debug("Iniciando live sync (Realtime + fallback polling)")
            # Delegar para HubScreenController (facade para realtime)
            self._callbacks._hub_controller.setup_realtime()
        except Exception as e:
            self._log_error(f"Erro ao iniciar live sync: {e}")

    def stop_live_sync(self) -> None:
        """Para sync de notas (sair do Hub, logout).

        MF-15: Extraído de HubScreen._stop_live_sync_impl.

        Ações:
        1. Chama controller para stop realtime
        2. Cancela subscriptions
        """
        try:
            self._log_debug("Parando live sync")
            # Delegar para HubScreenController (facade para realtime)
            self._callbacks._hub_controller.stop_realtime()
        except Exception as e:
            self._log_error(f"Erro ao parar live sync: {e}")

    def start_home_timers_safely(self) -> bool:
        """Inicia timers home apenas quando autenticação estiver pronta.

        MF-15: Extraído de HubScreen._start_home_timers_safely_impl.

        Ações:
        1. Verifica se auth está pronta
        2. Reseta cache de autores (troca de conta/login)
        3. Atualiza estado da UI de notas
        4. Inicia polling de notas via HubPollingService

        Returns:
            True se auth pronta e timers iniciados, False caso contrário.
        """
        # Verificar auth
        if not self._callbacks._auth_ready():
            self._log_debug("Autenticação ainda não pronta, aguardando...")
            return False

        self._log_debug("Autenticação pronta, iniciando timers home")

        try:
            state = self._callbacks.state

            # Forçar recarga do cache de nomes ao trocar de conta/login
            state.names_cache_loaded = False
            state.author_cache = {}
            state.email_prefix_map = {}
            state.last_org_for_names = None

            # Atualizar estado da UI de notas (botão, placeholder)
            self._callbacks._update_notes_ui_state()

            # Iniciar polling de notas (delega para HubPollingService)
            self._callbacks._polling_service.start_notes_polling()

            return True

        except Exception as e:
            self._log_error(f"Erro ao iniciar timers home: {e}")
            return False

    # ============================================================================
    # HELPERS DE LOG
    # ============================================================================

    def _log_debug(self, message: str) -> None:
        """Log de debug."""
        self._logger.debug(f"[HubLifecycleImpl] {message}")

    def _log_error(self, message: str) -> None:
        """Log de erro."""
        self._logger.error(f"[HubLifecycleImpl] {message}")
