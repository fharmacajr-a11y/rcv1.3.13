"""Views compartilhadas do módulo Clientes (apenas helpers reutilizáveis).

A UI principal está em src.modules.clientes.ui
"""

from __future__ import annotations

# Re-exportar apenas constantes necessárias
from .main_screen_helpers import DEFAULT_ORDER_LABEL, ORDER_CHOICES

# Shim: permite que @patch resolva o caminho completo do submódulo
from . import client_obligations_window  # noqa: F401

__all__ = [
    "DEFAULT_ORDER_LABEL",
    "ORDER_CHOICES",
    "client_obligations_window",
]
