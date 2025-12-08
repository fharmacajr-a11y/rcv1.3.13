from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import ttk
from typing import Any

from src.ui.window_utils import show_centered
from src.utils.resource_path import resource_path

logger = logging.getLogger(__name__)


def _apply_icon(window: tk.Toplevel) -> None:
    """Aplica o ícone rc.ico ao toplevel, se disponível."""
    try:
        icon_path = resource_path("rc.ico")
        if not os.path.exists(icon_path):
            return
        try:
            window.iconbitmap(icon_path)
            return
        except Exception:  # noqa: BLE001
            try:
                img = tk.PhotoImage(file=icon_path)
                window.iconphoto(True, img)
            except Exception as inner_exc:  # noqa: BLE001
                logger.debug("Falha ao aplicar iconphoto: %s", inner_exc)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao configurar icone do dialogo: %s", exc)


def show_info(parent: tk.Widget, title: str, message: str) -> None:
    """Mostra um diálogo de informação com ícone do app."""
    top = tk.Toplevel(parent)
    top.withdraw()
    top.title(title)
    top.resizable(False, False)
    top.transient(parent)
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
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao fechar dialogo de info: %s", exc)

    btn = ttk.Button(frm, text="OK", command=_close, bootstyle="primary")
    btn.pack(side="right")

    top.bind("<Return>", _close)
    top.bind("<Escape>", _close)
    try:
        top.update_idletasks()
        show_centered(top)
        top.grab_set()
        top.focus_force()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao exibir dialogo de info: %s", exc)
    top.wait_window()


def ask_ok_cancel(parent: tk.Widget, title: str, message: str) -> bool:
    """Mostra um diálogo OK/Cancelar com ícone do app e retorna True/False."""
    result = {"ok": False}

    top = tk.Toplevel(parent)
    top.withdraw()
    top.title(title)
    top.resizable(False, False)
    top.transient(parent)
    _apply_icon(top)

    content = ttk.Frame(top, padding=15)
    content.pack(fill="both", expand=True)

    icon_label = ttk.Label(
        content,
        text="?",
        foreground="#000000",
        font=("", 26, "bold"),
        anchor="n",
        justify="center",
    )
    icon_label.grid(row=0, column=0, padx=(5, 12), pady=5, sticky="n")

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
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao fechar dialogo OK/Cancelar: %s", exc)

    def _cancel(*_: Any) -> None:
        result["ok"] = False
        try:
            top.destroy()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao fechar dialogo OK/Cancelar: %s", exc)

    btns = ttk.Frame(frm)
    btns.pack(fill="x")

    ttk.Button(btns, text=OK_LABEL, command=_ok, bootstyle="primary").pack(side="right", padx=(8, 0))
    ttk.Button(btns, text=CANCEL_LABEL, command=_cancel, bootstyle="secondary-outline").pack(side="right", padx=(0, 5))

    top.bind("<Return>", _ok)
    top.bind("<Escape>", _cancel)
    try:
        top.update_idletasks()
        show_centered(top)
        top.grab_set()
        top.focus_force()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao exibir dialogo OK/Cancelar: %s", exc)
    top.wait_window()
    return bool(result["ok"])


OK_LABEL = "Sim"
CANCEL_LABEL = "Não"
