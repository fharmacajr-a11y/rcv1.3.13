# -*- coding: utf-8 -*-
"""Stub de compatibilidade: pick_mode.PickModeController.

O módulo pick_mode foi removido. Este stub mantém PickModeController
com _format_cnpj_for_pick acessível para testes legados.
"""

from __future__ import annotations

from src.utils.formatters import format_cnpj


class PickModeController:
    """Stub de compatibilidade para PickModeController."""

    @staticmethod
    def _format_cnpj_for_pick(value: str | None) -> str | None:
        """Delega para implementação canônica em src.utils.formatters."""
        return format_cnpj(value)


__all__ = ["PickModeController"]
