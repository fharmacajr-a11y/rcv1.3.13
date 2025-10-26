# -------------------------------- data/auth_bootstrap.py --------------------------------
import os
import logging
from typing import Optional

log = logging.getLogger(__name__)

def _get_access_token(client) -> Optional[str]:
    try:
        sess = client.auth.get_session()
        token = getattr(sess, "access_token", None)
        return token or None
    except Exception:
        return None

def _postgrest_bind(client, token: Optional[str]) -> None:
    if not token:
        return
    try:
        client.postgrest.auth(token)
    except Exception as e:
        log.warning("postgrest.auth falhou: %s", e)

def ensure_signed_in(client) -> None:
    """
    Garante que exista sessão válida no Supabase.
    Fluxo:
      1) Se já há sessão -> apenas injeta no PostgREST e retorna.
      2) Se não há sessão -> tenta login headless com SUPABASE_EMAIL/SUPABASE_PASSWORD (.env) para DEV.
      3) Se não houver variáveis -> levanta RuntimeError para a GUI abrir a tela de login.
    """
    token = _get_access_token(client)
    if token:
        _postgrest_bind(client, token)
        return

    email = os.getenv("SUPABASE_EMAIL")
    password = os.getenv("SUPABASE_PASSWORD")

    if email and password:
        # Login de desenvolvimento (sem UI), apenas para não travar inserções
        _res = client.auth.sign_in_with_password({"email": email, "password": password})
        token = _get_access_token(client)
        if not token:
            raise RuntimeError("Falha no login DEV (.env). Verifique SUPABASE_EMAIL/SUPABASE_PASSWORD.")
        _postgrest_bind(client, token)
        log.info("Login DEV realizado e token aplicado ao PostgREST.")
        return

    # Sem sessão e sem credenciais de DEV -> peça à GUI para abrir tela de login
    raise RuntimeError("Sem sessão Supabase. Abra a tela de login e autentique-se.")

# ----------------------------------------------------------------------------------------
