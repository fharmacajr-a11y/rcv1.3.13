# -*- coding: utf-8 -*-
"""SHIM: Compatibilidade retroativa para views/main_screen_helpers.py.

Este arquivo mantém compatibilidade com código que importa de:
    from src.modules.clientes.core.ui_helpers import ...

DEPRECADO: Use src.modules.clientes.core.ui_helpers no futuro.
"""

from __future__ import annotations

import warnings

# Emitir warning UMA VEZ por sessão
warnings.warn(
    "src.modules.clientes.views.main_screen_helpers está deprecado. Use src.modules.clientes.core.ui_helpers no lugar.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exportar tudo do módulo core
from ..core.ui_helpers import *  # noqa: F401, F403
