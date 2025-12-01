"""Módulo Notas/Hub - view e serviços."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Quebra ciclo: hub.views.hub_screen -> hub.actions -> notas.service -> notas.__init__ -> view -> HubScreen
    from .view import HubFrame

from . import service

__all__ = ["HubFrame", "service"]


def __getattr__(name: str) -> Any:
    """Lazy loader para HubFrame, evitando import circular."""
    if name == "HubFrame":
        from .view import HubFrame as _HubFrame

        globals()["HubFrame"] = _HubFrame
        return _HubFrame
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
