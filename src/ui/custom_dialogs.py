from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import Any

from src.utils.resource_path import resource_path


def _apply_icon(window: tk.Toplevel) -> None:
    """Aplica o ícone rc.ico ao toplevel, se disponível."""
    try:
        icon_path = resource_path("rc.ico")
        if not os.path.exists(icon_path):
            return
        try:
            window.iconbitmap(icon_path)
            return
        except Exception:
            try:
                img = tk.PhotoImage(file=icon_path)
                window.iconphoto(True, img)
            except Exception:
                pass
    except Exception:
        pass


def _center_on_parent(window: tk.Toplevel, parent: tk.Widget) -> None:
    try:
        window.update_idletasks()
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        ww = window.winfo_reqwidth()
        wh = window.winfo_reqheight()
        x = px + (pw - ww) // 2
        y = py + (ph - wh) // 2
        window.geometry(f"{ww}x{wh}+{x}+{y}")
    except Exception:
        pass


def show_info(parent: tk.Widget, title: str, message: str) -> None:
    """Mostra um diálogo de informação com ícone do app."""
    top = tk.Toplevel(parent)
    top.title(title)
    top.resizable(False, False)
    top.transient(parent)
    top.grab_set()
    _apply_icon(top)

    content = ttk.Frame(top, padding=15)
    content.pack(fill="both", expand=True)

    icon_label = tk.Label(content, bitmap="info")
    icon_label.grid(row=0, column=0, padx=(5, 10), pady=5, sticky="n")

    message_label = ttk.Label(
        content,
        text=message,
        wraplength=360,
        anchor="w",
        justify="left",
    )
    message_label.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="w")
    content.columnconfigure(1, weight=1)

    frm = ttk.Frame(content)
    frm.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="e")

    def _close(*_: Any) -> None:
        try:
            top.destroy()
        except Exception:
            pass

    btn = ttk.Button(frm, text="OK", command=_close, bootstyle="primary")
    btn.pack(side="right")

    top.bind("<Return>", _close)
    top.bind("<Escape>", _close)
    _center_on_parent(top, parent)
    try:
        top.focus_force()
    except Exception:
        pass
    top.wait_window()


def ask_ok_cancel(parent: tk.Widget, title: str, message: str) -> bool:
    """Mostra um diálogo OK/Cancelar com ícone do app e retorna True/False."""
    result = {"ok": False}

    top = tk.Toplevel(parent)
    top.title(title)
    top.resizable(False, False)
    top.transient(parent)
    top.grab_set()
    _apply_icon(top)

    content = ttk.Frame(top, padding=15)
    content.pack(fill="both", expand=True)

    icon_label = tk.Label(content, bitmap="question")
    icon_label.grid(row=0, column=0, padx=(5, 10), pady=5, sticky="n")

    message_label = ttk.Label(
        content,
        text=message,
        wraplength=360,
        anchor="w",
        justify="left",
    )
    message_label.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="w")
    content.columnconfigure(1, weight=1)

    frm = ttk.Frame(content)
    frm.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="e")

    def _ok(*_: Any) -> None:
        result["ok"] = True
        try:
            top.destroy()
        except Exception:
            pass

    def _cancel(*_: Any) -> None:
        result["ok"] = False
        try:
            top.destroy()
        except Exception:
            pass

    btns = ttk.Frame(frm)
    btns.pack(fill="x")

    ttk.Button(btns, text="OK", command=_ok, bootstyle="primary").pack(side="right", padx=(8, 0))
    ttk.Button(btns, text="Cancelar", command=_cancel, bootstyle="secondary-outline").pack(side="right", padx=(0, 5))

    top.bind("<Return>", _ok)
    top.bind("<Escape>", _cancel)
    _center_on_parent(top, parent)
    try:
        top.focus_force()
    except Exception:
        pass
    top.wait_window()
    return bool(result["ok"])
