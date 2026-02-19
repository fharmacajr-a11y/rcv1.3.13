# -*- coding: utf-8 -*-
"""Shared state container for Hub screen.

Este módulo define o HubState, container de estado interno do HubScreen.
Expandido na MF-15 para suportar separação View/Controller.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Type alias para cache de autores (compatível com hub_notes_helpers)
AuthorCache = Dict[str, Tuple[str, float]]  # email -> (display_name, timestamp)

DEFAULT_AUTH_RETRY_MS = 2000
DEFAULT_NAMES_REFRESH_COOLDOWN_S = 30

__all__ = [
    "HubState",
    "HubScreenConfig",
    "ensure_hub_state",
    "ensure_state",
]


@dataclass
class HubScreenConfig:
    """Configuração do HubScreen (timings, cooldowns, constantes)."""

    # Retry de autenticação
    AUTH_RETRY_MS: int = DEFAULT_AUTH_RETRY_MS

    # Cooldown para refresh de cache de nomes de autores
    NAMES_REFRESH_COOLDOWN_S: int = DEFAULT_NAMES_REFRESH_COOLDOWN_S

    # Intervalos de polling
    NOTES_POLL_INTERVAL_MS: int = 10000  # 10 segundos
    DASHBOARD_POLL_INTERVAL_MS: int = 60000  # 60 segundos


@dataclass
class HubState:
    """Estado completo do HubScreen.

    Attributes:
        # --- Estado de Tags (legado) ---
        author_tags: Mapa de email → tag de cor para renderização de notas
        poll_job: ID do job de polling agendado (after_id)
        is_refreshing: Flag de refresh em andamento
        last_refresh_ts: Timestamp do último refresh completo
        pending_notes: Notas pendentes de processamento
        auth_retry_ms: Intervalo de retry para autenticação

        # --- Identidade e Organização (MF-15) ---
        org_id: ID da organização atual
        user_id: ID do usuário logado
        user_email: Email do usuário logado
        user_role: Role do usuário (admin, user, etc.)

        # --- Estado de UI (MF-15) ---
        is_loading: Flag de loading geral
        is_dashboard_loaded: Flag de dashboard carregado
        is_notes_loaded: Flag de notas carregadas

        # --- Cache de Dados (MF-15 + MF-37) ---
        cached_notes: Lista de notas carregadas
        cached_authors: Mapa de email → display_name (legado)
        email_prefix_map: Mapa de prefixo → email completo (notas legadas)
        notes_content_hash: Hash MD5 do conteúdo das notas (evitar re-render)
        last_names_cache_hash: Hash MD5 do cache de nomes (evitar re-render)
        author_cache: Cache de autores com timestamp (email → (display_name, ts)) - MF-37

        # --- Flags de Lifecycle (MF-15) ---
        is_active: Flag de HubScreen ativo (visível)
        last_dashboard_refresh_time: Timestamp do último refresh de dashboard
        last_notes_refresh_time: Timestamp do último refresh de notas
        last_author_cache_refresh: Timestamp do último refresh de cache de autores
        last_org_for_names: Última org_id usada para carregar cache de nomes

        # --- Configuração de Features (MF-15) ---
        enable_live_sync: Flag de live sync habilitado
        enable_dashboard_refresh: Flag de refresh automático de dashboard

        # --- Estado de Live Sync ---
        live_sync_on: Flag de live sync ativo
        live_org_id: org_id do live sync
        live_channel: Canal de realtime
        live_last_ts: ISO timestamp da última nota conhecida

        # --- Estado de Erro (MF-37) ---
        notes_table_missing: Flag de tabela rc_notes ausente
        notes_table_missing_notified: Flag de notificação de erro já exibida
        notes_retry_ms: Intervalo de retry após erro de tabela

        # --- Cache de Nomes (MF-37) ---
        names_cache_loaded: Flag de cache de nomes carregado
        names_refreshing: Flag de refresh de nomes em andamento
        pending_name_fetch: Set de emails pendentes de fetch

        # --- Snapshots de Polling (MF-37) ---
        notes_last_snapshot: Snapshot (id, ts) para detectar mudanças
        notes_last_data: Dados completos normalizados das notas
        notes_poll_ms: Intervalo de polling de notas (ms)
        polling_active: Flag de polling ativo
    """

    # ═══════════════════════════════════════════════════════════════════════
    # Estado Legado (mantido para compatibilidade)
    # ═══════════════════════════════════════════════════════════════════════
    author_tags: Dict[str, str] = field(default_factory=dict)
    poll_job: Optional[str] = None
    is_refreshing: bool = False
    last_refresh_ts: Optional[float] = None
    pending_notes: List[Any] = field(default_factory=list)
    auth_retry_ms: int = DEFAULT_AUTH_RETRY_MS

    # ═══════════════════════════════════════════════════════════════════════
    # Identidade e Organização (MF-15)
    # ═══════════════════════════════════════════════════════════════════════
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # Estado de UI (MF-15)
    # ═══════════════════════════════════════════════════════════════════════
    is_loading: bool = False
    is_dashboard_loaded: bool = False
    is_notes_loaded: bool = False

    # ═══════════════════════════════════════════════════════════════════════
    # Cache de Dados (MF-15 + MF-37)
    # ═══════════════════════════════════════════════════════════════════════
    cached_notes: List[Dict[str, Any]] = field(default_factory=list)
    cached_authors: Dict[str, str] = field(default_factory=dict)
    email_prefix_map: Dict[str, str] = field(default_factory=dict)
    notes_content_hash: Optional[str] = None
    last_names_cache_hash: Optional[str] = None
    last_render_hash: Optional[str] = None

    # MF-37: Cache de autores com timestamp (email -> (display_name, timestamp))
    author_cache: AuthorCache = field(default_factory=dict)

    # ═══════════════════════════════════════════════════════════════════════
    # Flags de Lifecycle (MF-15)
    # ═══════════════════════════════════════════════════════════════════════
    is_active: bool = False
    last_dashboard_refresh_time: float = 0.0
    last_notes_refresh_time: float = 0.0
    last_author_cache_refresh: float = 0.0
    last_org_for_names: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # Configuração de Features (MF-15)
    # ═══════════════════════════════════════════════════════════════════════
    enable_live_sync: bool = True
    enable_dashboard_refresh: bool = True

    # ═══════════════════════════════════════════════════════════════════════
    # Estado de Live Sync
    # ═══════════════════════════════════════════════════════════════════════
    live_sync_on: bool = False
    live_org_id: Optional[str] = None
    live_channel: Optional[Any] = None
    live_last_ts: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # Estado de Erro
    # ═══════════════════════════════════════════════════════════════════════
    notes_table_missing: bool = False
    notes_table_missing_notified: bool = False
    notes_retry_ms: int = 60000  # 60 segundos

    # ═══════════════════════════════════════════════════════════════════════
    # Cache de Nomes
    # ═══════════════════════════════════════════════════════════════════════
    names_cache_loaded: bool = False
    names_refreshing: bool = False
    names_cache_loading: bool = False
    pending_name_fetch: set = field(default_factory=set)

    # ═══════════════════════════════════════════════════════════════════════
    # Snapshots de Polling
    # ═══════════════════════════════════════════════════════════════════════
    notes_last_snapshot: Optional[List[tuple]] = None
    notes_last_data: Optional[List[Dict[str, Any]]] = None
    notes_poll_ms: int = 10000  # 10 segundos
    polling_active: bool = False

    # ═══════════════════════════════════════════════════════════════════════
    # Métodos Auxiliares
    # ═══════════════════════════════════════════════════════════════════════

    def should_refresh_authors_cache(self, cooldown_s: int = DEFAULT_NAMES_REFRESH_COOLDOWN_S) -> bool:
        """Verifica se deve atualizar cache de autores (respeita cooldown).

        Args:
            cooldown_s: Cooldown em segundos (padrão: 30s)

        Returns:
            True se deve refresh, False se ainda em cooldown
        """
        if self.names_refreshing:
            return False

        now = time.time()
        elapsed = now - self.last_author_cache_refresh

        return elapsed >= cooldown_s

    def update_notes_hash(self, notes: Optional[Iterable[Any]]) -> bool:
        """Atualiza hash de notas. Retorna True se mudou.

        Suporta tanto lista de dicts quanto lista de objetos (NoteItemView).

        Args:
            notes: Lista de notas para calcular hash (dicts, objetos ou None)

        Returns:
            True se hash mudou, False se igual
        """
        import hashlib
        import json

        def _extract_tuple(note: Any) -> tuple[Any, Any, Any]:
            """Extrai tupla (id, created_at, body) de dict ou objeto."""
            if isinstance(note, dict):
                return note.get("id"), note.get("created_at"), note.get("body")
            # Objeto com atributos (NoteItemView, etc.)
            return (
                getattr(note, "id", None),
                getattr(note, "created_at", None),
                getattr(note, "body", None),
            )

        notes_list = list(notes or [])

        # Calcular hash do conteúdo
        content = json.dumps(
            [_extract_tuple(n) for n in notes_list],
            sort_keys=True,
            default=str,
        )
        new_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()  # nosec B324

        # Verificar se mudou
        if new_hash != self.notes_content_hash:
            self.notes_content_hash = new_hash
            return True

        return False

    def mark_dashboard_refresh(self) -> None:
        """Marca timestamp de refresh de dashboard."""
        self.last_dashboard_refresh_time = time.time()

    def mark_notes_refresh(self) -> None:
        """Marca timestamp de refresh de notas."""
        self.last_notes_refresh_time = time.time()

    def mark_authors_refresh(self) -> None:
        """Marca timestamp de refresh de cache de autores."""
        self.last_author_cache_refresh = time.time()


def ensure_hub_state(obj) -> HubState:
    """Attach a HubState instance using the _hub_state attribute."""
    state = getattr(obj, "_hub_state", None)
    if not isinstance(state, HubState):
        state = HubState()
        setattr(obj, "_hub_state", state)
    return state


def ensure_state(obj) -> HubState:
    """Backward-compatible alias that delegates to ensure_hub_state."""
    return ensure_hub_state(obj)
