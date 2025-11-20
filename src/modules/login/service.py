"""Service fino para o módulo de Login/Autenticação.

Este arquivo expõe uma API estável para operações de login,
logout e gerenciamento de sessão, reutilizando os serviços
legados em `src.core.auth` e módulos relacionados.
"""

from __future__ import annotations

from src.core.auth import authenticate_user, create_user, ensure_users_db, validate_credentials
from src.core.auth_controller import AuthController

__all__ = [
    "authenticate_user",
    "create_user",
    "ensure_users_db",
    "validate_credentials",
    "AuthController",
]
