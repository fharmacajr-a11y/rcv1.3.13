from __future__ import annotations

import importlib
from typing import Any

# Importar HubScreen antes de listá-lo em __all__
from .hub_screen import HubScreen

__all__ = ["HubScreen"]


def __getattr__(name: str) -> Any:
    if name == "HubScreen":
        module = importlib.import_module("src.modules.hub.views.hub_screen")
        hub_screen_cls = getattr(module, "HubScreen")
        globals()["HubScreen"] = hub_screen_cls
        return hub_screen_cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
