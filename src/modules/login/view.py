"""View principal do módulo de Login/Autenticação.

Este módulo é o ENTRYPOINT ÚNICO para UI de login no RC Gestor.
Qualquer código que precise abrir a tela de login deve importar daqui.

IMPLEMENTAÇÃO ATUAL:
  - LoginDialog: aponta para src.ui.login_dialog.LoginDialog (login moderno com Supabase)
  - show_splash: splash screen inicial da aplicação

ARQUIVOS LEGACY (apenas compatibilidade):
  - src.ui.login.login.LoginDialog: wrapper deprecated, não usar em código novo

EXEMPLO DE USO:
  from src.modules.login.view import LoginDialog, show_splash

  # Mostrar splash
  show_splash()

  # Abrir login
  dialog = LoginDialog(parent)
  dialog.wait_window()
  if dialog.login_success:
      # Login OK
"""

from __future__ import annotations

from src.ui.login_dialog import LoginDialog
from src.ui.splash import show_splash

__all__ = [
    "LoginDialog",
    "show_splash",
]
