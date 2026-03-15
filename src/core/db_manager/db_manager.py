# core/db_manager/db_manager.py  (versão Supabase)
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from src.infra.supabase_client import exec_postgrest, supabase
from src.core.cnpj_norm import normalize_cnpj as normalize_cnpj_norm
from src.core.models import Cliente
from src.core.session.session import get_current_user

try:
    from postgrest.exceptions import APIError as _PostgrestAPIError
except Exception:  # pragma: no cover – fallback se lib mudar
    _PostgrestAPIError = Exception  # type: ignore[assignment,misc]

log = logging.getLogger("db_manager")


class BatchInsertPartialError(Exception):
    """Exceção levantada quando um batch insert falha parcialmente.

    Attributes:
        inserted_ids: IDs dos registros inseridos com sucesso antes da falha.
        failed_batch_index: Índice (0-based) do lote que falhou.
        total_batches: Quantidade total de lotes.
        original_error: Exceção original do lote que falhou.
    """

    def __init__(
        self,
        message: str,
        *,
        inserted_ids: list[int],
        failed_batch_index: int,
        total_batches: int,
        original_error: BaseException,
    ) -> None:
        super().__init__(message)
        self.inserted_ids = inserted_ids
        self.failed_batch_index = failed_batch_index
        self.total_batches = total_batches
        self.original_error = original_error


# ---------------------------------------------------------------------------
# Detecção de erro "coluna inexistente" (PostgREST / PostgreSQL 42703)
# ---------------------------------------------------------------------------
_UNKNOWN_COL_CODES: frozenset[str] = frozenset({"42703", "PGRST204"})
_UNKNOWN_COL_KEYWORDS: tuple[str, ...] = (
    "undefined_column",
    "unknown column",
    'column "ultima_por" of relation',
    "is not a column",
)


def _is_unknown_column_error(exc: BaseException) -> bool:
    """Retorna True se *exc* indicar coluna inexistente no PostgREST/Postgres.

    Verifica ``code`` (SQLSTATE 42703 / PGRST204) e palavras-chave na mensagem.
    """
    code = getattr(exc, "code", None) or ""
    if code in _UNKNOWN_COL_CODES:
        return True
    msg = (getattr(exc, "message", None) or getattr(exc, "details", None) or str(exc)).lower()
    return any(kw in msg for kw in _UNKNOWN_COL_KEYWORDS)


def _is_unique_violation(exc: BaseException) -> bool:
    """Retorna True se *exc* indicar violação de unique constraint (SQLSTATE 23505)."""
    code = getattr(exc, "code", None) or ""
    if code == "23505":
        return True
    msg = (getattr(exc, "message", None) or getattr(exc, "details", None) or str(exc)).lower()
    return "unique" in msg and "violation" in msg


def _retry_without_ultima_por(
    primary: Callable[[], Any],
    fallback: Callable[[], Any],
    *,
    context: str,
) -> Any:
    """Executa *primary*; se PostgREST/Postgres reportar coluna 'ultima_por'
    inexistente (SQLSTATE 42703 / PGRST204), loga aviso e executa *fallback*.

    Consolida o padrão de retry que estava repetido 5× nos métodos CRUD.
    Qualquer outro erro é re-propagado sem modificação.
    """
    try:
        return primary()
    except _PostgrestAPIError as exc:
        if not _is_unknown_column_error(exc):
            raise
        log.warning("%s: coluna 'ultima_por' inexistente na tabela; aplicando fallback sem a coluna.", context)
        return fallback()


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

CLIENT_COLUMNS = "id,numero,nome,razao_social,cnpj,cnpj_norm,ultima_alteracao,ultima_por,obs,org_id,deleted_at,status_anvisa,status_farmacia_popular"
ClienteRow = dict[str, Any]


# -----------------------------------------------------------------------------
# Retry helper com backoff exponencial (compatível com data/supabase_repo.py)
# -----------------------------------------------------------------------------
def _current_user_email() -> str:
    try:
        cu: Any = get_current_user()
        return (getattr(cu, "email", "") or "").strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Org-id do usuário corrente (defesa em profundidade — PR18)
# ---------------------------------------------------------------------------
DEFAULT_PAGE_LIMIT: int = 200


def _current_org_id() -> str | None:
    """Retorna o org_id do usuário autenticado, ou None se indisponível."""
    try:
        resp = supabase.auth.get_user()
        user = getattr(resp, "user", None) or resp
        uid = getattr(user, "id", None)
        if not uid and isinstance(resp, dict):
            d = resp.get("data") or {}
            u = resp.get("user") or d.get("user") or {}
            uid = u.get("id") or u.get("uid")
        if not uid:
            return None
        res = exec_postgrest(supabase.table("memberships").select("org_id").eq("user_id", uid).limit(1))
        rows: list[Any] = res.data if isinstance(getattr(res, "data", None), list) else []
        if rows and rows[0].get("org_id"):
            return str(rows[0]["org_id"])
    except Exception as exc:
        log.debug("_current_org_id: falha ao resolver org_id: %s", exc)
    return None


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


def _to_cliente(row: dict[str, Any]) -> Cliente:
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
        status_anvisa=row.get("status_anvisa"),
        status_farmacia_popular=row.get("status_farmacia_popular"),
    )


def _resolve_order(order_by: str | None, descending: bool | None) -> tuple[str, bool]:
    col: str
    default_desc: bool
    col, default_desc = _ORDER_MAP.get(order_by or None, _ORDER_MAP[None])
    desc: bool = default_desc if descending is None else bool(descending)
    return col, desc


# -------------------- CRUD / LISTAGEM --------------------


def list_clientes_by_org(
    org_id: str,
    order_by: str | None = None,
    descending: bool | None = None,
    *,
    limit: int | None = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> list[Cliente]:
    """
    Lista clientes filtrando por org_id (obrigatório) com paginação.
    """
    if org_id is None:
        raise ValueError("org_id obrigatório")
    col: str
    desc: bool
    col, desc = _resolve_order(order_by, descending)
    query: Any = (
        supabase.table("clients")
        .select(CLIENT_COLUMNS)
        .is_("deleted_at", "null")
        .eq("org_id", org_id)
        .order(col, desc=desc)
        .order("id", desc=True)  # tiebreaker estável
    )
    if limit is not None:
        query = query.range(offset, offset + limit - 1)
    resp: Any = exec_postgrest(query)
    return [_to_cliente(r) for r in (resp.data or [])]


def list_clientes(
    order_by: str | None = None,
    descending: bool | None = None,
    *,
    limit: int | None = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> list[Cliente]:
    """Lista clientes ativos com filtro explícito por org_id e paginação.

    PR18: defesa em profundidade — sempre aplica org_id quando disponível.
    Se org_id não puder ser resolvido, emite warning e executa sem filtro
    (RLS do Supabase continua protegendo).
    """
    col: str
    desc: bool
    col, desc = _resolve_order(order_by, descending)
    query: Any = supabase.table("clients").select(CLIENT_COLUMNS).is_("deleted_at", "null")
    org = _current_org_id()
    if org:
        query = query.eq("org_id", org)
    else:
        log.warning("list_clientes: org_id indisponível; confiando apenas no RLS.")
    query = query.order(col, desc=desc).order("id", desc=True)
    if limit is not None:
        query = query.range(offset, offset + limit - 1)
    else:
        log.warning("list_clientes: chamado sem limite de paginação (fetch_all).")
    resp: Any = exec_postgrest(query)
    return [_to_cliente(r) for r in (resp.data or [])]


def list_clientes_deletados(
    order_by: str | None = None,
    descending: bool | None = None,
    *,
    limit: int | None = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> list[Cliente]:
    """Lista clientes na lixeira com filtro explícito por org_id e paginação."""
    col: str
    desc: bool
    col, desc = _resolve_order(order_by, descending)
    query: Any = supabase.table("clients").select(CLIENT_COLUMNS).not_.is_("deleted_at", "null")
    org = _current_org_id()
    if org:
        query = query.eq("org_id", org)
    else:
        log.warning("list_clientes_deletados: org_id indisponível; confiando apenas no RLS.")
    query = query.order(col, desc=desc).order("id", desc=True)
    if limit is not None:
        query = query.range(offset, offset + limit - 1)
    resp: Any = exec_postgrest(query)
    return [_to_cliente(r) for r in (resp.data or [])]


def get_cliente(cliente_id: int) -> Cliente | None:
    resp: Any = exec_postgrest(supabase.table("clients").select(CLIENT_COLUMNS).eq("id", cliente_id).limit(1))
    rows: list[Any] = resp.data or []
    return _to_cliente(rows[0]) if rows else None


def get_cliente_by_id(cliente_id: int) -> Cliente | None:
    resp: Any = exec_postgrest(supabase.table("clients").select(CLIENT_COLUMNS).eq("id", cliente_id).limit(1))
    if resp.data:
        return _to_cliente(resp.data[0])
    return None


def find_cliente_by_cnpj_norm(cnpj_norm: str, *, exclude_id: int | None = None) -> Cliente | None:
    normalized: str = normalize_cnpj_norm(cnpj_norm)
    if not normalized:
        return None

    query: Any = (
        supabase.table("clients").select(CLIENT_COLUMNS).is_("deleted_at", "null").eq("cnpj_norm", normalized).limit(1)
    )
    if exclude_id is not None:
        query = query.neq("id", int(exclude_id))

    resp: Any = exec_postgrest(query)
    rows: list[Any] = resp.data or []
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
    status_anvisa: str | None = None,
    status_farmacia_popular: str | None = None,
) -> int:
    normalized: str = normalize_cnpj_norm(cnpj) if cnpj_norm is None else cnpj_norm
    by: str = _current_user_email()
    org = _current_org_id()
    row: dict[str, Any] = {
        "numero": numero,
        "nome": nome,
        "razao_social": razao_social,
        "cnpj": cnpj,
        "cnpj_norm": normalized,
        "obs": obs,
        "ultima_alteracao": _now_iso(),
        "ultima_por": by,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status_anvisa": status_anvisa,
        "status_farmacia_popular": status_farmacia_popular,
    }
    if org:
        row["org_id"] = org

    def _do() -> int:
        payload: dict[str, Any] = dict(row)
        resp = _retry_without_ultima_por(
            lambda: exec_postgrest(supabase.table("clients").insert(payload)),
            lambda: exec_postgrest(
                supabase.table("clients").insert({k: v for k, v in payload.items() if k != "ultima_por"})
            ),
            context="insert_cliente",
        )

        # Muitas vezes o PostgREST retorna o registro inserido com o id
        if resp and getattr(resp, "data", None):
            try:
                return int(resp.data[0]["id"])
            except Exception as exc:
                log.debug("Falha ao extrair id do cliente inserido", exc_info=exc)

        # Fallback: buscar pelo CNPJ mais recente
        fallback_query: Any = supabase.table("clients").select("id").order("id", desc=True)
        if normalized:
            fallback_query = fallback_query.eq("cnpj_norm", normalized)
        else:
            fallback_query = fallback_query.eq("cnpj", cnpj)
        r2: Any = exec_postgrest(fallback_query.limit(1))
        if r2.data:
            return int(r2.data[0]["id"])

        raise RuntimeError("Falha ao obter ID do cliente inserido.")

    try:
        return _do()
    except Exception as e:
        log.warning(f"Falha ao inserir cliente após retries: {e}")
        raise


def insert_clientes_batch(
    clientes: list[dict[str, Any]],
    *,
    batch_size: int = 200,
) -> list[int]:
    """Insere múltiplos clientes em lotes via Supabase PostgREST.

    Cada lote é enviado num único POST (array insert). Isso é MUITO mais
    rápido que chamadas individuais (1 HTTP req por lote vs 1 por cliente).

    Args:
        clientes: Lista de dicts com campos do cliente (mesmo formato de insert_cliente).
                  Chaves esperadas: numero, nome, razao_social, cnpj, obs.
                  cnpj_norm será calculado se ausente.
        batch_size: Quantidade de registros por POST (default 200).

    Returns:
        Lista de IDs dos clientes inseridos.
    """
    if not clientes:
        return []

    by = _current_user_email()
    now = _now_iso()
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    org = _current_org_id()

    # Preparar payloads
    payloads: list[dict[str, Any]] = []
    for c in clientes:
        cnpj_raw = c.get("cnpj", "") or ""
        payload: dict[str, Any] = {
            "numero": c.get("numero", "") or "",
            "nome": c.get("nome", "") or "",
            "razao_social": c.get("razao_social", "") or "",
            "cnpj": cnpj_raw,
            "cnpj_norm": c.get("cnpj_norm") or normalize_cnpj_norm(cnpj_raw),
            "obs": c.get("obs", "") or "",
            "ultima_alteracao": now,
            "ultima_por": by,
            "created_at": created,
        }
        if org:
            payload["org_id"] = org
        payloads.append(payload)

    inserted_ids: list[int] = []
    skipped_cnpjs: list[str] = []
    total_batches = (len(payloads) + batch_size - 1) // batch_size
    for batch_idx, i in enumerate(range(0, len(payloads), batch_size)):
        batch = payloads[i : i + batch_size]
        try:
            resp = exec_postgrest(supabase.table("clients").insert(batch))
            if resp and getattr(resp, "data", None):
                for row in resp.data:
                    try:
                        inserted_ids.append(int(row["id"]))
                    except (KeyError, TypeError, ValueError):
                        pass
        except _PostgrestAPIError as exc:
            if _is_unknown_column_error(exc):
                # Retry sem ultima_por
                log.warning(
                    "insert_clientes_batch lote %d: coluna 'ultima_por' inexistente; aplicando fallback.",
                    batch_idx + 1,
                )
                for p in batch:
                    p.pop("ultima_por", None)
                resp = exec_postgrest(supabase.table("clients").insert(batch))
                if resp and getattr(resp, "data", None):
                    for row in resp.data:
                        try:
                            inserted_ids.append(int(row["id"]))
                        except (KeyError, TypeError, ValueError):
                            pass
            elif _is_unique_violation(exc):
                # Fallback: inserir um a um para identificar duplicados
                log.info(
                    "insert_clientes_batch: unique violation no lote %d, retentando individualmente.",
                    batch_idx + 1,
                )
                for single in batch:
                    try:
                        resp = exec_postgrest(supabase.table("clients").insert(single))
                        if resp and getattr(resp, "data", None):
                            for row in resp.data:
                                try:
                                    inserted_ids.append(int(row["id"]))
                                except (KeyError, TypeError, ValueError):
                                    pass
                    except _PostgrestAPIError as single_exc:
                        if _is_unique_violation(single_exc):
                            cnpj = single.get("cnpj_norm") or single.get("cnpj", "?")
                            log.info("insert_clientes_batch: CNPJ duplicado ignorado: %s", cnpj)
                            skipped_cnpjs.append(cnpj)
                        else:
                            raise
            else:
                log.error(
                    "insert_clientes_batch: falha no lote %d/%d (%d já inseridos de %d).",
                    batch_idx + 1,
                    total_batches,
                    len(inserted_ids),
                    len(clientes),
                )
                raise BatchInsertPartialError(
                    f"Falha no lote {batch_idx + 1}/{total_batches}: {exc}",
                    inserted_ids=inserted_ids,
                    failed_batch_index=batch_idx,
                    total_batches=total_batches,
                    original_error=exc,
                ) from exc

    if skipped_cnpjs:
        log.info("insert_clientes_batch: %d CNPJ(s) duplicados ignorados.", len(skipped_cnpjs))
    log.info("insert_clientes_batch: %d/%d inseridos com sucesso.", len(inserted_ids), len(clientes))
    return inserted_ids


def update_cliente(
    cliente_id: int,
    numero: str,
    nome: str,
    razao_social: str,
    cnpj: str,
    obs: str,
    *,
    cnpj_norm: str | None = None,
    status_anvisa: str | None = None,
    status_farmacia_popular: str | None = None,
) -> int:
    normalized: str = normalize_cnpj_norm(cnpj) if cnpj_norm is None else cnpj_norm
    by: str = _current_user_email()
    data: dict[str, Any] = {
        "numero": numero,
        "nome": nome,
        "razao_social": razao_social,
        "cnpj": cnpj,
        "cnpj_norm": normalized,
        "obs": obs,
        "ultima_alteracao": _now_iso(),
        "ultima_por": by,
        "status_anvisa": status_anvisa,
        "status_farmacia_popular": status_farmacia_popular,
    }

    def _do() -> int:
        payload: dict[str, Any] = dict(data)
        resp = _retry_without_ultima_por(
            lambda: exec_postgrest(supabase.table("clients").update(payload).eq("id", cliente_id)),
            lambda: exec_postgrest(
                supabase.table("clients")
                .update({k: v for k, v in payload.items() if k != "ultima_por"})
                .eq("id", cliente_id)
            ),
            context="update_cliente",
        )
        # count pode vir None; usa tamanho de data como alternativa
        if getattr(resp, "count", None) is not None:
            return int(resp.count or 0)
        return len(resp.data or [])

    try:
        return _do()
    except Exception as e:
        log.warning(f"Falha ao atualizar cliente {cliente_id} após retries: {e}")
        raise


def update_status_only(cliente_id: int, obs: str) -> int:
    ts: str = _now_iso()
    by: str = _current_user_email()
    data: dict[str, Any] = {"obs": obs, "ultima_alteracao": ts, "ultima_por": by}

    def _do() -> int:
        payload: dict[str, Any] = dict(data)
        resp = _retry_without_ultima_por(
            lambda: exec_postgrest(supabase.table("clients").update(payload).eq("id", cliente_id)),
            lambda: exec_postgrest(
                supabase.table("clients")
                .update({k: v for k, v in payload.items() if k != "ultima_por"})
                .eq("id", cliente_id)
            ),
            context="update_status_only",
        )
        if getattr(resp, "count", None) is not None:
            return int(resp.count or 0)
        return len(resp.data or [])

    try:
        return _do()
    except Exception as e:
        log.warning(f"Falha ao atualizar status do cliente {cliente_id}: {e}")
        raise


def delete_cliente(cliente_id: int) -> int:
    """Exclusão física de um único cliente (use soft_delete_clientes para lixeira)."""
    resp: Any = exec_postgrest(supabase.table("clients").delete().eq("id", cliente_id))
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or [])


def soft_delete_clientes(ids: Iterable[int]) -> int:
    id_list: list[int] = [int(i) for i in ids]
    if not id_list:
        return 0
    ts: str = _now_iso()
    by: str = _current_user_email()
    data: dict[str, Any] = {"deleted_at": ts, "ultima_alteracao": ts, "ultima_por": by}
    resp = _retry_without_ultima_por(
        lambda: exec_postgrest(supabase.table("clients").update(dict(data)).in_("id", id_list)),
        lambda: exec_postgrest(
            supabase.table("clients").update({k: v for k, v in data.items() if k != "ultima_por"}).in_("id", id_list)
        ),
        context="soft_delete_clientes",
    )

    # PostgREST pode não trazer count; fallback no len(data) retornado
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or id_list)


def restore_clientes(ids: Iterable[int]) -> int:
    id_list: list[int] = [int(i) for i in ids]
    if not id_list:
        return 0
    ts: str = _now_iso()
    by: str = _current_user_email()
    data: dict[str, Any] = {"deleted_at": None, "ultima_alteracao": ts, "ultima_por": by}
    resp = _retry_without_ultima_por(
        lambda: exec_postgrest(supabase.table("clients").update(dict(data)).in_("id", id_list)),
        lambda: exec_postgrest(
            supabase.table("clients").update({k: v for k, v in data.items() if k != "ultima_por"}).in_("id", id_list)
        ),
        context="restore_clientes",
    )
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or id_list)


def purge_clientes(ids: Iterable[int]) -> int:
    """Exclusão física definitiva em lote (usar com cuidado!)."""
    id_list: list[int] = [int(i) for i in ids]
    if not id_list:
        return 0
    resp: Any = exec_postgrest(supabase.table("clients").delete().in_("id", id_list))
    if getattr(resp, "count", None) is not None:
        return int(resp.count or 0)
    return len(resp.data or [])
