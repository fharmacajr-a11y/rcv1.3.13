# infra/supabase_auth.py
from __future__ import annotations

import logging
from supabase import Client

from src.infra.supabase_client import get_supabase
from src.core import session
from src.utils import prefs as prefs_utils

logger = logging.getLogger(__name__)

# Type aliases para melhor legibilidade
AuthTokens = tuple[str, str]  # (access_token, refresh_token)


class AuthError(Exception):
    pass


def login_with_password(email: str, password: str) -> AuthTokens:
    """
    Faz login no Supabase (Auth) usando email/senha.
    Retorna (access_token, refresh_token) e configura o cliente global com a sessão.

    Args:
        email: Email do usuário
        password: Senha do usuário

    Returns:
        Tupla contendo (access_token, refresh_token)

    Raises:
        AuthError: Se a autenticação falhar ou a sessão for inválida
    """
    sb: Client = get_supabase()
    try:
        # supabase-py >= 2.6.0
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        if not res or not getattr(res, "session", None):
            raise AuthError("Falha ao autenticar. Verifique suas credenciais.")
        access: str = res.session.access_token
        refresh: str = res.session.refresh_token
        if not access:
            raise AuthError("Sessão inválida (sem access token).")
        # guarda na sessão do app (memória)
        session.set_current_user(email)
        session.set_tokens(access, refresh)
        return access, refresh
    except Exception as e:
        raise AuthError(str(e))


def logout(client: Client | None = None) -> None:
    """
    Faz logout do Supabase e limpa tokens da sessão local.

    Args:
        client: Cliente Supabase opcional (usa get_supabase() se None)

    Note:
        Sempre limpa a sessão local, mesmo se o logout remoto falhar.
        Também tenta limpar a sessão persistida em disco.
    """
    try:
        sb: Client = client or get_supabase()
        sb.auth.sign_out()
    except Exception as exc:
        logger.warning("Falha ao fazer logout remoto: %s", exc, exc_info=exc)
    finally:
        logger.info("Sem token; ignorando set_current_user")
        session.set_tokens(None, None)
        try:
            prefs_utils.clear_auth_session()
        except Exception:
            logger.warning("Falha ao limpar sessão persistida no logout", exc_info=True)
