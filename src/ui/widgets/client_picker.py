"""DEPRECATED: Este módulo será removido em versão futura.

Use: from src.modules.clientes.forms import ClientPicker
"""

from __future__ import annotations

import warnings

warnings.warn(
    "src.ui.widgets.client_picker está deprecated. Use src.modules.clientes.forms",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.clientes.forms import ClientPicker  # noqa: E402,F401

__all__ = ["ClientPicker"]
