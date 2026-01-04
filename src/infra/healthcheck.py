# infra/healthcheck.py (no-OCR version)
from __future__ import annotations

import uuid
import logging
from typing import Any

from src.infra.supabase_client import get_supabase
from src.core.session.session_guard import SessionGuard

log = logging.getLogger(__name__)

# Type aliases para melhor legibilidade
HealthCheckResult = tuple[bool, str]
StorageCheckResult = tuple[bool, dict[str, Any]]
HealthPayload = dict[str, Any]


def db_check() -> HealthCheckResult:
    """Faz INSERT + DELETE reais em public.test_health para validar DB/RLS/políticas."""
    sb = get_supabase()
    test_id: str = str(uuid.uuid4())
    instance: str = str(uuid.uuid4())
    try:
        row: dict[str, str] = {"id": test_id, "instance": instance}
        sb.table("test_health").insert(row).execute()
        sb.table("test_health").delete().eq("id", test_id).execute()
        return True, "insert/delete OK"
    except Exception as e:
        return False, f"DB health falhou: {e}"


def storage_check(bucket: str) -> StorageCheckResult:
    """Verifica acesso ao bucket de storage listando conteúdo.

    Args:
        bucket: Nome do bucket a ser verificado

    Returns:
        Tupla (sucesso, info) onde info contém count ou error
    """
    sb = get_supabase()
    try:
        resp = sb.storage.from_(bucket).list()
        count: int | None = len(resp) if isinstance(resp, list) else None
        return True, {"count": count}
    except Exception as e:
        return False, {"error": str(e)}


def healthcheck(bucket: str = "rc-docs") -> HealthPayload:
    """Executa health checks: sessão, storage e DB (insert/delete).

    Args:
        bucket: Nome do bucket de storage a verificar (padrão: "rc-docs")

    Returns:
        Dicionário com:
        - ok: bool indicando se todos os checks passaram
        - items: dict com resultados de cada componente (session, storage, db)
        - bucket: nome do bucket verificado
    """
    items: dict[str, Any] = {}
    ok: bool = True

    # 1) Sessão
    alive = SessionGuard.ensure_alive()
    items["session"] = {"ok": bool(alive)}
    ok = ok and bool(alive)

    # 2) Storage
    s_ok: bool
    s_info: dict[str, Any]
    s_ok, s_info = storage_check(bucket)
    items["storage"] = {"ok": s_ok, **s_info}
    ok = ok and s_ok

    # 3) DB (INSERT/DELETE)
    db_ok: bool
    db_msg: str
    db_ok, db_msg = db_check()
    items["db"] = {"ok": db_ok, "msg": db_msg}
    ok = ok and db_ok

    if not db_ok:
        log.warning("HealthCheck DB FAIL: %s", db_msg)

    return {"ok": ok, "items": items, "bucket": bucket}
