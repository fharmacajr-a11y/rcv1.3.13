"""View principal do módulo de Login/Autenticação.

Este módulo encapsula a UI legada de login e telas associadas
(`src.ui.login.*`, `src.ui.login_dialog`, `src.ui.splash`) e
reexporta os entrypoints usados pelo restante da aplicação.

Qualquer ajuste visual futuro do fluxo de login deve ser feito
aqui, mantendo a interface estável para o restante do app.
"""

from __future__ import annotations

from src.ui.login import LoginDialog as LegacyLoginDialog
from src.ui.login_dialog import LoginDialog as SupabaseLoginDialog
from src.ui.splash import show_splash

# Alias principal compatível com o diálogo usado atualmente
LoginDialog = SupabaseLoginDialog

__all__ = [
    "LoginDialog",
    "LegacyLoginDialog",
    "SupabaseLoginDialog",
    "show_splash",
]
