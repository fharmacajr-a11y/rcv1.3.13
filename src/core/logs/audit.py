"""Módulo de auditoria de ações de clientes.

Este módulo registra ações importantes realizadas sobre clientes no sistema.
Não cria diretórios ou arquivos no import - apenas configura logging.
"""

from typing import Any

from .logger import get_logger

# Logger para auditoria (sem side effects no import)
_audit_logger = get_logger("rcgestor.audit")


def log_client_action(user: str, client_id: int, action: str, **kwargs: Any) -> None:
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
