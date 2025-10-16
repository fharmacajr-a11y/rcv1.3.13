"""Busca de clientes via Supabase (com ordenação em Python se necessário)."""
from __future__ import annotations

import unicodedata
from typing import Optional

from core.db_manager import list_clientes
from core.models import Cliente

def _normalize_order(order_by: Optional[str]) -> tuple[Optional[str], bool]:
    if not order_by:
        return None, False
    ob = order_by.lower()
    mapping = {
        "id": ("id", False),
        "numero": ("numero", False),
        "nome": ("nome", False),
        "razao_social": ("razao_social", False),
        "cnpj": ("cnpj", False),
        "ultima_alteracao": ("ultima_alteracao", True),
    }
    return mapping.get(ob, (None, False))

def _normalize_text(s: str) -> str:
    s = (s or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def _digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())

def search_clientes(term: str, order_by: str | None = None) -> list[Cliente]:
    column, descending = _normalize_order(order_by)
    clientes = list_clientes(order_by=column, descending=descending)
    t_norm = _normalize_text(term)
    t_digits = _digits(term)
    if not t_norm and not t_digits:
        return clientes
    out: list[Cliente] = []
    for c in clientes:
        if t_digits and (t_digits in _digits(c.cnpj or "") or t_digits in _digits(c.numero or "")):
            out.append(c); continue
        blob = " ".join([c.nome or "", c.razao_social or ""]).lower()
        if t_norm and t_norm in _normalize_text(blob):
            out.append(c)
    return out