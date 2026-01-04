from __future__ import annotations

import logging

from supabase import Client

log = logging.getLogger(__name__)


def bind_postgrest_auth_if_any(client: Client) -> None:
    """
    Aplica o access_token atual no PostgREST do mesmo client.

    Args:
        client: Cliente Supabase para aplicar autenticação no PostgREST

    Note:
        - Se não houver token, retorna silenciosamente (leituras podem degradar)
        - Se falhar ao aplicar, loga WARNING mas não estoura exceção (graceful degradation)
        - O token é obtido via _get_access_token do módulo data.auth_bootstrap
    """
    from src.data.auth_bootstrap import _get_access_token

    token: str | None = _get_access_token(client)
    if not token:
        log.debug("bind_postgrest_auth_if_any: sem token para aplicar")
        return

    try:
        client.postgrest.auth(token)
        log.info("PostgREST: token aplicado (sessão presente).")
    except Exception as e:
        log.warning("PostgREST auth falhou: %s", e)
        # Não estoura exceção - leituras podem degradar graciosamente
