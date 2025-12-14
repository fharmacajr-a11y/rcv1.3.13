# -*- coding: utf-8 -*-
"""HubAuthorsCacheFacade - Centraliza lógica de cache de autores do HubScreen.

MF-25: Extrai métodos de cache de autores (refresh, clear, pending fetches) do HubScreen
para um facade dedicado, seguindo o padrão estabelecido em MF-22, MF-23 e MF-24.

Responsabilidades:
- Atualizar cache de nomes de autores (async)
- Limpar cache de autores
- Gerenciar estado de pendências de fetch (add/remove pending fetches)
- Gerenciar flag de "cache carregado"
- Integração com HubPollingService (refresh) e HubStateManager (state)

Padrão de Design: Facade (Gang of Four)
- Simplifica interface de subsistemas complexos (polling, state management)
- Encapsula múltiplas dependências (polling_service, state_manager)
- Mantém HubScreen como thin orchestrator

Histórico: MF-25
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from src.modules.hub.services.hub_polling_service import HubPollingService
    from src.modules.hub.hub_state_manager import HubStateManager

logger = logging.getLogger(__name__)


class HubAuthorsCacheFacade:
    """MF-25: Facade para operações de cache de autores do HubScreen.

    Encapsula toda a lógica relacionada a:
    - Refresh assíncrono de cache de nomes de autores
    - Limpeza de cache
    - Gerenciamento de fetches pendentes
    - Estado de cache carregado

    Segue padrão estabelecido em:
    - MF-22: HubNavigationFacade, HubDashboardFacade
    - MF-23: HubNotesFacade
    - MF-24: HubLifecycleFacade
    """

    def __init__(
        self,
        polling_service: "HubPollingService",
        state_manager: "HubStateManager",
        get_org_id: Callable[[], Optional[str]],
        auth_ready_callback: Callable[[], bool],
        debug_logger: Optional[Any] = None,
    ):
        """Inicializa HubAuthorsCacheFacade com dependências injetadas.

        Args:
            polling_service: Serviço de polling (MF-14) para refresh de cache
            state_manager: Gerenciador de estado (MF-19) para operações de cache
            get_org_id: Callback para obter org_id
            auth_ready_callback: Callback para verificar se auth está pronta
            debug_logger: Logger opcional para debug
        """
        self._polling_service = polling_service
        self._state_manager = state_manager
        self._get_org_id = get_org_id
        self._auth_ready_callback = auth_ready_callback
        self._debug_logger = debug_logger

    # ==============================================================================
    # REFRESH DE CACHE (atualização assíncrona)
    # ==============================================================================

    def refresh_author_names_cache(self, force: bool = False) -> None:
        """Atualiza cache de nomes de autores async (MF-14, MF-25).

        Delega para HubPollingService.refresh_authors_cache(), que por sua vez
        chama HubScreenController.refresh_author_names_cache_async().

        Args:
            force: Se True, ignora cooldown e força atualização
        """
        try:
            self._polling_service.refresh_authors_cache(force=force)
            self._log_debug(f"Cache de autores refresh solicitado (force={force})")
        except Exception as e:
            logger.exception("Erro ao atualizar cache de autores")
            if self._debug_logger:
                self._debug_logger(f"[HubAuthorsCacheFacade] Erro ao refresh cache: {e}")

    # ==============================================================================
    # CLEAR DE CACHE (limpeza completa)
    # ==============================================================================

    def clear_author_cache(self) -> None:
        """Limpa cache de autores (MF-19, MF-25).

        Delega para HubStateManager.clear_author_cache().
        """
        try:
            self._state_manager.clear_author_cache()
            self._log_debug("Cache de autores limpo")
        except Exception as e:
            logger.exception("Erro ao limpar cache de autores")
            if self._debug_logger:
                self._debug_logger(f"[HubAuthorsCacheFacade] Erro ao limpar cache: {e}")

    # ==============================================================================
    # GERENCIAMENTO DE PENDÊNCIAS (fetches em andamento)
    # ==============================================================================

    def add_pending_name_fetch(self, email: str) -> None:
        """Adiciona email ao set de fetches pendentes (MF-19, MF-25).

        Usado para evitar fetches duplicados simultâneos do mesmo autor.

        Args:
            email: Email do autor sendo buscado
        """
        try:
            self._state_manager.add_pending_name_fetch(email)
            self._log_debug(f"Email adicionado às pendências: {email}")
        except Exception as e:
            logger.exception(f"Erro ao adicionar pending fetch para {email}")
            if self._debug_logger:
                self._debug_logger(f"[HubAuthorsCacheFacade] Erro ao add pending: {e}")

    def remove_pending_name_fetch(self, email: str) -> None:
        """Remove email do set de fetches pendentes (MF-19, MF-25).

        Chamado quando fetch completa (sucesso ou falha).

        Args:
            email: Email do autor cuja busca terminou
        """
        try:
            self._state_manager.remove_pending_name_fetch(email)
            self._log_debug(f"Email removido das pendências: {email}")
        except Exception as e:
            logger.exception(f"Erro ao remover pending fetch para {email}")
            if self._debug_logger:
                self._debug_logger(f"[HubAuthorsCacheFacade] Erro ao remove pending: {e}")

    # ==============================================================================
    # ESTADO DE CACHE CARREGADO (flag de carregamento)
    # ==============================================================================

    def set_names_cache_loaded(self, loaded: bool) -> None:
        """Define estado de cache de nomes carregado (MF-19, MF-25).

        Indica se o cache inicial de autores foi carregado pelo menos uma vez.

        Args:
            loaded: True se cache foi carregado, False caso contrário
        """
        try:
            self._state_manager.set_names_cache_loaded(loaded)
            self._log_debug(f"Estado de cache carregado definido: {loaded}")
        except Exception as e:
            logger.exception("Erro ao definir estado de cache carregado")
            if self._debug_logger:
                self._debug_logger(f"[HubAuthorsCacheFacade] Erro ao set loaded: {e}")

    # ==============================================================================
    # UTILIDADES PRIVADAS
    # ==============================================================================

    def _log_debug(self, message: str) -> None:
        """Log de debug (opcional)."""
        if self._debug_logger:
            self._debug_logger(f"[HubAuthorsCacheFacade] {message}")
        logger.debug(message)
