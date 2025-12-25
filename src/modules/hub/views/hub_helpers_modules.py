# -*- coding: utf-8 -*-
"""DEPRECATED: Use src.modules.hub.helpers.modules (mantido para compatibilidade).

ORG-003: Helpers de módulos foram consolidados em hub/helpers/modules.py.
Este arquivo permanece como shim de compatibilidade para não quebrar imports externos.

Para novos códigos, importe diretamente de:
    from src.modules.hub.helpers.modules import ...
"""

from __future__ import annotations

# Re-exports do novo local (ORG-003)
from ..helpers.modules import (
    ModuleButton,
    build_module_buttons,
    calculate_module_button_style,
)

__all__ = [
    "ModuleButton",
    "build_module_buttons",
    "calculate_module_button_style",
]
