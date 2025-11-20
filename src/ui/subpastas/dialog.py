"""
Shim para compatibilidade com o dialogo de subpastas legado.
"""

from __future__ import annotations

from src.modules.clientes.forms import open_subpastas_dialog  # noqa: F401

__all__ = ["open_subpastas_dialog"]
