"""Shim para compatibilidade da MainScreen antiga.

Mantem import `src.ui.main_screen.MainScreenFrame` funcionando enquanto a
implementacao real vive em `src.modules.clientes.views.main_screen`.
"""

from __future__ import annotations

from src.modules.clientes.views import (
    DEFAULT_ORDER_LABEL,
    MainScreenFrame,
    ORDER_CHOICES,
)

__all__ = ["MainScreenFrame", "DEFAULT_ORDER_LABEL", "ORDER_CHOICES"]
