"""Client search helpers using Supabase with local fallback."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from src.infra.supabase_client import exec_postgrest, is_supabase_online, supabase
from src.core.db_manager.db_manager import CLIENT_COLUMNS
from src.core.models import Cliente
from src.core.session.session import get_current_user  # << pegar org_id da sessao
from src.core.textnorm import join_and_normalize, normalize_search

log = logging.getLogger(__name__)


def _normalize_order(order_by: str | None) -> tuple[str | None, bool]:
    """Normaliza apelidos de ordenação para colunas canônicas e flag de descending."""
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


def _row_to_cliente(row: Mapping[str, Any]) -> Cliente:
    """Converte uma row retornada do backend em instância Cliente."""
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
    """Concatena campos relevantes de Cliente em blob normalizado para busca textual."""
    return join_and_normalize(
        getattr(cliente, "id", None),
        getattr(cliente, "nome", None),
        getattr(cliente, "razao_social", None),
        getattr(cliente, "cnpj", None),
        getattr(cliente, "numero", None),
        getattr(cliente, "obs", None),
    )


def _filter_rows_with_norm(rows: Sequence[Mapping[str, Any]], term: str) -> list[dict[str, Any]]:
    """
    Filtra rows já carregadas usando termo normalizado, cacheando _search_norm por row.

    Termo vazio retorna todas as rows.
    """
    query_norm = normalize_search(term)
    if not query_norm:
        return list(rows)  # type: ignore[arg-type]

    filtered: list[dict[str, Any]] = []
    for row in rows:
        # Convert to dict if needed for mutation
        row_dict = dict(row) if not isinstance(row, dict) else row
        norm = row_dict.get("_search_norm")
        if not norm:
            norm = join_and_normalize(
                row_dict.get("id"),
                row_dict.get("razao_social"),
                row_dict.get("cnpj"),
                row_dict.get("nome"),
                row_dict.get("numero"),
                row_dict.get("obs"),
            )
            row_dict["_search_norm"] = norm
        if query_norm in norm:
            filtered.append(row_dict)
    return filtered


def _filter_clientes(clientes: Sequence[Cliente], term: str) -> list[Cliente]:
    """Aplica filtro textual em clientes já carregados (uso local/offline)."""
    query_norm = normalize_search(term)
    if not query_norm:
        return list(clientes)
    return [cli for cli in clientes if query_norm in _cliente_search_blob(cli)]


def search_clientes(term: str | None, order_by: str | None = None, org_id: str | None = None) -> list[Cliente]:
    """
    Busca clientes por *term* (nome/razao/CNPJ/numero) priorizando Supabase.
    Fallback para filtro local quando offline ou em falha.

    - Quando online: exige org_id, consulta Supabase, aplica filtro local adicional
      se houver termo e reconsulta se nenhum resultado inicial.
    - Quando offline ou em falha: consulta repositório local; levanta ValueError
      se org_id for ausente.
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

            def _fetch_rows(search_term: str | None) -> list[dict[str, Any]]:
                qb = supabase.table("clients").select(CLIENT_COLUMNS).is_("deleted_at", "null").eq("org_id", org_id)
                if search_term:
                    pat = f"%{search_term}%"
                    qb = qb.or_(
                        "nome.ilike.{pat},razao_social.ilike.{pat},cnpj.ilike.{pat},numero.ilike.{pat}".format(pat=pat)
                    )
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
    except Exception as exc:
        log.warning("search_clientes: falha no Supabase, usando fallback local", exc_info=exc)

    if org_id is None:
        raise ValueError("org_id obrigatorio")
    from src.core.db_manager.db_manager import list_clientes_by_org  # evita ciclo

    clientes = list_clientes_by_org(org_id, order_by=col or None, descending=desc if col else None)
    if not term:
        return clientes
    return _filter_clientes(clientes, term)
