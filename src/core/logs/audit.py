# -*- coding: utf-8 -*-
"""Audit logging helpers shared across the application."""

from __future__ import annotations

from typing import Iterable

__all__ = [
    "ensure_schema",
    "log_client_action",
    "last_action_of_user",
    "last_client_activity_many",
]


def ensure_schema() -> None:
    """Placeholder para manter compatibilidade; schema de auditoria pode ser criado depois."""
    return None


def log_client_action(
    user: str,
    client_id: int,
    _action: str,  # Prefixo _ indica parametro nao usado (placeholder futuro)
    _details: str | None = None,  # Prefixo _ indica parametro nao usado
) -> None:
    """Registra uma acao de cliente. No momento, funcao no-op mantida para expansao futura."""
    return None


def last_action_of_user(user_id: int) -> str | None:
    """Retorna a ultima acao conhecida de um usuario. Placeholder retorna None."""
    return None


def last_client_activity_many(client_ids: Iterable[int]) -> dict[int, tuple[str, str]]:
    """Retorna mapeamento client_id -> (acao, timestamp). Placeholder retorna dicionario vazio."""
    return {}
