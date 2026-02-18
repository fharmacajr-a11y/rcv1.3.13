# -*- coding: utf-8 -*-
"""SHIM: Compatibilidade retroativa para components/helpers.py.

Este arquivo mantém compatibilidade com código que importa de:
    from src.modules.clientes.core.constants import ...

DEPRECADO: Use src.modules.clientes.core.constants no futuro.
"""

from __future__ import annotations

import warnings

# Emitir warning UMA VEZ por sessão
warnings.warn(
    "src.modules.clientes.components.helpers está deprecado. Use src.modules.clientes.core.constants no lugar.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exportar tudo do módulo core
from ..core.constants import *  # noqa: F401, F403

# Aliases para compatibilidade retroativa
from ..core.constants import STATUS_CHOICES as DEFAULT_STATUS_CHOICES  # noqa: F401
from ..core.constants import STATUS_GROUPS  # noqa: F401
from ..core.constants import STATUS_GROUPS as DEFAULT_STATUS_GROUPS  # noqa: F401

__all__ = [
    "DEFAULT_STATUS_GROUPS",
    "DEFAULT_STATUS_CHOICES",
    "STATUS_CHOICES",
    "STATUS_GROUPS",
    "STATUS_PREFIX_RE",
    "_load_status_choices",
    "_load_status_groups",
    "_build_status_menu",
]
