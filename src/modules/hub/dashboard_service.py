# -*- coding: utf-8 -*-
"""Dashboard service facade (compatibility shim).

DEPRECATED: Este módulo é um facade de compatibilidade.
Use: from src.modules.hub.dashboard.service import ...

Este arquivo existe para manter imports legados funcionando.
A implementação real está em src.modules.hub.dashboard.service.
"""

from __future__ import annotations

import importlib
from typing import Any

# __all__ definido no módulo real (src.modules.hub.dashboard.service)
# Aqui usamos __getattr__ para lazy loading (PEP 562)


def __getattr__(name: str) -> Any:
    """Lazy import from src.modules.hub.dashboard.service."""
    mod = importlib.import_module("src.modules.hub.dashboard.service")
    return getattr(mod, name)


def __dir__() -> list[str]:
    """List available attributes from the real module."""
    mod = importlib.import_module("src.modules.hub.dashboard.service")
    return sorted(set(dir(mod)))
