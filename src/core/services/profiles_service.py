# core/services/profiles_service.py
"""Serviço para consultar perfis de usuários (display_name, etc.)."""

from __future__ import annotations

import logging
from typing import Any

from src.infra.supabase_client import exec_postgrest, get_supabase

log = logging.getLogger(__name__)

_TABLE = "profiles"
_WARNED_MISSING_COL = False

# Aliases de prefixo -> prefixo correto
EMAIL_PREFIX_ALIASES: dict[str, str] = {
    "pharmaca2013": "fharmaca2013",  # corrigir sem "f" → com "f"
}


def _is_missing_column_error(err: Exception) -> bool:
    """Verifica se o erro é devido à coluna display_name ausente."""
    s = str(err).lower()
    return "42703" in s or ("does not exist" in s and "column" in s)


def list_profiles_by_org(org_id: str) -> list[dict[str, Any]]:
    """
    Lista perfis de uma organização com email e display_name.

    Args:
        org_id: UUID da organização

    Returns:
        Lista de dicionários com: email, display_name (se coluna existir)

    Raises:
        Exception: Se houver erro não relacionado à coluna ausente
    """
    global _WARNED_MISSING_COL
    supa = get_supabase()

    try:
        resp = exec_postgrest(supa.table(_TABLE).select("email, display_name").eq("org_id", org_id))
        return resp.data or []
    except Exception as e:
        # Fallback se coluna display_name não existir
        if _is_missing_column_error(e):
            if not _WARNED_MISSING_COL:
                log.warning("profiles_service: coluna display_name ausente; usando fallback.")
                _WARNED_MISSING_COL = True
            try:
                resp = exec_postgrest(supa.table(_TABLE).select("email").eq("org_id", org_id))
                return resp.data or []
            except Exception as fallback_exc:
                log.debug("profiles_service: fallback sem display_name falhou", exc_info=fallback_exc)
        log.warning("Erro ao listar profiles: %s", e)
        return []


def get_display_names_map(org_id: str) -> dict[str, str]:
    """
    Retorna mapa de email -> display_name para uma organização.

    Args:
        org_id: UUID da organização

    Returns:
        Dicionário {email_lowercase: display_name}
        Apenas emails com display_name preenchido
    """
    data: list[dict[str, Any]] = list_profiles_by_org(org_id)
    out: dict[str, str] = {}

    for row in data:
        email = (row.get("email") or "").strip().lower()
        dn = (row.get("display_name") or "").strip()
        if email and dn:
            out[email] = dn

    return out


def get_display_name_by_email(email: str) -> str | None:
    """
    Busca direta em 'profiles' filtrando por email (lowercase).
    Retorna display_name se existir; senão None. Tolerar erros.

    Args:
        email: Email do usuário (será convertido para lowercase)

    Returns:
        display_name se encontrado e preenchido, senão None
    """
    if not email:
        return None
    email_lc: str = email.strip().lower()
    try:
        supa = get_supabase()
        resp = exec_postgrest(supa.table("profiles").select("display_name").eq("email", email_lc).limit(1))
        rows = getattr(resp, "data", None) or []
        if rows:
            dn = (rows[0].get("display_name") or "").strip()
            return dn or None
    except Exception as e:
        log.debug("Erro ao buscar display_name para %s: %s", email_lc, e)
    return None


def get_email_prefix_map(org_id: str) -> dict[str, str]:
    """
    Mapa {prefixo_sem_dominio: email_completo_lower} para todos os perfis da org.
    Inclui aliases de prefixos (ex: pharmaca2013 → fharmaca2013).

    Args:
        org_id: UUID da organização

    Returns:
        Dicionário {prefixo: email_completo}
        Ex.: {"fharmaca2013": "fharmaca2013@hotmail.com", "pharmaca2013": "fharmaca2013@hotmail.com"}
        Retorna {} se houver erro
    """
    out: dict[str, str] = {}
    try:
        supa = get_supabase()
        resp = exec_postgrest(supa.table("profiles").select("email").eq("org_id", org_id))
        rows: list[Any] = getattr(resp, "data", None) or []
        for r in rows:
            em: str = (r.get("email") or "").strip().lower()
            if not em:
                continue
            prefix: str = em.split("@", 1)[0]

            # Aplicar alias no mapa
            alias: str = EMAIL_PREFIX_ALIASES.get(prefix, prefix)
            out.setdefault(alias, em)  # garante entrada com o prefixo correto
            out.setdefault(prefix, em)  # mantém também o original se existir
    except Exception as e:
        log.debug("Erro ao carregar mapa de prefixos para org %s: %s", org_id, e)
    return out


def get_display_names_by_user_ids(
    org_id: str,
    user_ids: list[str],
) -> dict[str, str]:
    """
    Retorna mapa de user_id -> display_name para uma lista de user_ids.

    Args:
        org_id: UUID da organização
        user_ids: Lista de UUIDs de usuários

    Returns:
        Dicionário {user_id: display_name}
        Apenas user_ids com display_name preenchido

    Note:
        A tabela profiles tem um campo 'id' que é o user_id (UUID).
        Se não houver display_name, tenta usar o prefixo do email.
    """
    if not user_ids:
        return {}

    # Remove duplicados e None/vazios
    clean_ids = [uid for uid in user_ids if uid and uid.strip()]
    if not clean_ids:
        return {}

    out: dict[str, str] = {}
    try:
        supa = get_supabase()
        # Buscar profiles por id (user_id) dentro da organização
        query = supa.table(_TABLE).select("id, email, display_name").eq("org_id", org_id).in_("id", clean_ids)
        resp = exec_postgrest(query)
        rows: list[dict[str, Any]] = getattr(resp, "data", None) or []

        for row in rows:
            user_id = row.get("id")
            if not user_id:
                continue

            # Prioridade: display_name > prefixo do email
            display_name = (row.get("display_name") or "").strip()
            if display_name:
                out[user_id] = display_name
            else:
                # Fallback: usar prefixo do email
                email = (row.get("email") or "").strip().lower()
                if email and "@" in email:
                    prefix = email.split("@", 1)[0]
                    # Aplicar alias se existir
                    prefix = EMAIL_PREFIX_ALIASES.get(prefix, prefix)
                    out[user_id] = prefix

    except Exception as e:
        log.debug("Erro ao buscar display_names por user_ids: %s", e)

    return out
