# -*- coding: utf-8 -*-
"""Audit logging helpers shared across the application."""

from __future__ import annotations

from typing import Iterable, Dict, Tuple, Optional

__all__ = [
    "ensure_schema",
    "log_client_action",
    "last_action_of_user",
    "last_client_activity_many",
]


def ensure_schema() -> None:
    """Placeholder to keep compatibility; an actual schema can be created later."""
    return None


def log_client_action(
    user: str,
    client_id: int,
    action: str,
    details: Optional[str] = None,
) -> None:
    """Records a client action. Currently a no-op kept for future expansion."""
    return None


def last_action_of_user(user_id: int) -> Optional[str]:
    """Returns the last action for a user; placeholder returning None."""
    return None


def last_client_activity_many(client_ids: Iterable[int]) -> Dict[int, Tuple[str, str]]:
    """Returns mapping client_id -> (action, timestamp). Placeholder returning empty mapping."""
    return {}
