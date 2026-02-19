# -*- coding: utf-8 -*-
"""HubLifecycleFacade - Centraliza lógica de lifecycle do HubScreen.

MF-24: Extrai métodos de lifecycle (polling, live sync, timers) do HubScreen
para um facade dedicado, seguindo o padrão estabelecido em MF-22 e MF-23.

Responsabilidades:
- Live sync (start/stop)
- Polling (start/stop)
- Timers e agendamento de atualizações
- Eventos de ciclo de vida (on_show)
- Integração com serviços de lifecycle (HubLifecycleManager, HubPollingService)

Padrão de Design: Facade (Gang of Four)
- Simplifica interface de subsistemas complexos (lifecycle, polling, timers)
- Encapsula múltiplas dependências (lifecycle_manager, polling_service, etc.)
- Mantém HubScreen como thin orchestrator

Histórico: MF-24
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from src.modules.hub.views.hub_lifecycle_manager import HubLifecycleManager
    from src.modules.hub.services.hub_lifecycle_impl import HubLifecycleImpl
    from src.modules.hub.services.hub_polling_service import HubPollingService
    from src.modules.hub.hub_state_manager import HubStateManager

logger = logging.getLogger(__name__)


class HubLifecycleFacade:
    """MF-24: Facade para operações de lifecycle do HubScreen.

    Encapsula toda a lógica relacionada a:
    - Ciclo de vida (start/stop polling e timers)
    - Live sync de notas
    - Agendamento de atualizações
    - Eventos de exibição da tela

    Segue padrão estabelecido em:
    - MF-22: HubNavigationFacade, HubDashboardFacade
    - MF-23: HubNotesFacade
    """

    def __init__(
        self,
        parent: Any,
        lifecycle_manager: Optional["HubLifecycleManager"],
        lifecycle_impl: "HubLifecycleImpl",
        polling_service: "HubPollingService",
        state_manager: "HubStateManager",
        auth_ready_callback: Callable[[], bool],
        get_org_id: Callable[[], Optional[str]],
        get_email: Callable[[], Optional[str]],
        start_live_sync_callback: Callable[[], None],
        render_notes_callback: Callable[[Any, bool], None],
        refresh_author_cache_callback: Callable[[bool], None],
        clear_author_cache_callback: Callable[[], None],
        debug_logger: Optional[Any] = None,
    ):
        """Inicializa HubLifecycleFacade com dependências injetadas.

        Args:
            parent: Referência ao HubScreen (para acesso ao state)
            lifecycle_manager: Gerenciador de lifecycle (MF-28)
            lifecycle_impl: Implementação de lifecycle (MF-15)
            polling_service: Serviço de polling (MF-14)
            state_manager: Gerenciador de estado (MF-19)
            auth_ready_callback: Callback para verificar se auth está pronta
            get_org_id: Callback para obter org_id
            get_email: Callback para obter email
            start_live_sync_callback: Callback para iniciar live sync
            render_notes_callback: Callback para renderizar notas
            refresh_author_cache_callback: Callback para atualizar cache de autores
            clear_author_cache_callback: Callback para limpar cache de autores
            debug_logger: Logger opcional para debug
        """
        self._parent = parent
        self._lifecycle_manager = lifecycle_manager
        self._lifecycle_impl = lifecycle_impl
        self._polling_service = polling_service
        self._state_manager = state_manager
        self._auth_ready_callback = auth_ready_callback
        self._get_org_id = get_org_id
        self._get_email = get_email
        self._start_live_sync_callback = start_live_sync_callback
        self._render_notes_callback = render_notes_callback
        self._refresh_author_cache_callback = refresh_author_cache_callback
        self._clear_author_cache_callback = clear_author_cache_callback
        self._debug_logger = debug_logger

    # ==============================================================================
    # LIVE SYNC (start/stop)
    # ==============================================================================

    def start_live_sync_impl(self) -> None:
        """Inicia sync de notas (MF-15)."""
        try:
            self._lifecycle_impl.start_live_sync()
            self._log_debug("Live sync iniciado")
        except Exception as e:
            logger.exception("Erro ao iniciar live sync")
            if self._debug_logger:
                self._debug_logger(f"[HubLifecycleFacade] Erro ao iniciar live sync: {e}")

    def stop_live_sync_impl(self) -> None:
        """Para sync (MF-15)."""
        try:
            self._lifecycle_impl.stop_live_sync()
            self._log_debug("Live sync parado")
        except Exception as e:
            logger.exception("Erro ao parar live sync")
            if self._debug_logger:
                self._debug_logger(f"[HubLifecycleFacade] Erro ao parar live sync: {e}")

    def start_live_sync(self) -> None:
        """Alias de compatibilidade para start_live_sync_impl."""
        return self.start_live_sync_impl()

    # ==============================================================================
    # POLLING (start/stop)
    # ==============================================================================

    def start_polling(self) -> None:
        """Inicia polling e timers (MF-28, MF-19)."""
        try:
            self._state_manager.set_polling_active(True)
            if self._lifecycle_manager is not None:
                self._lifecycle_manager.start()
                self._log_debug("Polling iniciado")
        except Exception as e:
            logger.exception("Erro ao iniciar polling")
            if self._debug_logger:
                self._debug_logger(f"[HubLifecycleFacade] Erro ao iniciar polling: {e}")

    def stop_polling(self) -> None:
        """Para polling e timers (MF-28, MF-19)."""
        try:
            self._state_manager.set_polling_active(False)
            if self._lifecycle_manager is not None:
                self._lifecycle_manager.stop()
                self._log_debug("Polling parado")
        except Exception as e:
            logger.exception("Erro ao parar polling")
            if self._debug_logger:
                self._debug_logger(f"[HubLifecycleFacade] Erro ao parar polling: {e}")

    # ==============================================================================
    # TIMERS (start/schedule)
    # ==============================================================================

    def start_timers(self) -> None:
        """Inicia lifecycle do HUB (MF-28: delega para HubLifecycleManager)."""
        try:
            if self._lifecycle_manager is not None:
                self._lifecycle_manager.start()
                self._log_debug("Timers do lifecycle iniciados")
        except Exception as e:
            logger.exception("Erro ao iniciar timers")
            if self._debug_logger:
                self._debug_logger(f"[HubLifecycleFacade] Erro ao iniciar timers: {e}")

    def schedule_poll(self, delay_ms: int = 6000) -> None:
        """Agenda polling fallback (MF-14)."""
        try:
            self._polling_service.schedule_next_poll(delay_ms=delay_ms)
            self._log_debug(f"Polling agendado para {delay_ms}ms")
        except Exception as e:
            logger.exception("Erro ao agendar polling")
            if self._debug_logger:
                self._debug_logger(f"[HubLifecycleFacade] Erro ao agendar polling: {e}")

    # ==============================================================================
    # ON_SHOW (evento de exibição da tela)
    # ==============================================================================

    def on_show(self) -> None:
        """Chamado quando a tela fica visível. Delega ao lifecycle service.

        MF-24: Implementa lógica de handle_screen_shown inline para reduzir
        dependências externas e manter facade autossuficiente.

        Garante:
        - Live-sync ativo
        - Renderização imediata dos dados em cache (se histórico vazio)
        - Reset e refresh do cache de autores
        """
        # 1) Iniciar live-sync
        try:
            self._start_live_sync_callback()
            self._log_debug("Live sync iniciado em on_show")
        except Exception as e:
            logger.warning(f"Erro ao iniciar live-sync no on_show: {e}")

        # 2) Renderizar notas em cache se histórico vazio
        try:
            # Acessa notes_history via parent
            notes_history = getattr(self._parent, "notes_history", None)
            is_empty = True
            if notes_history is not None:
                try:
                    is_empty = notes_history.index("end-1c") == "1.0"
                except Exception:
                    is_empty = True

            # Acessa state.notes_last_data via parent
            state = getattr(self._parent, "state", None)
            if is_empty and state is not None and state.notes_last_data:
                self._render_notes_callback(state.notes_last_data, True)
                self._log_debug("Notas renderizadas em on_show")
        except Exception as e:
            logger.warning(f"Erro ao renderizar notas no on_show: {e}")

        # 3) Resetar e atualizar cache de autores
        try:
            self._clear_author_cache_callback()
            # Reset _last_org_for_names
            if hasattr(self._parent, "_last_org_for_names"):
                self._parent._last_org_for_names = None
            self._refresh_author_cache_callback(True)
            self._log_debug("Cache de autores atualizado em on_show")
        except Exception as e:
            logger.warning(f"Erro ao atualizar cache de nomes no on_show: {e}")

    # ==============================================================================
    # UTILIDADES PRIVADAS
    # ==============================================================================

    def _log_debug(self, message: str) -> None:
        """Log de debug (opcional)."""
        if self._debug_logger:
            self._debug_logger(f"[HubLifecycleFacade] {message}")
        logger.debug(message)
