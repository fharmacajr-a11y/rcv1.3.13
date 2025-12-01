"""Utilitários para autenticação e sessão de usuário."""

from __future__ import annotations

import logging
import os

from infra.supabase_client import exec_postgrest, supabase

logger = logging.getLogger(__name__)


def current_user_id() -> str | None:
    """Retorna o ID do usuário atualmente autenticado.

    Tenta obter o ID do usuário da sessão atual do Supabase Auth.
    Suporta diferentes formatos de resposta do cliente Supabase.

    Returns:
        ID do usuário (UUID string) se autenticado, None caso contrário

    Examples:
        >>> uid = current_user_id()
        >>> if uid:
        ...     print(f"User ID: {uid}")
        ... else:
        ...     print("Not authenticated")
    """
    try:
        resp = supabase.auth.get_user()
        user = getattr(resp, "user", None)
        if user and getattr(user, "id", None):
            return user.id
        # Fallback: resposta em formato dict
        if isinstance(resp, dict):
            u = resp.get("user") or (resp.get("data") or {}).get("user") or {}
            return u.get("id") or u.get("uid")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao obter usuario atual no Supabase: %s", exc)
    return None


def resolve_org_id() -> str:
    """Resolve o ID da organização do usuário atual.

    Ordem de resolução:
    1. Busca org_id na tabela `memberships` usando o user_id atual
    2. Fallback para variável de ambiente SUPABASE_DEFAULT_ORG
    3. Levanta RuntimeError se nenhuma opção disponível

    Returns:
        ID da organização (UUID string)

    Raises:
        RuntimeError: Se usuário não autenticado e sem fallback configurado
        RuntimeError: Se não foi possível resolver org_id de nenhuma fonte

    Examples:
        >>> org_id = resolve_org_id()
        >>> print(f"Organization: {org_id}")
    """
    uid = current_user_id()
    fallback = (os.getenv("SUPABASE_DEFAULT_ORG") or "").strip()

    if not uid and not fallback:
        raise RuntimeError("Usuário não autenticado e SUPABASE_DEFAULT_ORG não definido.")

    # Tenta buscar org_id da tabela memberships
    try:
        if uid:
            res = exec_postgrest(supabase.table("memberships").select("org_id").eq("user_id", uid).limit(1))
            data = getattr(res, "data", None) or []
            if data:
                return data[0]["org_id"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao resolver org_id via memberships: %s", exc)

    # Fallback para variável de ambiente
    if fallback:
        return fallback

    raise RuntimeError("Não foi possível resolver a organização do usuário.")
