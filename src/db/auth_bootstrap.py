# -------------------------------- data/auth_bootstrap.py --------------------------------
from __future__ import annotations

import logging
import os
from typing import Any, Optional

log = logging.getLogger(__name__)


def _get_access_token(client: Any) -> Optional[str]:
    """Recupera o access_token da sessão atual do cliente Supabase (ou None)."""
    try:
        session = client.auth.get_session()
        token = getattr(session, "access_token", None)
        return token or None
    except Exception:
        return None


def _postgrest_bind(client: Any, token: Optional[str]) -> None:
    """Aplica o token da sessão atual no cliente PostgREST, ignorando falhas."""
    if not token:
        return
    try:
        client.postgrest.auth(token)
    except Exception as e:
        log.warning("postgrest.auth falhou: %s", e)


def ensure_signed_in(client: Any) -> None:
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
        _ = client.auth.sign_in_with_password({"email": email, "password": password})
        token = _get_access_token(client)
        if not token:
            raise RuntimeError("Falha no login DEV (.env). Verifique SUPABASE_EMAIL/SUPABASE_PASSWORD.")
        _postgrest_bind(client, token)
        log.info("Login DEV realizado e token aplicado ao PostgREST.")
        return

    # Sem sessão e sem credenciais de DEV -> peça à GUI para abrir tela de login
    raise RuntimeError("Sem sessão Supabase. Abra a tela de login e autentique-se.")


# ----------------------------------------------------------------------------------------
