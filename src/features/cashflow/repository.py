# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from datetime import date as date_cls
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# postgrest APIError (mantém assinatura usada no projeto)
# ---------------------------------------------------------------------------
try:
    from postgrest import APIError as PostgrestAPIError  # type: ignore
except Exception:  # fallback se lib mudar

    class PostgrestAPIError(Exception):  # type: ignore
        pass


# ---------------------------------------------------------------------------
# Cliente Supabase do projeto — compatível com vários layouts
# Tenta nesta ordem:
# 1) relativo (projetos com pacote "src"): ...infra.supabase.db_client.get_client
# 2) relativo fallback: ...infra.supabase_client.get_supabase
# 3) absoluto novo (sem 'src.'): infra.supabase.db_client.get_client
# 4) absoluto novo (sem 'src.'): infra.supabase_client.get_supabase
# 5) absoluto antigo (com 'src.'): src.infra.supabase.db_client.get_client
# 6) absoluto antigo (com 'src.'): src.infra.supabase_client.get_supabase
# Em todos os casos, normalizamos para uma função _GET() que retorna o client.
# ---------------------------------------------------------------------------
def _UNAVAILABLE() -> Any:
    raise RuntimeError("Cliente Supabase não disponível (infra/src.infra). Verifique paths de import.")


def _build_get() -> callable:  # pyright: ignore[reportGeneralTypeIssues]
    # 1) relativo db_client
    try:
        from ...infra.supabase.db_client import get_client as _gc  # type: ignore

        return _gc
    except Exception as exc:  # noqa: BLE001
        logger.debug("Supabase get_client relativo indisponivel: %s", exc)
    # 2) relativo supabase_client
    try:
        from ...infra.supabase_client import get_supabase as _gs  # type: ignore

        return _gs
    except Exception as exc:  # noqa: BLE001
        logger.debug("Supabase get_supabase relativo indisponivel: %s", exc)
    # 3) absoluto sem 'src.' db_client
    try:
        from infra.supabase.db_client import get_client as _gc  # type: ignore

        return _gc
    except Exception as exc:  # noqa: BLE001
        logger.debug("Supabase get_client absoluto indisponivel: %s", exc)
    # 4) absoluto sem 'src.' supabase_client
    try:
        from infra.supabase_client import get_supabase as _gs  # type: ignore

        return _gs
    except Exception as exc:  # noqa: BLE001
        logger.debug("Supabase get_supabase absoluto indisponivel: %s", exc)
    # 5) absoluto com 'src.' db_client
    try:
        from src.infra.supabase.db_client import get_client as _gc  # type: ignore

        return _gc
    except Exception as exc:  # noqa: BLE001
        logger.debug("Supabase get_client src.* indisponivel: %s", exc)
    # 6) absoluto com 'src.' supabase_client
    try:
        from src.infra.supabase_client import get_supabase as _gs  # type: ignore

        return _gs
    except Exception as exc:  # noqa: BLE001
        logger.debug("Supabase get_supabase src.* indisponivel: %s", exc)
    return _UNAVAILABLE


_GET = _build_get()

TABLE = "cashflow_entries"


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def _get_client():
    c = _GET()
    if c is None:
        # compat: se algum wrapper retornar None
        raise RuntimeError("Cliente Supabase não disponível (infra/src.infra). Verifique paths de import.")
    return c


def _fmt_api_error(e: PostgrestAPIError, op: str) -> RuntimeError:
    """Constrói mensagem amigável mantendo o código/status quando disponíveis."""
    code: str | None = getattr(e, "code", None)
    details: str = getattr(e, "details", None) or getattr(e, "message", None) or str(e)
    hint: str | None = getattr(e, "hint", None)
    msg: str = f"[{op}] Erro na API: {details}"
    if code:
        msg = f"[{op}] ({code}) {details}"
    if hint:
        msg += f" | hint: {hint}"
    return RuntimeError(msg)


def _iso(d: date_cls | str) -> str:
    return d if isinstance(d, str) else d.isoformat()


def _apply_text_filter(query: Any, text: str | None) -> Any:
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
    q = client.table(TABLE).select("*").order("date", desc=False)

    if org_id:
        q = q.eq("org_id", org_id)

    if dfrom:
        q = q.gte("date", _iso(dfrom))
    if dto:
        q = q.lte("date", _iso(dto))

    if type_filter and type_filter in ("IN", "OUT"):
        q = q.eq("type", type_filter)

    return _apply_text_filter(q, text)


def _execute_list_query(query: Any) -> list[dict[str, Any]]:
    try:
        res = query.execute()
        data: list[dict[str, Any]] = getattr(res, "data", None) or []
        return list(data)
    except PostgrestAPIError as e:
        raise _fmt_api_error(e, "SELECT")


def _accumulate_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
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
    """Lista lan??amentos por per??odo, com filtros opcionais."""
    c = _get_client()
    q = _build_list_query(c, dfrom, dto, type_filter, text, org_id)
    return _execute_list_query(q)


def totals(
    dfrom: date_cls | str | None,
    dto: date_cls | str | None,
    *,
    org_id: str | None = None,
) -> dict[str, float]:
    """Totaliza entradas/sa??das/saldo no per??odo."""
    rows: list[dict[str, Any]] = list_entries(dfrom, dto, org_id=org_id)
    return _accumulate_totals(rows)


def create_entry(data: dict[str, Any], org_id: str | None = None) -> dict[str, Any]:
    """Cria um lançamento e retorna o registro inserido."""
    c = _get_client()
    payload: dict[str, Any] = dict(data)
    if org_id and not payload.get("org_id"):
        payload["org_id"] = org_id
    try:
        res = c.table(TABLE).insert(payload).execute()
        rows: list[dict[str, Any]] = getattr(res, "data", None) or []
        return rows[0] if rows else payload
    except PostgrestAPIError as e:
        raise _fmt_api_error(e, "INSERT")


def update_entry(entry_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Atualiza um lançamento pelo id e retorna o registro atualizado."""
    c = _get_client()
    try:
        res = c.table(TABLE).update(data).eq("id", entry_id).execute()
        rows: list[dict[str, Any]] = getattr(res, "data", None) or []
        return rows[0] if rows else {"id": entry_id, **data}
    except PostgrestAPIError as e:
        raise _fmt_api_error(e, "UPDATE")


def delete_entry(entry_id: str) -> None:
    """Exclui um lançamento pelo id."""
    c = _get_client()
    try:
        c.table(TABLE).delete().eq("id", entry_id).execute()
    except PostgrestAPIError as e:
        raise _fmt_api_error(e, "DELETE")
