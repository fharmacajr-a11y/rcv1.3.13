# infra/supabase_auth.py
from __future__ import annotations
import logging
from typing import Tuple
from supabase import Client
from infra.supabase_client import get_supabase
from src.core import session

logger = logging.getLogger(__name__)


class AuthError(Exception):
    pass


def login_with_password(email: str, password: str) -> Tuple[str, str]:
    """
    Faz login no Supabase (Auth) usando email/senha.
    Retorna (access_token, refresh_token) e configura o cliente global com a sessão.
    """
    sb: Client = get_supabase()
    try:
        # supabase-py >= 2.6.0
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        if not res or not getattr(res, "session", None):
            raise AuthError("Falha ao autenticar. Verifique suas credenciais.")
        access = res.session.access_token
        refresh = res.session.refresh_token
        if not access:
            raise AuthError("Sessão inválida (sem access token).")
        # guarda na sessão do app (memória)
        session.set_current_user(email)
        session.set_tokens(access, refresh)
        return access, refresh
    except Exception as e:
        raise AuthError(str(e))


def logout():
    try:
        sb: Client = get_supabase()
        sb.auth.sign_out()
    except Exception:
        pass
    finally:
        # Proteger contra None antes de chamar set_current_user
        token = None  # logout sempre limpa o token
        if token is None:
            logger.info("Sem token; ignorando set_current_user")
        else:
            session.set_current_user(token)
        session.set_tokens(None, None)
