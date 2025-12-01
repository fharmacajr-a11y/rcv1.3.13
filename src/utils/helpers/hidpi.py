# utils/helpers/hidpi.py
"""Configuracao de suporte HiDPI para monitores de alta resolucao via ttkbootstrap."""

from __future__ import annotations

import logging
import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk


log = logging.getLogger(__name__)


def configure_hidpi_support(root: "tk.Tk | None" = None, scaling: float | None = None) -> None:
    """Configura suporte HiDPI de forma best-effort para Windows e Linux.

    - Windows: chama enable_high_dpi_awareness antes de criar o Tk e ignora erros.
    - Linux: aplica scaling calculado (ou informado) apos o Tk existir; se falhar, apenas registra debug.
    - macOS: suporte nativo, mantem no-op.
    """
    try:
        from ttkbootstrap.utility import enable_high_dpi_awareness
    except ImportError:
        # ttkbootstrap nao disponivel ou versao antiga
        return

    system = platform.system()

    if system == "Windows":
        # Windows: chamar sem parametros ANTES de criar Tk
        if root is None:
            try:
                enable_high_dpi_awareness()
            except Exception as exc:
                log.debug("HiDPI ja configurado ou indisponivel (Windows)", exc_info=exc)
        # Se root foi passado no Windows, ignora (ja tarde demais)

    elif system == "Linux":
        # Linux: chamar DEPOIS de criar Tk, com root e scaling
        if root is not None:
            try:
                # Scaling recomendado: 1.6-2.0 para monitores 4K
                scale_factor = scaling or _detect_linux_scaling(root)
                enable_high_dpi_awareness(root, scale_factor)  # pyright: ignore[reportCallIssue]
            except Exception as exc:
                log.debug("HiDPI nao aplicado no Linux", exc_info=exc)

    # macOS tem suporte nativo HiDPI, nao requer configuracao


def _detect_linux_scaling(root: "tk.Tk") -> float:
    """Calcula fator de escala no Linux baseado em DPI, limitando entre 1.0 e 3.0."""
    try:
        dpi = root.winfo_fpixels("1i")  # pixels por polegada
        scale = dpi / 96.0
        scale = max(1.0, min(3.0, scale))
        return round(scale, 1)
    except Exception:
        # Fallback para 1.0 (sem escala)
        return 1.0


__all__ = ["configure_hidpi_support"]
