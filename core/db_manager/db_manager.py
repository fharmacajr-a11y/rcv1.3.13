# core/db_manager/db_manager.py  (versão Supabase)
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Iterable, Optional

from infra.supabase_client import supabase
from core.models import Cliente

log = logging.getLogger("db_manager")

# Mapa de ordenação: (coluna, descending_default)
_ORDER_MAP: dict[str | None, tuple[str, bool]] = {
    None: ("id", True),
    "id": ("id", True),
    "nome": ("nome", False),
    "razao_social": ("razao_social", False),
    "cnpj": ("cnpj", False),
    "numero": ("numero", False),
    "ultima_alteracao": ("ultima_alteracao", True),  # mais recente primeiro por padrão
}


def init_db() -> None:
    """
    No modo Supabase, não há DB local a inicializar.
    Mantemos a função para compatibilidade com main.py.
    """
    if os.getenv("RC_NO_LOCAL_FS") == "1":
        log.info("RC_NO_LOCAL_FS=1: pulando criação/uso de DB local (modo cloud-only).")
    else:
        log.info("init_db(): usando Supabase; nenhum DB local a preparar.")


def init_or_upgrade() -> None:
    """
    Mantida por compatibilidade; no modo Supabase não há migrações locais.
    """
    log.info("init_or_upgrade(): nada a fazer no modo Supabase.")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_cliente(row: dict) -> Cliente:
    return Cliente(
        id=row.get("id"),
        numero=row.get("numero"),
        nome=row.get("nome"),
        razao_social=row.get("razao_social"),
        cnpj=row.get("cnpj"),
        ultima_alteracao=row.get("ultima_alteracao"),
        obs=row.get("obs"),
    )


def _resolve_order(
    order_by: str | None, descending: Optional[bool]
) -> tuple[str, bool]:
    col, default_desc = _ORDER_MAP.get(order_by or None, _ORDER_MAP[None])
    desc = default_desc if descending is None else bool(descending)
    return col, desc


# -------------------- CRUD / LISTAGEM --------------------


def list_clientes(
    order_by: str | None = None, descending: Optional[bool] = None
) -> list[Cliente]:
    col, desc = _resolve_order(order_by, descending)
    resp = (
        supabase.table("clients")
        .select("*")
        .is_("deleted_at", "null")  # somente ativos
        .order(col, desc=desc)
        .execute()
    )
    return [_to_cliente(r) for r in (resp.data or [])]


def list_clientes_deletados(
    order_by: str | None = None, descending: Optional[bool] = None
) -> list[Cliente]:
    col, desc = _resolve_order(order_by, descending)
    resp = (
        supabase.table("clients")
        .select("*")
        .not_.is_("deleted_at", "null")  # somente marcados como deletados
        .order(col, desc=desc)
        .execute()
    )
    return [_to_cliente(r) for r in (resp.data or [])]


def get_cliente(cliente_id: int) -> Optional[Cliente]:
    resp = supabase.table("clients").select("*").eq("id", cliente_id).limit(1).execute()
    rows = resp.data or []
    return _to_cliente(rows[0]) if rows else None


def get_cliente_by_id(cliente_id: int) -> Optional[Cliente]:
    resp = supabase.table("clients").select("*").eq("id", cliente_id).limit(1).execute()
    if resp.data:
        return _to_cliente(resp.data[0])
    return None


def insert_cliente(
    numero: str, nome: str, razao_social: str, cnpj: str, obs: str
) -> int:
    row = {
        "numero": numero,
        "nome": nome,
        "razao_social": razao_social,
        "cnpj": cnpj,
        "obs": obs,
        "ultima_alteracao": _now_iso(),
    }

    # IMPORTANTE: não encadear .select() após insert (evita AttributeError)
    resp = supabase.table("clients").insert(row).execute()

    # Muitas vezes o PostgREST retorna o registro inserido com o id
    if resp and getattr(resp, "data", None):
        try:
            return int(resp.data[0]["id"])
        except Exception:
            pass

    # Fallback: buscar pelo CNPJ mais recente
    r2 = (
        supabase.table("clients")
        .select("id")
        .eq("cnpj", cnpj)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    if r2.data:
        return int(r2.data[0]["id"])

    raise RuntimeError("Falha ao obter ID do cliente inserido.")


def update_cliente(
    cliente_id: int, numero: str, nome: str, razao_social: str, cnpj: str, obs: str
) -> int:
    data = {
        "numero": numero,
        "nome": nome,
        "razao_social": razao_social,
        "cnpj": cnpj,
        "obs": obs,
        "ultima_alteracao": _now_iso(),
    }
    resp = supabase.table("clients").update(data).eq("id", cliente_id).execute()

    # count pode vir None; usa tamanho de data como alternativa
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or [])


def delete_cliente(cliente_id: int) -> int:
    """Exclusão física de um único cliente (use soft_delete_clientes para lixeira)."""
    resp = supabase.table("clients").delete().eq("id", cliente_id).execute()
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or [])


def soft_delete_clientes(ids: Iterable[int]) -> int:
    id_list = [int(i) for i in ids]
    if not id_list:
        return 0
    ts = _now_iso()
    data = {"deleted_at": ts, "ultima_alteracao": ts}
    resp = supabase.table("clients").update(data).in_("id", id_list).execute()

    # PostgREST pode não trazer count; fallback no len(data) retornado
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or id_list)


def restore_clientes(ids: Iterable[int]) -> int:
    id_list = [int(i) for i in ids]
    if not id_list:
        return 0
    ts = _now_iso()
    data = {"deleted_at": None, "ultima_alteracao": ts}
    resp = supabase.table("clients").update(data).in_("id", id_list).execute()
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or id_list)


def purge_clientes(ids: Iterable[int]) -> int:
    """Exclusão física definitiva em lote (usar com cuidado!)."""
    id_list = [int(i) for i in ids]
    if not id_list:
        return 0
    resp = supabase.table("clients").delete().in_("id", id_list).execute()
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or [])
