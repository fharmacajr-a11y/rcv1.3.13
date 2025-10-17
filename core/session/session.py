"""Sessão simples para armazenar o usuário logado e tokens Supabase."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Session:
    current_user: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


_session = Session()


def set_current_user(username: str) -> None:
    _session.current_user = username


def get_current_user() -> Optional[str]:
    return _session.current_user


def set_tokens(access: Optional[str], refresh: Optional[str]) -> None:
    _session.access_token = access
    _session.refresh_token = refresh


def get_tokens() -> tuple[Optional[str], Optional[str]]:
    return _session.access_token, _session.refresh_token
