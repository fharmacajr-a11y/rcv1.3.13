# -*- coding: utf-8 -*-
"""DEPRECATED: Use src.modules.hub.helpers.debug (mantido para compatibilidade).

ORG-003: Helpers de debug foram consolidados em hub/helpers/debug.py.
Este arquivo permanece como shim de compatibilidade para não quebrar imports externos.

Para novos códigos, importe diretamente de:
    from src.modules.hub.helpers.debug import ...
"""

from __future__ import annotations

import logging
import os  # noqa: F401  # Necessário para testes que patcheiam os.path
from tkinter import messagebox  # noqa: F401  # Necessário para testes que patcheiam messagebox
from typing import Any, Callable, Dict, Iterable, Optional

# Re-exports do novo local (ORG-003)
from ..helpers import debug as _impl

# ORG-008-FIX: Expor logger para compatibilidade com patches de testes
logger = logging.getLogger(__name__)

# ORG-008-FIX: Wrappers que propagam o logger patchado para o módulo real
# Necessário porque testes patcham hub_debug_helpers.logger, mas a lógica
# está em ..helpers.debug. Os wrappers garantem que o logger patchado seja
# usado pela implementação real.


def hub_dlog(
    tag: str,
    *,
    enabled: bool,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Wrapper que propaga logger patchado para _impl.hub_dlog."""
    _impl.logger = logger
    return _impl.hub_dlog(tag, enabled=enabled, extra=extra)


def collect_notes_debug_data(
    get_org_id: Callable[[], Optional[str]],
    notes_last_data: Any,
    notes_last_snapshot: Any,
    author_names_cache: dict[str, str],
    email_prefix_map: dict[str, str],
    notes_cache_loaded: bool,
    notes_last_refresh: Optional[float],
    polling_active: bool,
    live_sync_on: bool,
) -> dict[str, Any]:
    """Wrapper que propaga logger patchado para _impl.collect_notes_debug_data."""
    _impl.logger = logger
    return _impl.collect_notes_debug_data(
        get_org_id=get_org_id,
        notes_last_data=notes_last_data,
        notes_last_snapshot=notes_last_snapshot,
        author_names_cache=author_names_cache,
        email_prefix_map=email_prefix_map,
        notes_cache_loaded=notes_cache_loaded,
        notes_last_refresh=notes_last_refresh,
        polling_active=polling_active,
        live_sync_on=live_sync_on,
    )


def show_debug_info(
    parent: Any,
    collect_debug_data: Callable[[], dict[str, Any]],
) -> None:
    """Wrapper que propaga logger patchado para _impl.show_debug_info."""
    _impl.logger = logger
    return _impl.show_debug_info(parent=parent, collect_debug_data=collect_debug_data)


def collect_full_notes_debug(
    *,
    get_org_id: Callable[[], Optional[str]],
    notes_last_data: Optional[Iterable[Any]],
    notes_last_snapshot: Optional[Iterable[Any]],
    author_names_cache: Dict[str, Any],
    email_prefix_map: Dict[str, str],
    notes_cache_loaded: bool,
    notes_last_refresh: Optional[float],
    polling_active: bool,
    live_sync_on: bool,
    current_user_email: Optional[str],
    debug_resolve_author_fn: Callable[[Any, str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Wrapper que propaga logger patchado para _impl.collect_full_notes_debug."""
    _impl.logger = logger
    return _impl.collect_full_notes_debug(
        get_org_id=get_org_id,
        notes_last_data=notes_last_data,
        notes_last_snapshot=notes_last_snapshot,
        author_names_cache=author_names_cache,
        email_prefix_map=email_prefix_map,
        notes_cache_loaded=notes_cache_loaded,
        notes_last_refresh=notes_last_refresh,
        polling_active=polling_active,
        live_sync_on=live_sync_on,
        current_user_email=current_user_email,
        debug_resolve_author_fn=debug_resolve_author_fn,
    )


__all__ = [
    "logger",
    "hub_dlog",
    "collect_notes_debug_data",
    "show_debug_info",
    "collect_full_notes_debug",
]
