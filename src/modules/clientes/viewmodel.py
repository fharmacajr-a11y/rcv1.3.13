"""DEPRECATED: Shim de compatibilidade.

Este arquivo foi movido para src.modules.clientes.core.viewmodel.

Imports devem ser atualizados para:
    from src.modules.clientes.core.viewmodel import ClienteRow, ClientesViewModel

Este shim será removido após migração completa de todos os importadores.
"""

from __future__ import annotations

import warnings

# Emitir warning UMA vez por processo
if not globals().get("_VIEWMODEL_DEPREC_WARNED"):
    warnings.warn(
        "Importar de 'src.modules.clientes.viewmodel' está DEPRECATED. "
        "Use 'src.modules.clientes.core.viewmodel' em vez disso.",
        DeprecationWarning,
        stacklevel=2,
    )
    _VIEWMODEL_DEPREC_WARNED = True

# Re-export de todos os símbolos públicos do core
from .core.viewmodel import (
    ClienteRow,
    ClientesViewModel,
    ClientesViewModelError,
)

__all__ = [
    "ClienteRow",
    "ClientesViewModel",
    "ClientesViewModelError",
]

__all__ = [
    "ClienteRow",
    "ClientesViewModel",
    "ClientesViewModelError",
]
