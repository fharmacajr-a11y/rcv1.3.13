# package
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.search import search as search

from .search import search_clientes

__all__ = ["search_clientes", "search"]


def __getattr__(name: str):
    """Lazy import de submodules para evitar circular imports."""
    if name == "search":
        return importlib.import_module("src.core.search.search")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
