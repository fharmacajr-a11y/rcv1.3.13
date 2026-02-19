# -*- coding: utf-8 -*-
"""Source code root package."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Só para o type checker enxergar os símbolos (evita reportUnsupportedDunderAll)
    # Em runtime, NÃO importa, quebrando o ciclo com adapters.storage.api
    from . import app_core, app_gui, app_status, app_utils

__all__ = ["app_core", "app_gui", "app_status", "app_utils"]


def __getattr__(name: str) -> Any:
    """
    Lazy loader para submódulos exportados em __all__.

    Evita imports pesados em tempo de import do pacote `src`,
    mas ainda permite `from src import app_core` funcionar.
    """
    if name in __all__:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
