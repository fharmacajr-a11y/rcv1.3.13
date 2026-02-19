# -*- coding: utf-8 -*-
"""Módulo de auditoria de ações de clientes.

Este módulo registra ações importantes realizadas sobre clientes no sistema.
Não cria diretórios ou arquivos no import - apenas configura logging.
"""

from __future__ import annotations

from typing import Any, Iterable

from .logger import get_logger

# Logger para auditoria (sem side effects no import)
_audit_logger = get_logger("rcgestor.audit")

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
    action: str,
    **kwargs: Any,
) -> None:
    """Registra ação de cliente para auditoria.

    Args:
        user: Usuário que realizou a ação.
        client_id: ID do cliente afetado.
        action: Tipo de ação ("criacao", "edicao", "exclusao", etc.).
        **kwargs: Dados adicionais para contexto.

    Example:
        >>> log_client_action("admin", 123, "edicao", field="email")
    """
    _audit_logger.info(
        "Cliente %d - %s por %s",
        client_id,
        action,
        user,
        extra={"client_id": client_id, "user": user, "action": action, **kwargs},
    )


def last_action_of_user(user_id: int) -> str | None:
    """Retorna a ultima acao conhecida de um usuario. Placeholder retorna None."""
    return None


def last_client_activity_many(client_ids: Iterable[int]) -> dict[int, tuple[str, str]]:
    """Retorna mapeamento client_id -> (acao, timestamp). Placeholder retorna dicionario vazio."""
    return {}
