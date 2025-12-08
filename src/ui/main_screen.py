"""DEPRECATED: Este módulo será removido em versão futura.

Use: from src.modules.clientes.views.main_screen import MainScreenFrame
"""

from __future__ import annotations

import warnings

warnings.warn(
    "src.ui.main_screen está deprecated. Use src.modules.clientes.views.main_screen",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.clientes.views import (  # noqa: E402
    DEFAULT_ORDER_LABEL,
    MainScreenFrame,
    ORDER_CHOICES,
)

__all__ = ["MainScreenFrame", "DEFAULT_ORDER_LABEL", "ORDER_CHOICES"]
