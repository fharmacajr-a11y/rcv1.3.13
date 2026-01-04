# -*- coding: utf-8 -*-
"""Repository for cashflow_entries table.

Provides data access functions for cashflow entries (income/expense tracking).
Uses centralized helpers from data.supabase_repo for client access and error handling.
"""

from __future__ import annotations

import logging
from datetime import date as date_cls
from typing import Any

from src.db.supabase_repo import (
    PostgrestAPIError,
    format_api_error,
    get_supabase_client,
    to_iso_date,
)

logger = logging.getLogger(__name__)

TABLE = "cashflow_entries"


# ---------------------------------------------------------------------------
# Utilitários Locais
# ---------------------------------------------------------------------------
def _apply_text_filter(query: Any, text: str | None) -> Any:
    """Aplica filtro de texto na descrição do lançamento."""
    if not text:
        return query
    try:
        return query.ilike("description", f"%{text}%")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Filtro ilike indisponivel (cashflow): %s", exc)
        return query


def _build_list_query(
    client: Any,
    dfrom: date_cls | str | None,
    dto: date_cls | str | None,
    type_filter: str | None,
    text: str | None,
    org_id: str | None,
) -> Any:
    """Constrói query de listagem com filtros."""
    q = client.table(TABLE).select("*").order("date", desc=False)

    if org_id:
        q = q.eq("org_id", org_id)

    if dfrom:
        q = q.gte("date", to_iso_date(dfrom))
    if dto:
        q = q.lte("date", to_iso_date(dto))

    if type_filter and type_filter in ("IN", "OUT"):
        q = q.eq("type", type_filter)

    return _apply_text_filter(q, text)


def _execute_list_query(query: Any) -> list[dict[str, Any]]:
    """Executa query e retorna dados, tratando erros."""
    try:
        res = query.execute()
        data: list[dict[str, Any]] = getattr(res, "data", None) or []
        return list(data)
    except PostgrestAPIError as e:
        raise format_api_error(e, "SELECT")


def _accumulate_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Calcula totais de entradas/saídas/saldo."""
    t_in: float = 0.0
    t_out: float = 0.0
    for r in rows:
        amt: float = float(r.get("amount", 0) or 0)
        if (r.get("type") or "").upper() == "IN":
            t_in += amt
        else:
            t_out += amt
    return {"in": t_in, "out": t_out, "balance": t_in - t_out}


# ---------------------------------------------------------------------------
# Repositório do Fluxo de Caixa
# ---------------------------------------------------------------------------
def list_entries(
    dfrom: date_cls | str | None,
    dto: date_cls | str | None,
    type_filter: str | None = None,
    text: str | None = None,
    *,
    org_id: str | None = None,
) -> list[dict[str, Any]]:
    """Lista lançamentos por período, com filtros opcionais."""
    c = get_supabase_client()
    q = _build_list_query(c, dfrom, dto, type_filter, text, org_id)
    return _execute_list_query(q)


def totals(
    dfrom: date_cls | str | None,
    dto: date_cls | str | None,
    *,
    org_id: str | None = None,
) -> dict[str, float]:
    """Totaliza entradas/saídas/saldo no período."""
    rows: list[dict[str, Any]] = list_entries(dfrom, dto, org_id=org_id)
    return _accumulate_totals(rows)


def create_entry(data: dict[str, Any], org_id: str | None = None) -> dict[str, Any]:
    """Cria um lançamento e retorna o registro inserido."""
    c = get_supabase_client()
    payload: dict[str, Any] = dict(data)
    if org_id and not payload.get("org_id"):
        payload["org_id"] = org_id
    try:
        res = c.table(TABLE).insert(payload).execute()
        rows: list[dict[str, Any]] = getattr(res, "data", None) or []
        return rows[0] if rows else payload
    except PostgrestAPIError as e:
        raise format_api_error(e, "INSERT")


def update_entry(entry_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Atualiza um lançamento pelo id e retorna o registro atualizado."""
    c = get_supabase_client()
    try:
        res = c.table(TABLE).update(data).eq("id", entry_id).execute()
        rows: list[dict[str, Any]] = getattr(res, "data", None) or []
        return rows[0] if rows else {"id": entry_id, **data}
    except PostgrestAPIError as e:
        raise format_api_error(e, "UPDATE")


def delete_entry(entry_id: str) -> None:
    """Exclui um lançamento pelo id."""
    c = get_supabase_client()
    try:
        c.table(TABLE).delete().eq("id", entry_id).execute()
    except PostgrestAPIError as e:
        raise format_api_error(e, "DELETE")
