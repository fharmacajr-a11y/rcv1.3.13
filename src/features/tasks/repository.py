# -*- coding: utf-8 -*-
"""Repository for rc_tasks table.

Provides data access functions for RC tasks (Regularize Consultoria).
Follows the same patterns as cashflow/repository.py.
"""

from __future__ import annotations

import logging
from datetime import date as date_cls
from typing import Any

from src.data.domain_types import RCTaskRow
from src.data.supabase_repo import (
    PostgrestAPIError,
    format_api_error,
    get_supabase_client,
    to_iso_date,
)

logger = logging.getLogger(__name__)

TABLE = "rc_tasks"


# ---------------------------------------------------------------------------
# Repositório de Tasks
# ---------------------------------------------------------------------------
def list_tasks_for_org(
    org_id: str,
    *,
    due_date: date_cls | None = None,
    status: str | None = None,
    assigned_to: str | None = None,
) -> list[RCTaskRow]:
    """Lista tarefas de uma organização, com filtros opcionais.

    Args:
        org_id: UUID da organização (obrigatório).
        due_date: Filtra por data de vencimento específica.
        status: Filtra por status ('pending', 'done', 'canceled').
        assigned_to: Filtra por UUID do usuário responsável.

    Returns:
        Lista de tarefas no formato RCTaskRow.

    Raises:
        RuntimeError: Se houver erro na API do Supabase.
    """
    client = get_supabase_client()
    query = client.table(TABLE).select("*").eq("org_id", org_id)

    if due_date is not None:
        query = query.eq("due_date", to_iso_date(due_date))

    if status is not None:
        query = query.eq("status", status)

    if assigned_to is not None:
        query = query.eq("assigned_to", assigned_to)

    # Ordenar por data de vencimento e prioridade
    query = query.order("due_date", desc=False).order("priority", desc=True)

    try:
        res = query.execute()
        data: list[RCTaskRow] = getattr(res, "data", None) or []
        return list(data)
    except PostgrestAPIError as e:
        raise format_api_error(e, "SELECT")


def count_tasks_for_org(
    org_id: str,
    *,
    due_date: date_cls | None = None,
    status: str | None = None,
) -> int:
    """Conta tarefas de uma organização, com filtros opcionais.

    Args:
        org_id: UUID da organização (obrigatório).
        due_date: Filtra por data de vencimento específica.
        status: Filtra por status ('pending', 'done', 'canceled').

    Returns:
        Quantidade de tarefas que atendem aos critérios.

    Raises:
        RuntimeError: Se houver erro na API do Supabase.
    """
    client = get_supabase_client()
    query = client.table(TABLE).select("id", count="exact").eq("org_id", org_id)

    if due_date is not None:
        query = query.eq("due_date", to_iso_date(due_date))

    if status is not None:
        query = query.eq("status", status)

    try:
        res = query.execute()
        # O count vem no atributo count do response
        count_val = getattr(res, "count", None)
        if count_val is not None:
            return int(count_val)
        # Fallback: contar registros retornados
        data: list[dict[str, Any]] = getattr(res, "data", None) or []
        return len(data)
    except PostgrestAPIError as e:
        raise format_api_error(e, "COUNT")
