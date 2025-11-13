# src/ui/window_policy.py
from __future__ import annotations
import ctypes
import platform
import tkinter as tk
import logging
from typing import cast

log = logging.getLogger(__name__)


def _workarea_win32() -> tuple[int, int, int, int] | None:
    """Retorna (x, y, w, h) da área útil (sem taskbar) no Windows."""
    SPI_GETWORKAREA = 48  # 0x0030

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    rect = RECT()
    ok = ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    if not ok:
        return None
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def get_workarea(root: tk.Misc) -> tuple[int, int, int, int]:
    """Área útil do monitor atual: (x,y,w,h). No Windows exclui taskbar."""
    if platform.system() == "Windows":
        wa = _workarea_win32()
        if wa:
            return wa
    # Fallback: área total do Tk (pode incluir barra em Linux/macOS)
    root.update_idletasks()
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def fit_geometry_for_device(root: tk.Misc) -> str:
    """
    Calcula geometria amigável para notebooks e desktops:
    - usa % da área útil (evita fullscreen/maximize)
    - aplica mínimos seguros
    """
    x, y, W, H = get_workarea(root)
    # perfis automáticos por resolução
    notebook_like = (W <= 1440) or (H <= 900)

    # percentuais por perfil (afinados para 1366x768, 1600x900, 1920x1080)
    if notebook_like:
        w = int(W * 0.96)
        h = int(H * 0.94)
        min_w, min_h = 1100, 650
    else:
        w = int(W * 0.92)
        h = int(H * 0.90)
        min_w, min_h = 1200, 720

    w = max(min_w, min(w, W))
    h = max(min_h, min(h, H))

    # centraliza na workarea
    gx = x + (W - w) // 2
    gy = y + (H - h) // 2
    return f"{w}x{h}+{gx}+{gy}"


def apply_fit_policy(win: tk.Misc) -> None:
    """Aplica a política Fit-to-WorkArea e garante foco/elevação."""
    geo = fit_geometry_for_device(win)
    # Define geometria antes do primeiro draw para evitar flicker
    # Cast para tk.Tk para acessar métodos de window manager
    window = cast(tk.Tk, win)
    window.geometry(geo)
    try:
        window.minsize(900, 580)  # mínimos gerais defensivos
    except Exception as e:
        log.debug("Failed to set minsize: %s", e)
    # traz para frente e foca sem topmost permanente
    try:
        window.lift()
        window.focus_force()
        window.wm_attributes("-topmost", True)
        window.after(10, lambda: window.wm_attributes("-topmost", False))
    except Exception as e:
        log.debug("Failed to set window focus/topmost: %s", e)
