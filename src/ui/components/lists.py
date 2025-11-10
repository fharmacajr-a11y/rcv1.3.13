# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable

import ttkbootstrap as tb

from src.config.constants import COL_STATUS_WIDTH  # <-- adicionar
from src.config.constants import (
    COL_CNPJ_WIDTH,
    COL_ID_WIDTH,
    COL_NOME_WIDTH,
    COL_OBS_WIDTH,
    COL_RAZAO_WIDTH,
    COL_ULTIMA_WIDTH,
    COL_WHATSAPP_WIDTH,
)

OBS_FG = "#0d6efd"

logger = logging.getLogger(__name__)
log = logger

__all__ = ["create_clients_treeview"]


def create_clients_treeview(
    parent: tk.Misc,
    *,
    on_double_click: Callable[[Any], Any] | None,
    on_select: Callable[[Any], Any] | None,
    on_delete: Callable[[Any], Any] | None,
    on_click: Callable[[Any], Any] | None,
) -> tb.Treeview:
    """Create the main clients Treeview configured with column widths and bindings."""
    columns = (
        ("ID", "ID", COL_ID_WIDTH, False),
        ("Razao Social", "Razão Social", COL_RAZAO_WIDTH, True),  # só esta estica
        ("CNPJ", "CNPJ", COL_CNPJ_WIDTH, False),
        ("Nome", "Nome", COL_NOME_WIDTH, False),
        ("WhatsApp", "WhatsApp", COL_WHATSAPP_WIDTH, False),  # col #5
        ("Observacoes", "Observações", COL_OBS_WIDTH, True),  # col #6
        ("Status", "Status", COL_STATUS_WIDTH, False),  # col #7 (NOVA)
        ("Ultima Alteracao", "Última Alteração", COL_ULTIMA_WIDTH, False),
    )

    tree = tb.Treeview(parent, columns=[c[0] for c in columns], show="headings")

    for key, heading, _, _ in columns:
        tree.heading(key, text=heading, anchor="center")

    for key, _, width, can_stretch in columns:
        tree.column(
            key, width=width, minwidth=width, anchor="center", stretch=can_stretch
        )

    def _block_header_resize(event: Any) -> str | None:
        if tree.identify_region(event.x, event.y) == "separator":
            return "break"
        return None

    tree.bind("<Button-1>", _block_header_resize, add="+")

    try:
        default_font = tkfont.nametofont("TkDefaultFont")
        bold_font = default_font.copy()
        bold_font.configure(weight="bold")
        tree.tag_configure("has_obs", font=bold_font, foreground=OBS_FG)
    except Exception as exc:
        log.debug("Falha ao configurar fonte em negrito: %s", exc)

    if on_double_click:
        tree.bind("<Double-1>", on_double_click, add="+")
    if on_select:
        tree.bind("<<TreeviewSelect>>", on_select, add="+")
    if on_delete:
        tree.bind("<Delete>", on_delete, add="+")
    if on_click:
        tree.bind("<ButtonRelease-1>", on_click, add="+")

    def _on_motion_hand_cursor(event: Any) -> None:
        try:
            col = tree.identify_column(event.x)
            tree.configure(cursor="hand2" if col in ("#5", "#7") else "")
        except Exception:
            tree.configure(cursor="")

    tree.bind("<Motion>", _on_motion_hand_cursor, add="+")
    tree.bind("<Leave>", lambda _e: tree.configure(cursor=""), add="+")

    return tree
