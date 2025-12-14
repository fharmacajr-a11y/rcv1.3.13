from __future__ import annotations

import importlib
from typing import Any

# Helpers principais do HUB
from src.modules.hub.async_runner import HubAsyncRunner
from src.modules.hub.layout import HubLayoutConfig, apply_hub_layout, apply_hub_notes_right

# Re-exportar HubScreen a partir de views
from .views import HubScreen

__all__ = [
    "HubScreen",
    "HubAsyncRunner",
    "HubLayoutConfig",
    "apply_hub_layout",
    "apply_hub_notes_right",
]


def __getattr__(name: str) -> Any:
    if name == "HubScreen":
        module = importlib.import_module("src.modules.hub.views.hub_screen")
        hub_screen_cls = getattr(module, "HubScreen")
        globals()["HubScreen"] = hub_screen_cls
        return hub_screen_cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
