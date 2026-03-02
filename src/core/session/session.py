# -*- coding: utf-8 -*-
"""Sessao do usuario logado + tokens do Supabase, com org_id carregado da tabela memberships."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from src.infra.db_schemas import MEMBERSHIPS_SELECT_ORG_ROLE
from src.infra.supabase_client import exec_postgrest, supabase


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


# -------------------- Estado + lock -------------------- #
_LOCK: threading.RLock = threading.RLock()
_CURRENT_USER: CurrentUser | None = None
_TOKENS: Tokens = Tokens()


# -------------------- API publica -------------------- #
def refresh_current_user_from_supabase() -> None:
    """
    Le o usuario atual do Supabase Auth e resolve o org_id na tabela public.memberships.
    Prioriza a linha com role='owner'; se nao houver, usa a primeira.

    O IO (rede) ocorre FORA do lock; apenas a troca atomica de _CURRENT_USER
    e feita dentro do lock, evitando bloquear outras threads durante chamadas remotas.
    """
    global _CURRENT_USER

    # --- IO fora do lock ---------------------------------------------------
    sess = supabase.auth.get_session()
    user = getattr(sess, "user", None)
    if not user:
        with _LOCK:
            _CURRENT_USER = None
        return

    uid = getattr(user, "id", None)
    email = getattr(user, "email", None)

    resp = exec_postgrest(supabase.table("memberships").select(MEMBERSHIPS_SELECT_ORG_ROLE).eq("user_id", uid))
    rows: list[MembershipRow] = resp.data or []

    org_id: str | None = None
    if rows:
        owners: list[MembershipRow] = [r for r in rows if (r.get("role") or "").lower() == "owner"]
        chosen = owners[0] if owners else (rows[0] if rows else None)
        if chosen:
            org_id = chosen.get("org_id")

    new_user = CurrentUser(uid=uid, email=email, org_id=org_id)  # pyright: ignore[reportArgumentType]

    # --- set atomico sob lock ---------------------------------------------
    with _LOCK:
        _CURRENT_USER = new_user


def get_current_user() -> CurrentUser | None:
    """Retorna uma COPIA do usuario atual (uid, email, org_id) ou None."""
    with _LOCK:
        cu = _CURRENT_USER
        if cu is None:
            return None
        return CurrentUser(uid=cu.uid, email=cu.email, org_id=cu.org_id)


def clear_current_user() -> None:
    """Limpa a sessao do usuario atual."""
    global _CURRENT_USER
    with _LOCK:
        _CURRENT_USER = None


# -------------------- Tokens -------------------- #
def set_tokens(access: str | None, refresh: str | None) -> None:
    global _TOKENS
    with _LOCK:
        _TOKENS = Tokens(access_token=access, refresh_token=refresh)


def get_tokens() -> TokensTuple:
    with _LOCK:
        return _TOKENS.access_token, _TOKENS.refresh_token


# -------------------- Compat/legado -------------------- #
def set_current_user(username: str) -> None:
    """Compat: define apenas o e-mail; org_id ficara None ate rodar refresh_current_user_from_supabase()."""
    global _CURRENT_USER
    with _LOCK:
        _CURRENT_USER = CurrentUser(uid="", email=username or "", org_id=None)


def get_session() -> Session:
    """
    Compat: fornece um objeto Session contendo user + tokens,
    para chamadas antigas que esperavam essa estrutura.
    Captura snapshot consistente de user + tokens sob um unico lock.
    """
    with _LOCK:
        cu = _CURRENT_USER
        at = _TOKENS.access_token
        rt = _TOKENS.refresh_token

    return Session(
        uid=getattr(cu, "uid", "") if cu else "",
        email=getattr(cu, "email", "") if cu else "",
        org_id=getattr(cu, "org_id", None) if cu else None,
        access_token=at,
        refresh_token=rt,
    )
