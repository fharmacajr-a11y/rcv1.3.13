# core/__init__.py — leve, com import preguiçoso do classifier
from __future__ import annotations

__all__ = ["classify_document"]

def classify_document(*args, **kwargs):
    """
    Proxy preguiçoso para evitar carregar o pipeline pesado de
    classificação durante o startup (antes da GUI subir).
    """
    from .classify_document import classify_document as _impl
    return _impl(*args, **kwargs)
