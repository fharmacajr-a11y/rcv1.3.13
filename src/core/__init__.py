# core/__init__.py — leve, com import preguiçoso do classifier
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core import db_manager as db_manager
    from src.core import search as search
    from src.core import services as services

__all__ = ["classify_document", "services", "search", "db_manager"]


def __getattr__(name: str):
    """Lazy import de subpackages para evitar circular imports."""
    if name in ("services", "search", "db_manager"):
        return importlib.import_module(f"src.core.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def classify_document(*args, **kwargs):
    """
    Proxy preguiçoso para evitar carregar o pipeline pesado de
    classificação durante o startup (antes da GUI subir).
    """
    from .classify_document import classify_document as _impl

    return _impl(*args, **kwargs)
