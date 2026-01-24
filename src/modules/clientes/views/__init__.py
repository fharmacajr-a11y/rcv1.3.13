"""Views compartilhadas do módulo Clientes (apenas helpers reutilizáveis).

A UI principal está em src.modules.clientes_v2.
"""

from __future__ import annotations

# Re-exportar apenas constantes necessárias
from .main_screen_helpers import DEFAULT_ORDER_LABEL, ORDER_CHOICES

__all__ = [
    "DEFAULT_ORDER_LABEL",
    "ORDER_CHOICES",
]
