# core/session/session_guard.py
from __future__ import annotations

import logging

from src.infra.supabase_client import get_supabase
from src.core import session

log = logging.getLogger(__name__)


class SessionGuard:
    @staticmethod
    def ensure_alive() -> bool:
        """
        Garante que a sessão do Supabase está válida.
        Tenta get_session() (que já renova se expirou) e,
        em último caso, tenta refresh_session().
        Retorna True se há sessão válida, False caso contrário.
        """
        sb = get_supabase()
        try:
            # get_session tenta renovar se preciso (doc supabase-py)
            res = sb.auth.get_session()
            if getattr(res, "session", None) and getattr(res.session, "access_token", None):
                return True
        except Exception as exc:
            log.debug("SessionGuard: get_session falhou", exc_info=exc)
        # Tentativa explícita de refresh
        try:
            res = sb.auth.refresh_session()
            if getattr(res, "session", None) and getattr(res.session, "access_token", None):
                session.set_tokens(res.session.access_token, res.session.refresh_token)
                return True
        except Exception as exc:
            log.debug("SessionGuard: refresh_session falhou", exc_info=exc)
        return False
