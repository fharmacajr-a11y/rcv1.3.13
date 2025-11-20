"""
Shim para manter compatibilidade com o antigo caminho do ClientPicker.
"""

from __future__ import annotations

from src.modules.clientes.forms import ClientPicker  # noqa: F401

__all__ = ["ClientPicker"]
