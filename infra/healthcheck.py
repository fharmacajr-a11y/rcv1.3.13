# infra/healthcheck.py (no-OCR version)
from __future__ import annotations
from typing import Dict, Any, Tuple
import uuid
import logging

from infra.supabase_client import get_supabase
from src.core.session.session_guard import SessionGuard

log = logging.getLogger(__name__)


def db_check() -> Tuple[bool, str]:
    """Faz INSERT + DELETE reais em public.test_health para validar DB/RLS/políticas."""
    sb = get_supabase()
    test_id = str(uuid.uuid4())
    instance = str(uuid.uuid4())
    try:
        row = {"id": test_id, "instance": instance}
        sb.table("test_health").insert(row).execute()
        sb.table("test_health").delete().eq("id", test_id).execute()
        return True, "insert/delete OK"
    except Exception as e:
        return False, f"DB health falhou: {e}"


def storage_check(bucket: str) -> Tuple[bool, Dict[str, Any]]:
    sb = get_supabase()
    try:
        resp = sb.storage.from_(bucket).list()
        return True, {"count": len(resp) if isinstance(resp, list) else None}
    except Exception as e:
        return False, {"error": str(e)}


def healthcheck(bucket: str = "rc-docs") -> Dict[str, Any]:
    """Executa health checks: sessão, storage e DB (insert/delete)."""
    items: Dict[str, Any] = {}
    ok = True

    # 1) Sessão
    alive = SessionGuard.ensure_alive()
    items["session"] = {"ok": bool(alive)}
    ok = ok and bool(alive)

    # 2) Storage
    s_ok, s_info = storage_check(bucket)
    items["storage"] = {"ok": s_ok, **s_info}
    ok = ok and s_ok

    # 3) DB (INSERT/DELETE)
    db_ok, db_msg = db_check()
    items["db"] = {"ok": db_ok, "msg": db_msg}
    ok = ok and db_ok

    if not db_ok:
        log.warning("HealthCheck DB FAIL: %s", db_msg)

    return {"ok": ok, "items": items, "bucket": bucket}
