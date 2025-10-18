# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
import ttkbootstrap as tb


def show_splash(root: tk.Misc, min_ms: int = 1200) -> tb.Toplevel:
    splash = tb.Toplevel(root)
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    splash.lift()

    frame = tb.Frame(splash, padding=16)
    frame.pack(fill="both", expand=True)
    tb.Label(frame, text="Carregando…").pack(pady=(0, 8))
    pb = tb.Progressbar(frame, mode="indeterminate", length=220)
    pb.pack()
    splash.after(10, pb.start)

    splash.update_idletasks()
    w, h = 260, 96
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    splash.update()

    def _close():
        if splash.winfo_exists():
            try:
                splash.attributes("-topmost", False)
            except Exception:
                pass
            splash.destroy()

    splash.after(min_ms, _close)
    return splash
