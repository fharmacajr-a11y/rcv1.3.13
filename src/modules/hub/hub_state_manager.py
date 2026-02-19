# -*- coding: utf-8 -*-
"""HubStateManager - Gerenciamento centralizado de estado do HubScreen.

MF-19: Extração do gerenciamento de estado do HubScreen.

Este módulo centraliza toda a lógica de mutação de estado do Hub, permitindo:
- Controle centralizado de mutações (evitar side-effects espalhados)
- Validação de transições de estado
- Debug e logging de mudanças de estado
- Testabilidade (mock/spy de mudanças)
- Encapsulamento (HubScreen não expõe estado mutável diretamente)

Filosofia:
- HubState continua sendo uma dataclass imutável (frozen=False para mutações controladas)
- HubStateManager é a única interface para modificar o estado
- Métodos de atualização são explícitos e documentados
- Leitura do estado é sempre via property read-only
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.modules.hub.state import AuthorCache, HubState

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)


__all__ = ["HubStateManager"]


logger = get_logger(__name__)


class HubStateManager:
    """Gerenciador centralizado de estado do HubScreen.

    MF-19: Centraliza todas as mutações de estado do Hub, fornecendo uma API
    clara e testável para modificar o estado interno.

    Responsabilidades:
    - Armazenar a instância de HubState
    - Fornecer métodos específicos para cada tipo de mutação
    - Validar transições de estado quando necessário
    - Logar mudanças importantes (opcional, para debug)

    Uso:
        manager = HubStateManager(HubState())
        manager.set_auth_ready(True)
        manager.update_author_cache({"user@example.com": ("John Doe", 123456.0)})
        current_state = manager.state  # read-only access
    """

    def __init__(self, initial_state: HubState) -> None:
        """Inicializa o manager com um estado inicial.

        Args:
            initial_state: Instância inicial de HubState
        """
        self._state = initial_state
        logger.debug("HubStateManager inicializado (MF-19)")

    # ═══════════════════════════════════════════════════════════════════════
    # Read-only State Access
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def state(self) -> HubState:
        """Acesso read-only ao estado atual.

        Returns:
            Instância atual de HubState (não deve ser modificada diretamente)
        """
        return self._state

    # ═══════════════════════════════════════════════════════════════════════
    # Auth & Loading State
    # ═══════════════════════════════════════════════════════════════════════

    def set_loading(self, is_loading: bool) -> None:
        """Define o estado de loading geral."""
        self._state.is_loading = is_loading

    def set_dashboard_loaded(self, loaded: bool) -> None:
        """Define o estado de dashboard carregado."""
        self._state.is_dashboard_loaded = loaded

    def set_notes_loaded(self, loaded: bool) -> None:
        """Define o estado de notas carregadas."""
        self._state.is_notes_loaded = loaded

    # ═══════════════════════════════════════════════════════════════════════
    # Organization & User Identity
    # ═══════════════════════════════════════════════════════════════════════

    def set_org_context(
        self,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> None:
        """Atualiza o contexto de organização e usuário.

        Args:
            org_id: ID da organização
            user_id: ID do usuário
            user_email: Email do usuário
            user_role: Role do usuário (admin, user, etc.)
        """
        if org_id is not None:
            self._state.org_id = org_id
        if user_id is not None:
            self._state.user_id = user_id
        if user_email is not None:
            self._state.user_email = user_email
        if user_role is not None:
            self._state.user_role = user_role

    # ═══════════════════════════════════════════════════════════════════════
    # Author Cache Management
    # ═══════════════════════════════════════════════════════════════════════

    def update_author_cache(self, cache: AuthorCache) -> None:
        """Atualiza o cache de autores (substitui completamente).

        Args:
            cache: Novo cache de autores {email -> (display_name, timestamp)}
        """
        self._state.author_cache = cache

    def merge_author_cache(self, updates: AuthorCache) -> None:
        """Faz merge de novos autores no cache existente.

        Args:
            updates: Dicionário com novos autores a adicionar/atualizar
        """
        if not self._state.author_cache:
            self._state.author_cache = {}
        self._state.author_cache.update(updates)

    def update_email_prefix_map(self, prefix_map: Dict[str, str]) -> None:
        """Atualiza o mapa de prefixos de email (notas legadas).

        Args:
            prefix_map: Mapa de prefixo -> email completo
        """
        self._state.email_prefix_map = prefix_map

    def set_names_cache_loaded(self, loaded: bool) -> None:
        """Define o estado de cache de nomes carregado."""
        self._state.names_cache_loaded = loaded

    def set_names_refreshing(self, refreshing: bool) -> None:
        """Define o estado de refresh de nomes em andamento."""
        self._state.names_refreshing = refreshing

    def set_names_cache_loading(self, loading: bool) -> None:
        """Define o estado de loading de cache de nomes."""
        self._state.names_cache_loading = loading

    def add_pending_name_fetch(self, email: str) -> None:
        """Adiciona um email ao set de fetches pendentes.

        Args:
            email: Email a ser adicionado
        """
        if not self._state.pending_name_fetch:
            self._state.pending_name_fetch = set()
        self._state.pending_name_fetch.add(email)

    def remove_pending_name_fetch(self, email: str) -> None:
        """Remove um email do set de fetches pendentes.

        Args:
            email: Email a ser removido
        """
        if self._state.pending_name_fetch:
            self._state.pending_name_fetch.discard(email)

    def clear_pending_name_fetch(self) -> None:
        """Limpa todos os fetches pendentes."""
        self._state.pending_name_fetch = set()

    def clear_author_cache(self) -> None:
        """Limpa completamente o cache de autores e mapa de prefixos."""
        self._state.author_cache = {}
        self._state.email_prefix_map = {}
        self._state.names_cache_loaded = False

    # ═══════════════════════════════════════════════════════════════════════
    # Notes State Management
    # ═══════════════════════════════════════════════════════════════════════

    def update_notes_data(
        self,
        notes: List[Dict[str, Any]],
        update_snapshot: bool = True,
    ) -> None:
        """Atualiza os dados de notas e opcionalmente o snapshot.

        Args:
            notes: Lista de notas
            update_snapshot: Se True, atualiza também notes_last_snapshot
        """
        self._state.notes_last_data = notes

        if update_snapshot:
            self._state.notes_last_snapshot = [(n.get("id"), n.get("created_at")) for n in notes]

    def set_notes_snapshot(self, snapshot: Optional[List[Tuple]]) -> None:
        """Define o snapshot de notas (id, created_at).

        Args:
            snapshot: Lista de tuplas (id, created_at)
        """
        self._state.notes_last_snapshot = snapshot

    def set_cached_notes(self, notes: List[Dict[str, Any]]) -> None:
        """Define as notas cacheadas.

        Args:
            notes: Lista de notas
        """
        self._state.cached_notes = notes

    # ═══════════════════════════════════════════════════════════════════════
    # Polling State Management
    # ═══════════════════════════════════════════════════════════════════════

    def set_polling_active(self, active: bool) -> None:
        """Define o estado de polling ativo.

        Args:
            active: True se polling está ativo
        """
        self._state.polling_active = active

    def set_notes_poll_interval(self, interval_ms: int) -> None:
        """Define o intervalo de polling de notas.

        Args:
            interval_ms: Intervalo em milissegundos
        """
        self._state.notes_poll_ms = interval_ms

    def set_notes_table_missing(self, missing: bool) -> None:
        """Define o estado de tabela de notas ausente.

        Args:
            missing: True se tabela está ausente
        """
        self._state.notes_table_missing = missing

    def set_notes_table_missing_notified(self, notified: bool) -> None:
        """Define se o erro de tabela ausente já foi notificado.

        Args:
            notified: True se já foi notificado
        """
        self._state.notes_table_missing_notified = notified

    # ═══════════════════════════════════════════════════════════════════════
    # Live Sync State Management
    # ═══════════════════════════════════════════════════════════════════════

    def set_live_sync_on(self, enabled: bool) -> None:
        """Define o estado de live sync.

        Args:
            enabled: True se live sync está habilitado
        """
        self._state.live_sync_on = enabled

    def set_live_org_id(self, org_id: Optional[str]) -> None:
        """Define o org_id do live sync.

        Args:
            org_id: ID da organização para live sync
        """
        self._state.live_org_id = org_id

    def set_live_channel(self, channel: Optional[Any]) -> None:
        """Define o canal de realtime.

        Args:
            channel: Canal de realtime
        """
        self._state.live_channel = channel

    def set_live_last_ts(self, timestamp: Optional[str]) -> None:
        """Define o timestamp da última nota conhecida (live sync).

        Args:
            timestamp: ISO timestamp
        """
        self._state.live_last_ts = timestamp

    def update_live_last_ts(self, new_ts: str) -> None:
        """Atualiza live_last_ts se o novo timestamp for maior.

        Args:
            new_ts: Novo ISO timestamp
        """
        current = self._state.live_last_ts or ""
        if new_ts > current:
            self._state.live_last_ts = new_ts

    # ═══════════════════════════════════════════════════════════════════════
    # Lifecycle State Management
    # ═══════════════════════════════════════════════════════════════════════

    def set_active(self, active: bool) -> None:
        """Define o estado de HubScreen ativo (visível).

        Args:
            active: True se Hub está ativo
        """
        self._state.is_active = active

    def set_last_dashboard_refresh_time(self, timestamp: float) -> None:
        """Define o timestamp do último refresh de dashboard.

        Args:
            timestamp: Unix timestamp
        """
        self._state.last_dashboard_refresh_time = timestamp

    def set_last_notes_refresh_time(self, timestamp: float) -> None:
        """Define o timestamp do último refresh de notas.

        Args:
            timestamp: Unix timestamp
        """
        self._state.last_notes_refresh_time = timestamp

    def set_last_author_cache_refresh(self, timestamp: float) -> None:
        """Define o timestamp do último refresh de cache de autores.

        Args:
            timestamp: Unix timestamp
        """
        self._state.last_author_cache_refresh = timestamp

    def set_last_org_for_names(self, org_id: Optional[str]) -> None:
        """Define a última org_id usada para carregar cache de nomes.

        Args:
            org_id: ID da organização
        """
        self._state.last_org_for_names = org_id

    # ═══════════════════════════════════════════════════════════════════════
    # Legacy State (compatibilidade com código antigo)
    # ═══════════════════════════════════════════════════════════════════════

    def set_author_tags(self, tags: Dict[str, str]) -> None:
        """Define o mapa de tags de autores (legado).

        Args:
            tags: Mapa de email -> tag de cor
        """
        self._state.author_tags = tags

    def set_poll_job(self, job_id: Optional[str]) -> None:
        """Define o ID do job de polling agendado (legado).

        Args:
            job_id: ID retornado por after()
        """
        self._state.poll_job = job_id

    def set_refreshing(self, refreshing: bool) -> None:
        """Define o estado de refresh em andamento (legado).

        Args:
            refreshing: True se refresh está em andamento
        """
        self._state.is_refreshing = refreshing

    def set_last_refresh_ts(self, timestamp: Optional[float]) -> None:
        """Define o timestamp do último refresh completo (legado).

        Args:
            timestamp: Unix timestamp
        """
        self._state.last_refresh_ts = timestamp

    # ═══════════════════════════════════════════════════════════════════════
    # Bulk Updates (para operações complexas)
    # ═══════════════════════════════════════════════════════════════════════

    def bulk_update(self, **kwargs: Any) -> None:
        """Atualiza múltiplos campos de estado de uma vez.

        Use com cautela - prefira métodos específicos quando possível.
        Útil para operações complexas que modificam múltiplos campos relacionados.

        Args:
            **kwargs: Pares campo=valor a serem atualizados
        """
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
            else:
                logger.warning(f"HubStateManager.bulk_update: campo desconhecido '{key}' ignorado")

    def __repr__(self) -> str:
        """Representação do manager para debug."""
        return f"<HubStateManager state={self._state}>"
