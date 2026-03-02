from __future__ import annotations

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn

import logging
import os
import tkinter as tk
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
        except tk.TclError:
            # FIX: Fallback deve usar rc.png (PhotoImage não funciona com .ico no Windows)
            try:
                png_path = resource_path("rc.png")
                if os.path.exists(png_path):
                    img = tk.PhotoImage(file=png_path)
                    window.iconphoto(True, img)
            except tk.TclError as inner_exc:
                logger.debug("Falha ao aplicar iconphoto: %s", inner_exc)
    except (OSError, tk.TclError) as exc:
        logger.debug("Falha ao configurar icone do dialogo: %s", exc)


def show_info(parent: tk.Widget, title: str, message: str) -> None:
    """Mostra um diálogo de informação com ícone do app."""
    top = ctk.CTkToplevel(parent)
    top.withdraw()
    top.title(title)
    top.resizable(False, False)
    top.transient(parent)
    _apply_icon(top)

    content = ctk.CTkFrame(top)  # TODO: padding=15 -> usar padx/pady no pack/grid
    content.pack(fill="both", expand=True)

    icon_label = ctk.CTkLabel(content, text="\u2139", font=("", 26, "bold"))
    icon_label.grid(row=0, column=0, padx=(5, 10), pady=5, sticky="n")

    message_label = ctk.CTkLabel(
        content,
        text=message,
        wraplength=360,
        anchor="w",
        justify="left",
    )
    message_label.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="w")
    content.columnconfigure(1, weight=1)

    frm = ctk.CTkFrame(content)
    frm.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="e")

    def _close(*_: Any) -> None:
        try:
            top.destroy()
        except tk.TclError as exc:
            logger.debug("Falha ao fechar dialogo de info: %s", exc)

    btn = make_btn(frm, text="OK", command=_close)
    btn.pack(side="right")

    top.bind("<Return>", _close)
    top.bind("<Escape>", _close)
    try:
        top.update_idletasks()
        show_centered(top)
        top.grab_set()
        top.focus_force()
    except tk.TclError as exc:
        logger.debug("Falha ao exibir dialogo de info: %s", exc)
    top.wait_window()


def ask_ok_cancel(parent: tk.Widget, title: str, message: str) -> bool:
    """Mostra um diálogo OK/Cancelar com ícone do app e retorna True/False."""
    result = {"ok": False}

    top = ctk.CTkToplevel(parent)
    top.withdraw()
    top.title(title)
    top.resizable(False, False)
    top.transient(parent)
    _apply_icon(top)

    content = ctk.CTkFrame(top)  # TODO: padding=15 -> usar padx/pady no pack/grid
    content.pack(fill="both", expand=True)

    icon_label = ctk.CTkLabel(
        content,
        text="?",
        text_color="#000000",  # FIX: CTkLabel usa text_color, não foreground
        font=("", 26, "bold"),
        anchor="n",
        justify="center",
    )
    icon_label.grid(row=0, column=0, padx=(5, 12), pady=5, sticky="n")

    message_label = ctk.CTkLabel(
        content,
        text=message,
        wraplength=360,
        anchor="w",
        justify="left",
    )
    message_label.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="w")
    content.columnconfigure(1, weight=1)

    frm = ctk.CTkFrame(content)
    frm.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="e")

    def _ok(*_: Any) -> None:
        result["ok"] = True
        try:
            top.destroy()
        except tk.TclError as exc:
            logger.debug("Falha ao fechar dialogo OK/Cancelar: %s", exc)

    def _cancel(*_: Any) -> None:
        result["ok"] = False
        try:
            top.destroy()
        except tk.TclError as exc:
            logger.debug("Falha ao fechar dialogo OK/Cancelar: %s", exc)

    btns = ctk.CTkFrame(frm)
    btns.pack(fill="x")

    make_btn(btns, text=OK_LABEL, command=_ok).pack(side="right", padx=(8, 0))
    make_btn(btns, text=CANCEL_LABEL, command=_cancel).pack(side="right", padx=(0, 5))

    top.bind("<Return>", _ok)
    top.bind("<Escape>", _cancel)
    try:
        top.update_idletasks()
        show_centered(top)
        top.grab_set()
        top.focus_force()
    except tk.TclError as exc:
        logger.debug("Falha ao exibir dialogo OK/Cancelar: %s", exc)
    top.wait_window()
    return bool(result["ok"])


OK_LABEL = "Sim"
CANCEL_LABEL = "Não"
