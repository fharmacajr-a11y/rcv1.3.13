"""Shim de compatibilidade para a view de Auditoria.

O conteúdo real vive em src.modules.auditoria.views.main_frame.
"""

from __future__ import annotations

from .views.main_frame import AuditoriaFrame

__all__ = ["AuditoriaFrame"]
