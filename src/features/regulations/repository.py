# -*- coding: utf-8 -*-
"""Repository for reg_obligations table.

Provides data access functions for regulatory obligations (SNGPC, Farmácia Popular, etc.).
Follows the same patterns as cashflow/repository.py.
"""

from __future__ import annotations

import logging
from datetime import date as date_cls
from typing import Any

from src.data.domain_types import RegObligationRow
from src.data.supabase_repo import (
    PostgrestAPIError,
    format_api_error,
    get_supabase_client,
    to_iso_date,
)

logger = logging.getLogger(__name__)

TABLE = "reg_obligations"


# ---------------------------------------------------------------------------
# Repositório de Obrigações Regulatórias
# ---------------------------------------------------------------------------
def list_obligations_for_org(
    org_id: str,
    *,
    start_date: date_cls | None = None,
    end_date: date_cls | None = None,
    status: str | None = None,
    kind: str | None = None,
    limit: int | None = None,
) -> list[RegObligationRow]:
    """Lista obrigações regulatórias de uma organização, com filtros opcionais.

    Args:
        org_id: UUID da organização (obrigatório).
        start_date: Filtra por due_date >= start_date.
        end_date: Filtra por due_date <= end_date.
        status: Filtra por status ('pending', 'done', 'overdue', 'canceled').
        kind: Filtra por tipo ('SNGPC', 'FARMACIA_POPULAR', 'SIFAP', etc.).
        limit: Limita o número de resultados retornados.

    Returns:
        Lista de obrigações no formato RegObligationRow.

    Raises:
        RuntimeError: Se houver erro na API do Supabase.
    """
    client = get_supabase_client()
    query = client.table(TABLE).select("*").eq("org_id", org_id)

    if start_date is not None:
        query = query.gte("due_date", to_iso_date(start_date))

    if end_date is not None:
        query = query.lte("due_date", to_iso_date(end_date))

    if status is not None:
        query = query.eq("status", status)

    if kind is not None:
        query = query.eq("kind", kind)

    # Ordenar por data de vencimento
    query = query.order("due_date", desc=False)

    if limit is not None:
        query = query.limit(limit)

    try:
        res = query.execute()
        data: list[RegObligationRow] = getattr(res, "data", None) or []
        return list(data)
    except PostgrestAPIError as e:
        raise format_api_error(e, "SELECT")


def count_pending_obligations(org_id: str) -> int:
    """Conta obrigações pendentes ou atrasadas de uma organização.

    Considera status 'pending' e 'overdue' como pendentes de resolução.

    Args:
        org_id: UUID da organização (obrigatório).

    Returns:
        Quantidade de obrigações com status 'pending' ou 'overdue'.

    Raises:
        RuntimeError: Se houver erro na API do Supabase.
    """
    client = get_supabase_client()
    query = client.table(TABLE).select("id", count="exact").eq("org_id", org_id).in_("status", ["pending", "overdue"])

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
