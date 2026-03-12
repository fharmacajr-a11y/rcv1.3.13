# utils/helpers/hidpi.py
"""Configuracao de suporte HiDPI para monitores de alta resolucao.

⚠️ MIGRAÇÃO COMPLETA: ttkbootstrap foi REMOVIDO (18/01/2026).
Este módulo agora usa apenas configurações nativas do Tkinter.
"""

from __future__ import annotations

import logging
import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk


log = logging.getLogger(__name__)


def configure_hidpi_support(root: "tk.Tk | None" = None, scaling: float | None = None) -> None:
    """Configura suporte HiDPI de forma best-effort para Windows e Linux.

    - Windows: usa ctypes para configurar DPI awareness antes de criar Tk
    - Linux: aplica scaling calculado (ou informado) após o Tk existir
    - macOS: suporte nativo, mantém no-op.
    """
    system = platform.system()

    if system == "Windows":
        # Windows: configurar DPI awareness via ctypes ANTES de criar Tk
        if root is None:
            try:
                import ctypes

                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            except Exception as exc:
                log.debug("HiDPI ja configurado ou indisponivel (Windows)", exc_info=exc)
        # Se root foi passado no Windows, ignora (ja tarde demais)

    # macOS (e Linux): suporte nativo ou não requer configuração

    # macOS tem suporte nativo HiDPI, nao requer configuracao


__all__ = ["configure_hidpi_support"]
