"""Módulo Lixeira - view e serviços."""

from __future__ import annotations

from .view import LixeiraFrame, abrir_lixeira, refresh_if_open
from . import service

__all__ = ["LixeiraFrame", "abrir_lixeira", "refresh_if_open", "service"]
