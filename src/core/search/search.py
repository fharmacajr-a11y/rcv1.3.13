"""Busca de clientes via Supabase (com ordenação em Python se necessário)."""

from __future__ import annotations

import unicodedata
from typing import Optional, List

from infra.supabase_client import exec_postgrest, supabase, is_supabase_online
from src.core.models import Cliente
from src.core.session.session import get_current_user  # << pegar org_id da sessão


def _normalize_order(order_by: Optional[str]) -> tuple[Optional[str], bool]:
    if not order_by:
        return None, False
    ob = order_by.lower()
    mapping = {
        "nome": ("nome", False),
        "razao social": ("razao_social", False),
        "razao_social": ("razao_social", False),
        "cnpj": ("cnpj", False),
        "ultima alteracao": ("ultima_alteracao", True),
        "ultima_alteracao": ("ultima_alteracao", True),
    }
    return mapping.get(ob, (None, False))


def _normalize_text(s: str) -> str:
    s = (s or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _row_to_cliente(row: dict) -> Cliente:
    return Cliente(
        id=row.get("id"),
        numero=row.get("numero"),
        nome=row.get("nome"),
        razao_social=row.get("razao_social"),
        cnpj=row.get("cnpj"),
        ultima_alteracao=row.get("ultima_alteracao"),
        obs=row.get("obs"),
    )


def search_clientes(
    term: str | None,
    order_by: Optional[str] = None,
    org_id: Optional[str] = None
) -> list[Cliente]:
    """
    Busca clientes por *term* (nome/razão/CNPJ/número) priorizando Supabase.
    Fallback para filtro local quando offline.
    """
    # Se não veio parâmetro, tenta pegar da sessão
    if org_id is None:
        cu = get_current_user()
        org_id = getattr(cu, "org_id", None) if cu else None

    term = (term or "").strip()
    col, desc = _normalize_order(order_by)

    # Preferir Supabase quando online
    try:
        if is_supabase_online():
            if org_id is None:
                raise ValueError("org_id obrigatório")
            qb = (
                supabase.table("clients")
                .select("*")
                .is_("deleted_at", "null")
                .eq("org_id", org_id)
            )
            if term:
                pat = f"%{term}%"
                # nome, razao_social, cnpj, numero (WhatsApp)
                qb = qb.or_(f"nome.ilike.{pat},razao_social.ilike.{pat},cnpj.ilike.{pat},numero.ilike.{pat}")
            if col:
                qb = qb.order(col, desc=desc)
            resp = exec_postgrest(qb)
            rows = resp.data or []
            return [_row_to_cliente(r) for r in rows]
    except Exception:
        # qualquer falha → cai no fallback local
        pass

    # Fallback offline/local
    if org_id is None:
        raise ValueError("org_id obrigatório")
    from src.core.db_manager.db_manager import list_clientes_by_org  # evita ciclo
    clientes = list_clientes_by_org(org_id, order_by=col or None, descending=desc if col else None)
    if not term:
        return clientes

    # filtro local por texto/dígitos
    t_norm = _normalize_text(term)
    t_digits = _digits(term)
    if not t_norm and not t_digits:
        return clientes

    out: List[Cliente] = []
    for c in clientes:
        if t_digits and (t_digits in _digits(c.cnpj or "") or t_digits in _digits(c.numero or "")):
            out.append(c)
            continue
        blob = " ".join([c.nome or "", c.razao_social or ""]).lower()
        if t_norm and t_norm in _normalize_text(blob):
            out.append(c)
    return out
