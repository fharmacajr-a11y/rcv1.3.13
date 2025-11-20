"""Módulo Senhas - tela principal e serviços."""

from __future__ import annotations

from .controller import PasswordsController
from .view import PasswordsFrame
from .views.passwords_screen import PasswordsScreen
from . import service

__all__ = ["PasswordsFrame", "PasswordsScreen", "PasswordsController", "service"]
