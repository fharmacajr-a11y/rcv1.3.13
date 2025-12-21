"""Utilitários de logging para o módulo ANVISA.

Fornece helpers para logging estruturado com contexto (org_id, client_id, request_id, action).
"""

import logging
from typing import Any


def get_anvisa_logger(name: str = __name__) -> logging.Logger:
    """Retorna um logger para o módulo ANVISA.

    Args:
        name: Nome do logger (geralmente __name__ do módulo).

    Returns:
        Logger configurado.
    """
    return logging.getLogger(name)


class AnvisaContextFilter(logging.Filter):
    """Filter que garante atributos de contexto ANVISA em todos os records.

    Adiciona os seguintes atributos aos LogRecord se não existirem:
    - org_id: ID da organização
    - client_id: ID do cliente
    - request_id: ID da requisição ANVISA
    - action: Ação sendo executada

    Valores ausentes são preenchidos com "-".
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Adiciona atributos de contexto ao record."""
        if not hasattr(record, "org_id"):
            record.org_id = "-"
        if not hasattr(record, "client_id"):
            record.client_id = "-"
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        if not hasattr(record, "action"):
            record.action = "-"
        return True


def add_anvisa_filter(logger: logging.Logger) -> None:
    """Adiciona o AnvisaContextFilter ao logger (idempotente).

    Args:
        logger: Logger ao qual adicionar o filter.
    """
    # Verifica se o filter já existe
    for filt in logger.filters:
        if isinstance(filt, AnvisaContextFilter):
            return

    logger.addFilter(AnvisaContextFilter())


def fmt_ctx(**ctx: Any) -> str:
    """Formata contexto para incluir em mensagens de log.

    Args:
        **ctx: Contexto a formatar (org_id, client_id, request_id, action, etc).

    Returns:
        String formatada com o contexto (ex: "org=123 client=456 req=789 action=create").

    Examples:
        >>> fmt_ctx(org_id="org-123", client_id=456, action="create")
        'org=org-123 client=456 action=create'

        >>> fmt_ctx(request_id="req-789")
        'req=req-789'
    """
    parts = []

    # Ordem consistente de campos
    field_order = ["org_id", "client_id", "request_id", "action"]

    for field in field_order:
        if field in ctx and ctx[field] not in (None, "", "-"):
            # Remove sufixo "_id" para abreviar
            key = field.replace("_id", "")
            parts.append(f"{key}={ctx[field]}")

    # Adiciona campos extras (não na ordem padrão)
    for key, value in ctx.items():
        if key not in field_order and value not in (None, "", "-"):
            parts.append(f"{key}={value}")

    return " ".join(parts)
