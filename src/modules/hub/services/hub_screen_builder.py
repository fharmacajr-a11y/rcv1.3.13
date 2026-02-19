# -*- coding: utf-8 -*-
"""MF-22: HubScreenBuilder - Extrai lógica de inicialização do HubScreen.

Este módulo é responsável por construir e configurar um HubScreen,
extraindo a lógica complexa de _init_state para um builder dedicado.

Responsabilidades:
- Inicializar HubState e StateManager
- Configurar callbacks de navegação
- Criar componentes via HubComponentFactory
- Injetar dependências no HubScreen

Benefícios:
- Reduz complexidade de _init_state (~50-80 linhas removidas)
- Centraliza lógica de construção/inicialização
- Facilita testes de setup
- Melhora legibilidade do HubScreen
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from src.modules.hub.views.hub_screen import HubScreen
    from src.modules.hub.state import HubState

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


from src.modules.hub.state import ensure_state
from src.modules.hub.hub_state_manager import HubStateManager
from src.modules.hub.services.hub_component_factory import HubComponentFactory, HubComponents

logger = get_logger(__name__)

# Constantes (compatibilidade)
AUTH_RETRY_MS = 2000  # 2 segundos


class HubScreenBuilder:
    """MF-22: Responsável por construir e configurar um HubScreen.

    Este builder encapsula toda a lógica de inicialização que anteriormente
    estava em _init_state, incluindo:
    - Setup de state e state manager
    - Configuração de callbacks
    - Criação de componentes via factory
    - Injeção de dependências

    Args:
        logger_instance: Logger opcional (usa logger do módulo se None)
    """

    def __init__(self, logger_instance: Optional[Any] = None):
        """Inicializa builder.

        Args:
            logger_instance: Logger opcional
        """
        self._logger = logger_instance or logger

    def build(
        self,
        screen: HubScreen,
        *,
        open_clientes: Optional[Callable[[], None]] = None,
        open_auditoria: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_sngpc: Optional[Callable[[], None]] = None,
        open_mod_sifap: Optional[Callable[[], None]] = None,
        open_cashflow: Optional[Callable[[], None]] = None,
        open_sites: Optional[Callable[[], None]] = None,
    ) -> HubComponents:
        """Constrói e configura o HubScreen.

        Args:
            screen: Instância do HubScreen a ser configurada
            open_*: Callbacks de navegação para módulos externos

        Returns:
            HubComponents com todos os componentes criados

        Raises:
            Exception: Se componentes não puderem ser criados (fatal)
        """
        # 1. Configurar constantes e state
        screen.AUTH_RETRY_MS = AUTH_RETRY_MS
        state = ensure_state(screen)
        state.auth_retry_ms = AUTH_RETRY_MS
        screen._hub_state = state

        self._logger.debug("HubScreenBuilder: Estado base configurado")

        # 2. Criar StateManager (MF-19)
        screen._state_manager = HubStateManager(state)
        self._logger.debug("HubScreenBuilder: StateManager criado")

        # 3. Configurar callbacks de navegação (MF-16)
        self._setup_navigation_callbacks(
            screen,
            open_clientes=open_clientes,
            open_farmacia_popular=open_farmacia_popular,
            open_sngpc=open_sngpc,
            open_mod_sifap=open_mod_sifap,
            open_cashflow=open_cashflow,
            open_sites=open_sites,
        )

        # 4. Inicializar campos do state
        self._init_state_fields(screen, state)
        self._logger.debug("HubScreenBuilder: Campos de estado inicializados")

        # 5. Criar componentes via factory
        factory = HubComponentFactory(logger=self._logger)

        try:
            components = factory.create_components(
                screen=screen,
                open_clientes=open_clientes,
                open_farmacia_popular=open_farmacia_popular,
                open_sngpc=open_sngpc,
                open_mod_sifap=open_mod_sifap,
                open_cashflow=open_cashflow,
                open_sites=open_sites,
            )

            self._logger.debug("HubScreenBuilder: Componentes criados via factory")
            return components

        except Exception as e:
            self._logger.error(f"HubScreenBuilder FATAL: Componentes não puderam ser criados: {e}")
            raise  # MF-22: Falha fatal - Hub não funciona sem componentes

    def _setup_navigation_callbacks(
        self,
        screen: HubScreen,
        *,
        open_clientes: Optional[Callable[[], None]] = None,
        open_auditoria: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_sngpc: Optional[Callable[[], None]] = None,
        open_mod_sifap: Optional[Callable[[], None]] = None,
        open_cashflow: Optional[Callable[[], None]] = None,
        open_sites: Optional[Callable[[], None]] = None,
    ) -> None:
        """Configura callbacks de navegação no HubScreen.

        Args:
            screen: Instância do HubScreen
            open_*: Callbacks de navegação
        """
        # MF-16: Criar estrutura de callbacks
        from src.modules.hub.infrastructure.hub_navigation_callbacks import HubNavigationCallbacks

        screen._nav_callbacks = HubNavigationCallbacks(
            open_clientes=open_clientes,
            open_farmacia_popular=open_farmacia_popular,
            open_sngpc=open_sngpc,
            open_mod_sifap=open_mod_sifap,
            open_cashflow=open_cashflow,
            open_sites=open_sites,
        )

        # MF-16: Manter atributos públicos individuais para compatibilidade
        screen.open_clientes = open_clientes
        screen.open_farmacia_popular = open_farmacia_popular
        screen.open_sngpc = open_sngpc
        screen.open_mod_sifap = open_mod_sifap
        screen.open_cashflow = open_cashflow
        screen.open_sites = open_sites

        self._logger.debug("HubScreenBuilder: Callbacks de navegação configurados")

    def _init_state_fields(self, screen: HubScreen, state: HubState) -> None:
        """Inicializa campos do HubState.

        Args:
            screen: Instância do HubScreen
            state: HubState a ser inicializado
        """
        # Estado de polling
        state.notes_poll_ms = getattr(state, "notes_poll_ms", 10000)
        state.notes_retry_ms = getattr(state, "notes_retry_ms", 60000)
        state.notes_last_snapshot = getattr(state, "notes_last_snapshot", None)
        state.notes_last_data = getattr(state, "notes_last_data", None)
        state.notes_table_missing = getattr(state, "notes_table_missing", False)
        state.notes_table_missing_notified = getattr(state, "notes_table_missing_notified", False)
        state.polling_active = getattr(state, "polling_active", False)

        # Alias local mínimo (compatibilidade)
        screen._notes_poll_ms = 10000  # 10 segundos

        # Cache de nomes de autores
        state.author_cache = getattr(state, "author_cache", {}) or {}
        state.email_prefix_map = getattr(state, "email_prefix_map", {}) or {}
        state.names_cache_loaded = getattr(state, "names_cache_loaded", False)
        state.names_refreshing = getattr(state, "names_refreshing", False)
        state.names_cache_loading = getattr(state, "names_cache_loading", False)
        state.pending_name_fetch = getattr(state, "pending_name_fetch", set()) or set()
        state.last_names_cache_hash = getattr(state, "last_names_cache_hash", None)
        state.last_render_hash = getattr(state, "last_render_hash", None)

        # Aliases locais mínimos
        screen._names_last_refresh = 0.0
        screen._last_org_for_names = state.last_org_for_names
        screen._last_render_hash = state.last_render_hash

        # Live sync
        state.live_sync_on = getattr(state, "live_sync_on", False)
        state.live_org_id = getattr(state, "live_org_id", None)
        state.live_channel = getattr(state, "live_channel", None)
        state.live_last_ts = getattr(state, "live_last_ts", None)
