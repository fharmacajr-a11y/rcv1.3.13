# -*- coding: utf-8 -*-
"""Shared state container for Hub screen."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


DEFAULT_AUTH_RETRY_MS = 2000

__all__ = ["HubState", "ensure_hub_state", "ensure_state"]


@dataclass
class HubState:
    author_tags: Dict[str, str] = field(default_factory=dict)
    poll_job: Optional[str] = None
    is_refreshing: bool = False
    last_refresh_ts: Optional[float] = None
    pending_notes: List[Any] = field(default_factory=list)
    auth_retry_ms: int = DEFAULT_AUTH_RETRY_MS


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
