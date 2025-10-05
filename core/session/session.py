"""Sessão simples para armazenar o usuário logado."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Session:
    current_user: Optional[str] = None

_session = Session()

def set_current_user(username: str) -> None:
    _session.current_user = username

def get_current_user() -> Optional[str]:
    return _session.current_user
