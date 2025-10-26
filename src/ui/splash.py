# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
import ttkbootstrap as tb


def _center_coords(screen_w: int, screen_h: int, w: int, h: int) -> tuple[int, int]:
    x = max((screen_w - w) // 2, 0)
    y = max((screen_h - h) // 2, 0)
    return x, y


def show_splash(root: tk.Misc, min_ms: int = 1200) -> tb.Toplevel:
    # Criar invisível para evitar "piscada" no 0,0
    splash = tb.Toplevel(root)
    splash.withdraw()
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)

    # UI básica
    frame = tb.Frame(splash, padding=16)
    frame.pack(fill="both", expand=True)
    lbl = tb.Label(frame, text="Carregando…")
    lbl.pack(pady=(0, 8))
    bar = tb.Progressbar(frame, mode="indeterminate", length=240)
    bar.pack(fill="x")
    bar.start(14)

    # Medir e centralizar antes de exibir
    splash.update_idletasks()
    try:
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    except Exception:
        sw, sh = 1366, 768

    # Tamanho fixo e confortável
    w, h = 300, 110
    x, y = _center_coords(sw, sh, w, h)
    splash.geometry(f"{w}x{h}+{x}+{y}")

    # Mostrar já centralizado (sem flash)
    splash.deiconify()
    splash.lift()
    splash.update()

    def _close():
        if splash.winfo_exists():
            try:
                splash.attributes("-topmost", False)
            except Exception:
                pass
            splash.destroy()

    splash.after(int(min_ms), _close)
    return splash
