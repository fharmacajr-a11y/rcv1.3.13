"""Client search helpers using Supabase with local fallback."""

from __future__ import annotations

from typing import List, Optional

from infra.supabase_client import exec_postgrest, is_supabase_online, supabase
from src.core.db_manager.db_manager import CLIENT_COLUMNS
from src.core.models import Cliente
from src.core.session.session import get_current_user  # << pegar org_id da sessao
from src.core.textnorm import join_and_normalize, normalize_search


def _normalize_order(order_by: Optional[str]) -> tuple[Optional[str], bool]:
    if not order_by:
        return None, False
    mapping = {
        "nome": ("nome", False),
        "razao social": ("razao_social", False),
        "razao_social": ("razao_social", False),
        "cnpj": ("cnpj", False),
        "id": ("id", False),
        "ultima alteracao": ("ultima_alteracao", True),
        "ultima_alteracao": ("ultima_alteracao", True),
    }
    return mapping.get(order_by.lower(), (None, False))


def _row_to_cliente(row: dict) -> Cliente:
    return Cliente(
        id=row.get("id"),
        numero=row.get("numero"),
        nome=row.get("nome"),
        razao_social=row.get("razao_social"),
        cnpj=row.get("cnpj"),
        cnpj_norm=row.get("cnpj_norm"),
        ultima_alteracao=row.get("ultima_alteracao"),
        obs=row.get("obs"),
        ultima_por=row.get("ultima_por"),
        created_at=row.get("created_at"),
    )


def _cliente_search_blob(cliente: Cliente) -> str:
    return join_and_normalize(
        getattr(cliente, "id", None),
        getattr(cliente, "nome", None),
        getattr(cliente, "razao_social", None),
        getattr(cliente, "cnpj", None),
        getattr(cliente, "numero", None),
        getattr(cliente, "obs", None),
    )


def _filter_rows_with_norm(rows: List[dict], term: str) -> List[dict]:
    query_norm = normalize_search(term)
    if not query_norm:
        return rows

    filtered: List[dict] = []
    for row in rows:
        norm = row.get("_search_norm")
        if not norm:
            norm = join_and_normalize(
                row.get("id"),
                row.get("razao_social"),
                row.get("cnpj"),
                row.get("nome"),
                row.get("numero"),
                row.get("obs"),
            )
            row["_search_norm"] = norm
        if query_norm in norm:
            filtered.append(row)
    return filtered


def _filter_clientes(clientes: List[Cliente], term: str) -> List[Cliente]:
    query_norm = normalize_search(term)
    if not query_norm:
        return clientes
    return [cli for cli in clientes if query_norm in _cliente_search_blob(cli)]


def search_clientes(term: str | None, order_by: Optional[str] = None, org_id: Optional[str] = None) -> list[Cliente]:
    """
    Busca clientes por *term* (nome/razao/CNPJ/numero) priorizando Supabase.
    Fallback para filtro local quando offline.
    """
    if org_id is None:
        current_user = get_current_user()
        org_id = getattr(current_user, "org_id", None) if current_user else None

    term = (term or "").strip()
    col, desc = _normalize_order(order_by)

    try:
        if is_supabase_online():
            if org_id is None:
                raise ValueError("org_id obrigatorio")

            def _fetch_rows(search_term: str | None) -> List[dict]:
                qb = supabase.table("clients").select(CLIENT_COLUMNS).is_("deleted_at", "null").eq("org_id", org_id)
                if search_term:
                    pat = f"%{search_term}%"
                    qb = qb.or_("nome.ilike.{pat},razao_social.ilike.{pat},cnpj.ilike.{pat},numero.ilike.{pat}".format(pat=pat))
                if col:
                    qb = qb.order(col, desc=desc)
                resp_inner = exec_postgrest(qb)
                return list(resp_inner.data or [])

            rows = _fetch_rows(term)
            if term:
                rows = _filter_rows_with_norm(rows, term)
                if not rows:
                    rows = _filter_rows_with_norm(_fetch_rows(None), term)
            clientes = [_row_to_cliente(r) for r in rows]
            if term:
                return _filter_clientes(clientes, term)
            return clientes
    except Exception:
        pass

    if org_id is None:
        raise ValueError("org_id obrigatorio")
    from src.core.db_manager.db_manager import list_clientes_by_org  # evita ciclo

    clientes = list_clientes_by_org(org_id, order_by=col or None, descending=desc if col else None)
    if not term:
        return clientes
    return _filter_clientes(clientes, term)
