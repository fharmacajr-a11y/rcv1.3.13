"""Helper para configurar a titlebar dark/light no Windows."""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def set_immersive_dark_mode(window: tk.Misc, enabled: bool) -> None:
    """
    Aplica titlebar dark/light no Windows usando DwmSetWindowAttribute.

    Args:
        window: Janela tk para aplicar o efeito
        enabled: True para modo escuro, False para modo claro

    Note:
        Esta função é segura para chamar em qualquer plataforma - não faz nada
        se não for Windows. Não levanta exceções se falhar.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        import ctypes.wintypes

        hwnd = window.winfo_id()
        value = ctypes.c_int(1 if enabled else 0)

        # Tentar atributos 20 (DWMWA_USE_IMMERSIVE_DARK_MODE) e 19 (fallback)
        for attr in (20, 19):
            try:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attr,
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao aplicar atributo DWM %d: %s", attr, exc)
                logger.debug("Falha ao aplicar atributo DWM %d: %s", attr, exc)
                continue
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao configurar titlebar dark/light: %s", exc, exc_info=True)


__all__ = ["set_immersive_dark_mode"]
