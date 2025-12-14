"""DEPRECATED UI MODULE - Login Antigo (Minimalista)

Este módulo pertence à UI antiga (pré-modules/*).
Mantido apenas como wrapper de compatibilidade.

NOVO CÓDIGO DEVE USAR:
  from src.ui.login_dialog import LoginDialog  # Login moderno com Supabase

ou via módulo:
  from src.modules.login.view import LoginDialog
"""

# DEPRECATED: Este módulo será removido em versão futura.
# Use src.ui.login_dialog.LoginDialog diretamente.

from __future__ import annotations

import logging
import warnings

# MF-11: Import movido para o topo (Ruff E402)
from src.ui.login_dialog import LoginDialog as ModernLoginDialog

# Emite warning ao importar este módulo
warnings.warn(
    "src.ui.login.login está deprecated. Use src.ui.login_dialog.LoginDialog",
    DeprecationWarning,
    stacklevel=2,
)

log = logging.getLogger(__name__)


class LoginDialog(ModernLoginDialog):
    """DEPRECATED: Wrapper de compatibilidade para LoginDialog antigo.

    Use src.ui.login_dialog.LoginDialog diretamente.
    """

    def __init__(self, parent=None):
        warnings.warn(
            "LoginDialog da UI antiga está deprecated. Use src.ui.login_dialog.LoginDialog",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(parent or parent.winfo_toplevel() if parent else None)


__all__ = ["LoginDialog"]
