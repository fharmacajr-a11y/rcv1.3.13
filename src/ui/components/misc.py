# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import re
import webbrowser
from dataclasses import dataclass
from typing import Callable

import tkinter as tk

import ttkbootstrap as tb
from PIL import Image, ImageOps, ImageTk

STATUS_DOT = "\u25CF"
_ICON_CACHE: dict[tuple[str, int], ImageTk.PhotoImage] = {}

logger = logging.getLogger(__name__)
log = logger

__all__ = [
    "MenuComponents",
    "StatusIndicators",
    "create_menubar",
    "create_status_bar",
    "get_whatsapp_icon",
    "draw_whatsapp_overlays",
]


@dataclass(slots=True)
class MenuComponents:
    menu: tk.Menu
    theme_var: tk.StringVar
    tema_menu: tk.Menu


@dataclass(slots=True)
class StatusIndicators:
    frame: tb.Frame
    count_var: tk.StringVar
    status_dot_var: tk.StringVar
    status_text_var: tk.StringVar
    status_dot: tb.Label
    status_label: tb.Label


def create_menubar(
    root: tk.Misc,
    theme_name: str,
    on_set_theme: Callable[[str], None],
    on_show_changelog: Callable[[], None],
    on_exit: Callable[[], None],
) -> MenuComponents:
    """Create and attach the application menubar."""
    theme_var = tk.StringVar(master=root, value=theme_name or "flatly")
    menubar = tk.Menu(root)
    menu_arquivo = tk.Menu(menubar, tearoff=0)

    def _apply_theme(valor: str) -> None:
        if not valor:
            return
        on_set_theme(valor)

    tema_menu = tk.Menu(menu_arquivo, tearoff=0)
    tema_menu.add_radiobutton(
        label="Tema claro",
        variable=theme_var,
        value="flatly",
        command=lambda: _apply_theme("flatly"),
    )
    tema_menu.add_radiobutton(
        label="Tema escuro",
        variable=theme_var,
        value="darkly",
        command=lambda: _apply_theme("darkly"),
    )
    menu_arquivo.add_cascade(label="Tema", menu=tema_menu)

    menu_ajuda = tk.Menu(menu_arquivo, tearoff=0)
    menu_ajuda.add_command(label="Sobre/Changelog", command=on_show_changelog)
    menu_arquivo.add_cascade(label="Ajuda", menu=menu_ajuda)

    menu_arquivo.add_separator()
    menu_arquivo.add_command(label="Sair", command=on_exit)

    menubar.add_cascade(label="Arquivo", menu=menu_arquivo)
    try:
        root.config(menu=menubar)
    except Exception as exc:
        log.exception("Falha ao anexar menubar", exc_info=exc)

    return MenuComponents(menu=menubar, theme_var=theme_var, tema_menu=tema_menu)


def create_status_bar(
    parent: tk.Misc,
    *,
    count_var: tk.StringVar | None = None,
    status_dot_var: tk.StringVar | None = None,
    status_text_var: tk.StringVar | None = None,
    default_status_text: str = "LOCAL",
) -> StatusIndicators:
    """Create the status bar used on the bottom of the main window."""
    frame = tb.Frame(parent)

    count_var = count_var or tk.StringVar(master=parent, value="0 clientes")
    status_dot_var = status_dot_var or tk.StringVar(master=parent, value=STATUS_DOT)
    status_text_var = status_text_var or tk.StringVar(
        master=parent, value=default_status_text
    )

    tb.Label(frame, textvariable=count_var).pack(side="left")

    right_box = tb.Frame(frame)
    right_box.pack(side="right")

    status_dot = tb.Label(right_box, textvariable=status_dot_var, bootstyle="warning")
    status_dot.configure(font=("", 14))
    status_dot.pack(side="left", padx=(0, 6))

    status_label = tb.Label(
        right_box, textvariable=status_text_var, bootstyle="inverse"
    )
    status_label.pack(side="left")

    return StatusIndicators(
        frame=frame,
        count_var=count_var,
        status_dot_var=status_dot_var,
        status_text_var=status_text_var,
        status_dot=status_dot,
        status_label=status_label,
    )


def get_whatsapp_icon(size: int = 15) -> ImageTk.PhotoImage | None:
    """Retorna PhotoImage do WhatsApp redimensionado com cache."""
    key = ("whatsapp.png", size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    try:
        assets = os.path.join(os.path.dirname(__file__), "..", "assets")
        assets = os.path.normpath(assets)
        base = None
        for cand in (f"whatsapp_{size}.png", "whatsapp.webp", "whatsapp.png"):
            path = os.path.join(assets, cand)
            if os.path.exists(path):
                base = path
                break
        if not base:
            return None
        img = Image.open(base).convert("RGBA")
        if img.size != (size, size):
            img = ImageOps.contain(img, (size, size), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        _ICON_CACHE[key] = photo
        return photo
    except Exception as exc:
        log.debug("Nao foi possivel carregar o ícone do WhatsApp: %s", exc)
        return None


def draw_whatsapp_overlays(tree: tk.Widget, column: str, size: int = 15) -> None:
    """Desenha ícones do WhatsApp sobre a coluna especificada em um Treeview."""
    if not hasattr(tree, "_wa_overlays"):
        tree._wa_overlays = []

    for widget in getattr(tree, "_wa_overlays", []):
        try:
            widget.destroy()
        except Exception:
            pass
    tree._wa_overlays = []

    icon = get_whatsapp_icon(size)
    if not icon:
        return

    try:
        for iid in tree.get_children(""):
            bbox = tree.bbox(iid, column)
            if not bbox:
                continue
            x, y, _w, h = bbox
            numero = tree.set(iid, column)
            if not numero:
                continue
            lbl = tk.Label(tree, image=icon, borderwidth=0, cursor="hand2")
            lbl.place(x=x + 2, y=y + (h // 2), anchor="w")
            lbl.bind("<Button-1>", lambda _e, n=numero: _abrir_whatsapp(n))
            tree._wa_overlays.append(lbl)
    except Exception as exc:
        log.debug("Falha ao desenhar ícones do WhatsApp: %s", exc)


def _abrir_whatsapp(numero: str) -> None:
    digitos = re.sub(r"\D", "", numero or "")
    if not digitos:
        return
    if not digitos.startswith("55"):
        digitos = "55" + digitos
    try:
        webbrowser.open_new(f"https://web.whatsapp.com/send?phone={digitos}")
    except Exception as exc:
        log.debug("Falha ao abrir WhatsApp: %s", exc)
