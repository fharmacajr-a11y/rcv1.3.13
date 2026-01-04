"""
core.services package

Esse __init__.py existe para garantir que `src.core.services` seja um pacote
"normal", permitindo que o pytest monkeypatch resolva caminhos do tipo:
`src.core.services.clientes_service.update_cliente`.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.services import clientes_service as clientes_service
    from src.core.services import lixeira_service as lixeira_service
    from src.core.services import notes_service as notes_service
    from src.core.services import path_resolver as path_resolver
    from src.core.services import profiles_service as profiles_service

__all__ = ["clientes_service", "lixeira_service", "notes_service", "path_resolver", "profiles_service"]


def __getattr__(name: str):
    """Lazy import de submodules para evitar circular imports."""
    if name in __all__:
        return importlib.import_module(f"src.core.services.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
