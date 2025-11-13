# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date as date_cls

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


def _build_get() -> callable:
    # 1) relativo db_client
    try:
        from ...infra.supabase.db_client import get_client as _gc  # type: ignore

        return _gc
    except Exception:
        pass
    # 2) relativo supabase_client
    try:
        from ...infra.supabase_client import get_supabase as _gs  # type: ignore

        return _gs
    except Exception:
        pass
    # 3) absoluto sem 'src.' db_client
    try:
        from infra.supabase.db_client import get_client as _gc  # type: ignore

        return _gc
    except Exception:
        pass
    # 4) absoluto sem 'src.' supabase_client
    try:
        from infra.supabase_client import get_supabase as _gs  # type: ignore

        return _gs
    except Exception:
        pass
    # 5) absoluto com 'src.' db_client
    try:
        from src.infra.supabase.db_client import get_client as _gc  # type: ignore

        return _gc
    except Exception:
        pass
    # 6) absoluto com 'src.' supabase_client
    try:
        from src.infra.supabase_client import get_supabase as _gs  # type: ignore

        return _gs
    except Exception:
        pass
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
    code = getattr(e, "code", None)
    details = getattr(e, "details", None) or getattr(e, "message", None) or str(e)
    hint = getattr(e, "hint", None)
    msg = f"[{op}] Erro na API: {details}"
    if code:
        msg = f"[{op}] ({code}) {details}"
    if hint:
        msg += f" | hint: {hint}"
    return RuntimeError(msg)


def _iso(d: date_cls | str) -> str:
    return d if isinstance(d, str) else d.isoformat()


# ---------------------------------------------------------------------------
# Repositório do Fluxo de Caixa
# ---------------------------------------------------------------------------
def list_entries(
    dfrom: date_cls | str,
    dto: date_cls | str,
    type_filter: Optional[str] = None,
    text: Optional[str] = None,
    *,
    org_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista lançamentos por período, com filtros opcionais."""
    c = _get_client()
    q = c.table(TABLE).select("*").order("date", desc=False)

    if org_id:
        q = q.eq("org_id", org_id)

    if dfrom:
        q = q.gte("date", _iso(dfrom))
    if dto:
        q = q.lte("date", _iso(dto))

    if type_filter and type_filter in ("IN", "OUT"):
        q = q.eq("type", type_filter)

    if text:
        # Busca por descrição (case-insensitive); se ilike não existir, backend ignora
        try:
            q = q.ilike("description", f"%{text}%")
        except Exception:
            pass

    try:
        res = q.execute()
        data = getattr(res, "data", None) or []
        return list(data)
    except PostgrestAPIError as e:
        raise _fmt_api_error(e, "SELECT")


def totals(
    dfrom: date_cls | str,
    dto: date_cls | str,
    *,
    org_id: Optional[str] = None,
) -> Dict[str, float]:
    """Totaliza entradas/saídas/saldo no período."""
    rows = list_entries(dfrom, dto, org_id=org_id)
    t_in = 0.0
    t_out = 0.0
    for r in rows:
        amt = float(r.get("amount", 0) or 0)
        if (r.get("type") or "").upper() == "IN":
            t_in += amt
        else:
            t_out += amt
    return {"in": t_in, "out": t_out, "balance": t_in - t_out}


def create_entry(data: Dict[str, Any], org_id: Optional[str] = None) -> Dict[str, Any]:
    """Cria um lançamento e retorna o registro inserido."""
    c = _get_client()
    payload = dict(data)
    if org_id and not payload.get("org_id"):
        payload["org_id"] = org_id
    try:
        res = c.table(TABLE).insert(payload).execute()
        rows = getattr(res, "data", None) or []
        return rows[0] if rows else payload
    except PostgrestAPIError as e:
        raise _fmt_api_error(e, "INSERT")


def update_entry(entry_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza um lançamento pelo id e retorna o registro atualizado."""
    c = _get_client()
    try:
        res = c.table(TABLE).update(data).eq("id", entry_id).execute()
        rows = getattr(res, "data", None) or []
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
