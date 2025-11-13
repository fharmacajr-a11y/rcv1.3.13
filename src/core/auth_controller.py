# application/auth_controller.py
from __future__ import annotations

import contextlib
from typing import Any, Callable, Dict, Optional


class AuthController:
    def __init__(self, on_user_change: Optional[Callable[[Optional[str]], None]] = None) -> None:
        self._user: Optional[str] = None
        self._user_data: Optional[Dict[str, Any]] = None  # Dados completos do usuário
        self._on_user_change = on_user_change

    def current_user(self) -> Optional[str]:
        return self._user

    def set_current_user(self, username: Optional[str]) -> None:
        self._user = username or None
        # integração best-effort com sessão, se existir
        with contextlib.suppress(Exception):
            from src.core.session import set_user  # ajuste se o nome real for diferente

            set_user(self._user)
        if callable(self._on_user_change):
            with contextlib.suppress(Exception):
                self._on_user_change(self._user)

    def set_user_data(self, user_data: Optional[Dict[str, Any]]) -> None:
        """
        Define dados completos do usuário após login bem-sucedido.

        Args:
            user_data: Dict com email, org_id, etc.
        """
        self._user_data = user_data or None
        if user_data and user_data.get("email"):
            self._user = user_data.get("email")
        elif not user_data:
            self._user = None

        # Notificar mudança
        if callable(self._on_user_change):
            with contextlib.suppress(Exception):
                self._on_user_change(self._user)

    @property
    def is_authenticated(self) -> bool:
        """Retorna True se usuário está autenticado."""
        return self._user_data is not None and self._user is not None

    def get_email(self) -> Optional[str]:
        """Retorna email do usuário autenticado (seguro contra None)."""
        try:
            if self._user_data:
                return self._user_data.get("email")
            return self._user
        except Exception:
            return None

    def get_org_id(self) -> Optional[str]:
        """Retorna org_id do usuário autenticado (seguro contra None)."""
        try:
            if not self._user_data:
                return None

            # Tentar obter diretamente
            org_id = self._user_data.get("org_id")
            if org_id:
                return org_id

            # Tentar obter de claims (JWT)
            claims = self._user_data.get("claims") or {}
            return claims.get("org_id")
        except Exception:
            return None

    def get_user_id(self) -> Optional[str]:
        """Retorna user_id/uid do usuário autenticado (seguro contra None)."""
        try:
            if not self._user_data:
                return None
            return self._user_data.get("id") or self._user_data.get("uid")
        except Exception:
            return None

    def clear(self) -> None:
        self._user_data = None
        self.set_current_user(None)

    # helper para fluxos que exigem login
    def require(self, launcher: Callable[[], Optional[str]]) -> Optional[str]:
        if self._user:
            return self._user
        user = None
        with contextlib.suppress(Exception):
            user = launcher()  # ex.: abrir diálogo e retornar o username
        if user:
            self.set_current_user(user)
        return self._user
