# infra/healthcheck.py
from __future__ import annotations
from typing import Dict, Any
from infra.supabase_client import get_supabase
from core.session.session_guard import SessionGuard

DEFAULT_BUCKET = "rc-docs"  # altere se seu bucket tiver outro nome


def healthcheck(bucket: str = DEFAULT_BUCKET) -> Dict[str, Any]:
    """
    Verifica:
      - Sessão válida (get_session/refresh).
      - Leitura do Storage (listagem no bucket).
    Retorna dict com 'ok' e itens detalhados.
    """
    sb = get_supabase()
    items = {}
    ok = True

    # 1) Sessão
    alive = SessionGuard.ensure_alive()
    items["session"] = {"ok": bool(alive)}
    ok = ok and bool(alive)

    # 2) Storage (lista raiz do bucket)
    try:
        resp = sb.storage.from_(bucket).list()
        # supabase-py retorna lista; qualquer retorno sem exceção já validou acesso
        items["storage"] = {
            "ok": True,
            "count": len(resp) if isinstance(resp, list) else None,
        }
    except Exception as e:
        items["storage"] = {"ok": False, "error": str(e)}
        ok = False

    return {"ok": ok, "items": items, "bucket": bucket}
