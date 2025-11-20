"""Módulo Fluxo de Caixa - view e serviços."""

from __future__ import annotations

from .view import CashflowFrame, open_cashflow_window
from src.modules.cashflow.views.fluxo_caixa_frame import CashflowFrame as FluxoCaixaFrame
from . import service

__all__ = ["CashflowFrame", "FluxoCaixaFrame", "open_cashflow_window", "service"]
