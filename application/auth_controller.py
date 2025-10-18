# application/auth_controller.py
from __future__ import annotations
from typing import Optional, Callable
import contextlib


class AuthController:
    def __init__(
        self, on_user_change: Optional[Callable[[Optional[str]], None]] = None
    ) -> None:
        self._user: Optional[str] = None
        self._on_user_change = on_user_change

    def current_user(self) -> Optional[str]:
        return self._user

    def set_current_user(self, username: Optional[str]) -> None:
        self._user = username or None
        # integração best-effort com sessão, se existir
        with contextlib.suppress(Exception):
            from core.session import set_user  # ajuste se o nome real for diferente

            set_user(self._user)
        if callable(self._on_user_change):
            with contextlib.suppress(Exception):
                self._on_user_change(self._user)

    def clear(self) -> None:
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
