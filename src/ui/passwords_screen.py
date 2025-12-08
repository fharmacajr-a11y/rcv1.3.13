"""DEPRECATED: Este módulo será removido em versão futura.

Use: from src.modules.passwords.views.passwords_screen import PasswordsScreen, PasswordDialog
"""

import warnings

warnings.warn(
    "src.ui.passwords_screen está deprecated. Use src.modules.passwords.views.passwords_screen",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.passwords.views.passwords_screen import PasswordDialog, PasswordsScreen  # noqa: E402

__all__ = ["PasswordDialog", "PasswordsScreen"]
