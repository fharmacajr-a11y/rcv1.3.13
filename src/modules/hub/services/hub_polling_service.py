# -*- coding: utf-8 -*-
"""Hub Polling Service - Consolidação da lógica de polling de notas e cache de autores.

═══════════════════════════════════════════════════════════════════════════════
MF-14: Consolidar Lógica de Polling
═══════════════════════════════════════════════════════════════════════════════

Este módulo centraliza toda a lógica de polling do HUB, anteriormente espalhada
em HubScreen e HubLifecycle:

RESPONSABILIDADES:
- Iniciar/parar polling de notas
- Coordenar refresh de cache de autores
- Verificar cooldowns e condições (auth, online)
- Agendar próximas execuções via callbacks

BENEFÍCIOS DA CONSOLIDAÇÃO:
1. Reduz complexidade de hub_screen.py (~50 linhas)
2. Centraliza lógica de scheduling/cooldown em um único lugar
3. Facilita testes unitários (serviço isolado)
4. Melhora separação de concerns (HubScreen = UI, Service = polling logic)

ARQUITETURA:
- HubPollingService coordena quando/como fazer polling
- HubScreenController executa ações (refresh_notes, refresh_authors_cache)
- HubLifecycle agenda timers periódicos (schedule_notes_poll, schedule_authors_refresh)

DEPENDÊNCIAS:
- HubScreenController (para executar refresh)
- HubLifecycle (para agendar timers)
- HubState (para armazenar estado de polling)

STATUS: Criado na MF-14 (Dezembro/2025)
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.modules.hub.state import HubState
    from src.modules.hub.hub_lifecycle import HubLifecycle
    from src.modules.hub.hub_screen_controller import HubScreenController


class HubPollingCallbacks(Protocol):
    """Protocolo para callbacks necessários pelo serviço de polling.

    MF-14: Define interface mínima que HubScreen deve implementar.
    """

    @property
    def state(self) -> HubState:
        """Estado do HUB (contém polling_active, flags, etc.)."""
        ...

    @property
    def _lifecycle(self) -> HubLifecycle:
        """Lifecycle manager (para agendar timers)."""
        ...

    @property
    def _hub_controller(self) -> HubScreenController:
        """Controller (para executar refresh)."""
        ...

    def refresh_notes_async(self, *, force: bool = False) -> None:
        """Método público de refresh de notas."""
        ...


logger = logging.getLogger(__name__)


class HubPollingService:
    """Serviço de polling de notas e cache de autores.

    MF-14: Centraliza lógica de polling que estava em HubScreen.

    Responsabilidades:
    - Iniciar polling (verificar auth, agendar refresh)
    - Coordenar refresh de cache de autores
    - Executar polling de notas
    - Agendar próximas execuções

    NÃO faz:
    - Implementação de refresh (delega para HubScreenController)
    - Agendamento de timers (delega para HubLifecycle)
    """

    def __init__(self, callbacks: HubPollingCallbacks) -> None:
        """Inicializa o serviço de polling.

        Args:
            callbacks: Objeto que implementa HubPollingCallbacks (normalmente HubScreen)
        """
        self._callbacks = callbacks
        self._logger = logger

    def start_notes_polling(self, *, force: bool = False) -> None:
        """Inicia polling de atualizações de notas e refresh de cache de autores.

        MF-14: Extraído de HubScreen._start_notes_polling.

        Ações:
        1. Marca polling_active = True
        2. Força refresh do cache de autores
        3. Força refresh inicial de notas
        4. Agenda polling periódico de authors
        5. Agenda polling periódico de notas

        Args:
            force: Se True, força refresh mesmo se já ativo
        """
        state = self._callbacks.state

        # Já está ativo? (skip se não forçado)
        if state.polling_active and not force:
            self._log_debug("Polling já ativo, skip")
            return

        state.polling_active = True
        self._log_debug("Iniciando polling de notas e cache de autores")

        try:
            # 1. Carregar cache de nomes na primeira vez
            self.refresh_authors_cache(force=True)

            # 2. Refresh inicial de notas
            self._callbacks.refresh_notes_async(force=True)

            # 3. Agendar refresh periódico de authors
            self._callbacks._lifecycle.schedule_authors_refresh()

            # 4. Agendar polling periódico de notas
            self._callbacks._lifecycle.schedule_notes_poll()

        except Exception as e:
            self._log_error(f"Erro ao iniciar polling: {e}")
            state.polling_active = False

    def refresh_authors_cache(self, force: bool = False) -> None:
        """Atualiza cache de nomes de autores (profiles.display_name) de forma assíncrona.

        MF-14: Extraído de HubScreen._refresh_author_names_cache_impl.

        Chamado por HubLifecycle periodicamente.

        Args:
            force: Se True, ignora cooldown e força atualização
        """
        try:
            # Delegar para HubScreenController (facade para hub_async_tasks_service)
            self._callbacks._hub_controller.refresh_author_names_cache_async(force=force)
        except Exception as e:
            self._log_error(f"Erro ao refresh cache de autores: {e}")

    def poll_notes(self, force: bool = False) -> None:
        """Executa polling de notas (uma iteração).

        MF-14: Extraído de HubScreen._poll_notes_impl.

        Chamado por HubLifecycle periodicamente.

        Args:
            force: Se True, força refresh ignorando cooldowns
        """
        try:
            # Delegar para HubScreenController
            self._callbacks._hub_controller.refresh_notes(force=force)
        except Exception as e:
            self._log_error(f"Erro no polling de notas: {e}")

    def schedule_next_poll(self, delay_ms: int = 6000) -> None:
        """Agenda próximo polling de notas (usado por live sync fallback).

        MF-14: Extraído de HubScreen._schedule_poll.

        Args:
            delay_ms: Delay em milissegundos até próximo poll
        """
        try:
            # Delegar para HubLifecycle (quem gerencia timers)
            self._callbacks._lifecycle.schedule_notes_poll(delay_ms=delay_ms)
        except Exception as e:
            self._log_error(f"Erro ao agendar polling: {e}")

    def stop_polling(self) -> None:
        """Para o polling de notas e cache.

        MF-14: Método novo para cleanup explícito.

        Útil ao sair do HUB ou fazer logout.
        """
        state = self._callbacks.state
        state.polling_active = False
        self._log_debug("Polling parado")

    # ============================================================================
    # HELPERS DE LOG
    # ============================================================================

    def _log_debug(self, message: str) -> None:
        """Log de debug."""
        self._logger.debug(f"[HubPollingService] {message}")

    def _log_error(self, message: str) -> None:
        """Log de erro."""
        self._logger.error(f"[HubPollingService] {message}")
