# -*- coding: utf-8 -*-
"""Sessao do usuario logado + tokens do Supabase, com org_id carregado da tabela memberships."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from infra.supabase_client import exec_postgrest, supabase


# -------------------- Modelos -------------------- #
@dataclass
class CurrentUser:
    uid: str | None
    email: str | None
    org_id: str | None = None


@dataclass
class Tokens:
    access_token: str | None = None
    refresh_token: str | None = None


MembershipRow = dict[str, Any]
TokensTuple = tuple[str | None, str | None]


# Compatibilidade com codigo legado que importava `Session`
@dataclass
class Session:
    uid: str = ""
    email: str = ""
    org_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None


# -------------------- Estado -------------------- #
_CURRENT_USER: CurrentUser | None = None
_TOKENS: Tokens = Tokens()


# -------------------- API publica -------------------- #
def refresh_current_user_from_supabase() -> None:
    """
    Le o usuario atual do Supabase Auth e resolve o org_id na tabela public.memberships.
    Prioriza a linha com role='owner'; se nao houver, usa a primeira.
    """
    global _CURRENT_USER

    sess = supabase.auth.get_session()
    user = getattr(sess, "user", None)
    if not user:
        _CURRENT_USER = None
        return

    uid = getattr(user, "id", None)
    email = getattr(user, "email", None)

    # Busca memberships do usuario
    resp = exec_postgrest(supabase.table("memberships").select("org_id, role").eq("user_id", uid))
    rows: list[MembershipRow] = resp.data or []

    org_id: str | None = None
    if rows:
        owners: list[MembershipRow] = [r for r in rows if (r.get("role") or "").lower() == "owner"]
        chosen = owners[0] if owners else rows[0]
        org_id = chosen.get("org_id")

    _CURRENT_USER = CurrentUser(uid=uid, email=email, org_id=org_id)  # pyright: ignore[reportArgumentType]


def get_current_user() -> CurrentUser | None:
    """Retorna o usuario atual (uid, email, org_id) ou None."""
    return _CURRENT_USER


def clear_current_user() -> None:
    """Limpa a sessao do usuario atual."""
    global _CURRENT_USER
    _CURRENT_USER = None


# -------------------- Tokens -------------------- #
def set_tokens(access: str | None, refresh: str | None) -> None:
    _TOKENS.access_token = access
    _TOKENS.refresh_token = refresh


def get_tokens() -> TokensTuple:
    return _TOKENS.access_token, _TOKENS.refresh_token


# -------------------- Compat/legado -------------------- #
def set_current_user(username: str) -> None:
    """Compat: define apenas o e-mail; org_id ficara None ate rodar refresh_current_user_from_supabase()."""
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
