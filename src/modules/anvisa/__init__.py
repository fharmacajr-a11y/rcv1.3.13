"""Módulo ANVISA - Em desenvolvimento.

Funcionalidades relacionadas à ANVISA serão implementadas aqui.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.anvisa.views.anvisa_screen import AnvisaScreen as AnvisaScreen

__all__ = ["AnvisaScreen"]


def __getattr__(name: str):
    """Lazy import usando PEP 562."""
    if name == "AnvisaScreen":
        from src.modules.anvisa.views.anvisa_screen import AnvisaScreen

        return AnvisaScreen
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Lista de atributos exportados."""
    return sorted(__all__)
