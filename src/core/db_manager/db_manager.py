# core/db_manager/db_manager.py  (versão Supabase)
from __future__ import annotations

import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Callable, Iterable, Optional

import httpx

from infra.supabase_client import exec_postgrest, supabase
from src.config.constants import RETRY_BASE_DELAY
from src.core.cnpj_norm import normalize_cnpj as normalize_cnpj_norm
from src.core.models import Cliente
from src.core.session.session import get_current_user

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

CLIENT_COLUMNS = (
    "id,numero,nome,razao_social,cnpj,cnpj_norm,ultima_alteracao,ultima_por,obs,"
    "org_id,deleted_at"
)


# -----------------------------------------------------------------------------
# Retry helper com backoff exponencial (compatível com data/supabase_repo.py)
# -----------------------------------------------------------------------------
RETRY_ERRORS = (
    httpx.ReadError,
    httpx.WriteError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    OSError,
)


def _with_retries(fn: Callable, tries: int = 3, base_delay: float = RETRY_BASE_DELAY):
    """
    Executa fn() com tentativas e backoff exponencial + jitter.
    Re-tenta em erros de rede/transientes (inclui WinError 10035) e 5xx.
    """
    last_exc = None
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except RETRY_ERRORS as e:
            last_exc = e
        except Exception as e:
            msg = str(e).lower()
            if "502" in msg or "bad gateway" in msg or "5xx" in msg or "503" in msg:
                last_exc = e
            else:
                raise

        if attempt < tries:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.15)
            time.sleep(delay)

    raise last_exc


def _current_user_email() -> str:
    try:
        cu = get_current_user()
        return (getattr(cu, "email", "") or "").strip()
    except Exception:
        return ""


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
        cnpj_norm=row.get("cnpj_norm"),
        ultima_alteracao=row.get("ultima_alteracao"),
        obs=row.get("obs"),
        ultima_por=row.get("ultima_por"),
    )


def _resolve_order(
    order_by: str | None, descending: Optional[bool]
) -> tuple[str, bool]:
    col, default_desc = _ORDER_MAP.get(order_by or None, _ORDER_MAP[None])
    desc = default_desc if descending is None else bool(descending)
    return col, desc


# -------------------- CRUD / LISTAGEM --------------------


def list_clientes_by_org(
    org_id: str,
    order_by: str | None = None,
    descending: Optional[bool] = None,
) -> list[Cliente]:
    """
    Lista clientes filtrando por org_id (obrigatório).
    """
    if org_id is None:
        raise ValueError("org_id obrigatório")
    col, desc = _resolve_order(order_by, descending)
    resp = exec_postgrest(
        supabase.table("clients")
        .select(CLIENT_COLUMNS)
        .is_("deleted_at", "null")
        .eq("org_id", org_id)
        .order(col, desc=desc)
    )
    return [_to_cliente(r) for r in (resp.data or [])]


def list_clientes(
    order_by: str | None = None, descending: Optional[bool] = None
) -> list[Cliente]:
    col, desc = _resolve_order(order_by, descending)
    resp = exec_postgrest(
        supabase.table("clients")
        .select(CLIENT_COLUMNS)
        .is_("deleted_at", "null")  # somente ativos
        .order(col, desc=desc)
    )
    return [_to_cliente(r) for r in (resp.data or [])]


def list_clientes_deletados(
    order_by: str | None = None, descending: Optional[bool] = None
) -> list[Cliente]:
    col, desc = _resolve_order(order_by, descending)
    resp = exec_postgrest(
        supabase.table("clients")
        .select(CLIENT_COLUMNS)
        .not_.is_("deleted_at", "null")  # somente marcados como deletados
        .order(col, desc=desc)
    )
    return [_to_cliente(r) for r in (resp.data or [])]


def get_cliente(cliente_id: int) -> Optional[Cliente]:
    resp = exec_postgrest(
        supabase.table("clients")
        .select(CLIENT_COLUMNS)
        .eq("id", cliente_id)
        .limit(1)
    )
    rows = resp.data or []
    return _to_cliente(rows[0]) if rows else None


def get_cliente_by_id(cliente_id: int) -> Optional[Cliente]:
    resp = exec_postgrest(
        supabase.table("clients")
        .select(CLIENT_COLUMNS)
        .eq("id", cliente_id)
        .limit(1)
    )
    if resp.data:
        return _to_cliente(resp.data[0])
    return None


def find_cliente_by_cnpj_norm(
    cnpj_norm: str, *, exclude_id: int | None = None
) -> Optional[Cliente]:
    normalized = normalize_cnpj_norm(cnpj_norm)
    if not normalized:
        return None

    query = (
        supabase.table("clients")
        .select(CLIENT_COLUMNS)
        .is_("deleted_at", "null")
        .eq("cnpj_norm", normalized)
        .limit(1)
    )
    if exclude_id is not None:
        query = query.neq("id", int(exclude_id))

    resp = exec_postgrest(query)
    rows = resp.data or []
    if not rows:
        return None
    return _to_cliente(rows[0])


def insert_cliente(
    numero: str,
    nome: str,
    razao_social: str,
    cnpj: str,
    obs: str,
    *,
    cnpj_norm: str | None = None,
) -> int:
    normalized = normalize_cnpj_norm(cnpj) if cnpj_norm is None else cnpj_norm
    by = _current_user_email()
    row = {
        "numero": numero,
        "nome": nome,
        "razao_social": razao_social,
        "cnpj": cnpj,
        "cnpj_norm": normalized,
        "obs": obs,
        "ultima_alteracao": _now_iso(),
        "ultima_por": by,
    }

    def _do():
        payload = dict(row)
        try:
            resp = exec_postgrest(supabase.table("clients").insert(payload))
        except Exception:
            payload.pop("ultima_por", None)
            resp = exec_postgrest(supabase.table("clients").insert(payload))

        # Muitas vezes o PostgREST retorna o registro inserido com o id
        if resp and getattr(resp, "data", None):
            try:
                return int(resp.data[0]["id"])
            except Exception:
                pass

        # Fallback: buscar pelo CNPJ mais recente
        fallback_query = supabase.table("clients").select("id").order("id", desc=True)
        if normalized:
            fallback_query = fallback_query.eq("cnpj_norm", normalized)
        else:
            fallback_query = fallback_query.eq("cnpj", cnpj)
        r2 = exec_postgrest(fallback_query.limit(1))
        if r2.data:
            return int(r2.data[0]["id"])

        raise RuntimeError("Falha ao obter ID do cliente inserido.")

    try:
        return _with_retries(_do, tries=3, base_delay=RETRY_BASE_DELAY)
    except Exception as e:
        log.warning(f"Falha ao inserir cliente após retries: {e}")
        raise


def update_cliente(
    cliente_id: int,
    numero: str,
    nome: str,
    razao_social: str,
    cnpj: str,
    obs: str,
    *,
    cnpj_norm: str | None = None,
) -> int:
    normalized = normalize_cnpj_norm(cnpj) if cnpj_norm is None else cnpj_norm
    by = _current_user_email()
    data = {
        "numero": numero,
        "nome": nome,
        "razao_social": razao_social,
        "cnpj": cnpj,
        "cnpj_norm": normalized,
        "obs": obs,
        "ultima_alteracao": _now_iso(),
        "ultima_por": by,
    }

    def _do():
        payload = dict(data)
        try:
            resp = exec_postgrest(
                supabase.table("clients").update(payload).eq("id", cliente_id)
            )
        except Exception:
            payload.pop("ultima_por", None)
            resp = exec_postgrest(
                supabase.table("clients").update(payload).eq("id", cliente_id)
            )
        # count pode vir None; usa tamanho de data como alternativa
        if getattr(resp, "count", None) is not None:
            return int(resp.count or 0)
        return len(resp.data or [])

    try:
        return _with_retries(_do, tries=3, base_delay=RETRY_BASE_DELAY)
    except Exception as e:
        log.warning(f"Falha ao atualizar cliente {cliente_id} após retries: {e}")
        raise


def update_status_only(cliente_id: int, obs: str) -> int:
    ts = _now_iso()
    by = _current_user_email()
    data = {"obs": obs, "ultima_alteracao": ts, "ultima_por": by}

    def _do():
        payload = dict(data)
        try:
            resp = exec_postgrest(
                supabase.table("clients").update(payload).eq("id", cliente_id)
            )
        except Exception:
            payload.pop("ultima_por", None)
            resp = exec_postgrest(
                supabase.table("clients").update(payload).eq("id", cliente_id)
            )
        if getattr(resp, "count", None) is not None:
            return int(resp.count or 0)
        return len(resp.data or [])

    try:
        return _with_retries(_do, tries=3, base_delay=RETRY_BASE_DELAY)
    except Exception as e:
        log.warning(f"Falha ao atualizar status do cliente {cliente_id}: {e}")
        raise


def delete_cliente(cliente_id: int) -> int:
    """Exclusão física de um único cliente (use soft_delete_clientes para lixeira)."""
    resp = exec_postgrest(supabase.table("clients").delete().eq("id", cliente_id))
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or [])


def soft_delete_clientes(ids: Iterable[int]) -> int:
    id_list = [int(i) for i in ids]
    if not id_list:
        return 0
    ts = _now_iso()
    by = _current_user_email()
    data = {"deleted_at": ts, "ultima_alteracao": ts, "ultima_por": by}
    try:
        resp = exec_postgrest(
            supabase.table("clients").update(dict(data)).in_("id", id_list)
        )
    except Exception:
        data_fb = dict(data)
        data_fb.pop("ultima_por", None)
        resp = exec_postgrest(
            supabase.table("clients").update(data_fb).in_("id", id_list)
        )

    # PostgREST pode não trazer count; fallback no len(data) retornado
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or id_list)


def restore_clientes(ids: Iterable[int]) -> int:
    id_list = [int(i) for i in ids]
    if not id_list:
        return 0
    ts = _now_iso()
    by = _current_user_email()
    data = {"deleted_at": None, "ultima_alteracao": ts, "ultima_por": by}
    try:
        resp = exec_postgrest(
            supabase.table("clients").update(dict(data)).in_("id", id_list)
        )
    except Exception:
        data_fb = dict(data)
        data_fb.pop("ultima_por", None)
        resp = exec_postgrest(
            supabase.table("clients").update(data_fb).in_("id", id_list)
        )
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or id_list)


def purge_clientes(ids: Iterable[int]) -> int:
    """Exclusão física definitiva em lote (usar com cuidado!)."""
    id_list = [int(i) for i in ids]
    if not id_list:
        return 0
    resp = exec_postgrest(supabase.table("clients").delete().in_("id", id_list))
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or [])
