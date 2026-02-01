# -*- coding: utf-8 -*-
"""SHIM: Compatibilidade retroativa para export.py.

Este arquivo mantém compatibilidade com código que importa de:
    from src.modules.clientes.core.export import ...

DEPRECADO: Use src.modules.clientes.core.export no futuro.
"""

from __future__ import annotations

import warnings

# Emitir warning UMA VEZ por sessão
warnings.warn(
    "src.modules.clientes.export está deprecado. " "Use src.modules.clientes.core.export no lugar.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exportar tudo do módulo core
from .core.export import *  # noqa: F401, F403

__all__ = [
    "CSV_COLUMNS",
    "CSV_HEADERS",
    "export_clients_to_csv",
    "export_clients_to_xlsx",
]
