# -*- coding: utf-8 -*-
"""Sessão do usuário logado + tokens do Supabase, com org_id carregado da tabela memberships."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from infra.supabase_client import exec_postgrest, supabase


# -------------------- Modelos -------------------- #
@dataclass
class CurrentUser:
    uid: str
    email: str
    org_id: Optional[str] = None


@dataclass
class Tokens:
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


# Compatibilidade com código legado que importava `Session`
@dataclass
class Session:
    uid: str = ""
    email: str = ""
    org_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


# -------------------- Estado -------------------- #
_CURRENT_USER: Optional[CurrentUser] = None
_TOKENS = Tokens()


# -------------------- API pública -------------------- #
def refresh_current_user_from_supabase() -> None:
    """
    Lê o usuário atual do Supabase Auth e resolve o org_id na tabela public.memberships.
    Prioriza a linha com role='owner'; se não houver, usa a primeira.
    """
    global _CURRENT_USER

    sess = supabase.auth.get_session()
    user = getattr(sess, "user", None)
    if not user:
        _CURRENT_USER = None
        return

    uid = getattr(user, "id", None)
    email = getattr(user, "email", None)

    # Busca memberships do usuário
    resp = exec_postgrest(
        supabase.table("memberships").select("org_id, role").eq("user_id", uid)
    )
    rows: List[dict] = resp.data or []

    org_id: Optional[str] = None
    if rows:
        owners = [r for r in rows if (r.get("role") or "").lower() == "owner"]
        chosen = owners[0] if owners else rows[0]
        org_id = chosen.get("org_id")

    _CURRENT_USER = CurrentUser(uid=uid, email=email, org_id=org_id)


def get_current_user() -> Optional[CurrentUser]:
    """Retorna o usuário atual (uid, email, org_id) ou None."""
    return _CURRENT_USER


def clear_current_user() -> None:
    """Limpa a sessão do usuário atual."""
    global _CURRENT_USER
    _CURRENT_USER = None


# -------------------- Tokens -------------------- #
def set_tokens(access: Optional[str], refresh: Optional[str]) -> None:
    _TOKENS.access_token = access
    _TOKENS.refresh_token = refresh


def get_tokens() -> tuple[Optional[str], Optional[str]]:
    return _TOKENS.access_token, _TOKENS.refresh_token


# -------------------- Compat/legado -------------------- #
def set_current_user(username: str) -> None:
    """Compat: define apenas o e-mail; org_id ficará None até rodar refresh_current_user_from_supabase()."""
    global _CURRENT_USER
    _CURRENT_USER = CurrentUser(uid="", email=username or "", org_id=None)


def get_session() -> Session:
    """
    Compat: fornece um objeto Session contendo user + tokens,
    para chamadas antigas que esperavam essa estrutura.
    """
    cu = get_current_user()
    at, rt = get_tokens()
    return Session(
        uid=getattr(cu, "uid", "") if cu else "",
        email=getattr(cu, "email", "") if cu else "",
        org_id=getattr(cu, "org_id", None) if cu else None,
        access_token=at,
        refresh_token=rt,
    )
