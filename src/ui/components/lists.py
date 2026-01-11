# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable

import ttkbootstrap as tb

from config.constants import (
    COL_CNPJ_WIDTH,
    COL_ID_WIDTH,
    COL_NOME_WIDTH,
    COL_OBS_WIDTH,
    COL_RAZAO_WIDTH,
    COL_STATUS_WIDTH,
    COL_ULTIMA_WIDTH,
    COL_WHATSAPP_WIDTH,
)
from src.modules.clientes.views.main_screen_constants import (
    STATUS_COLOR_DEFAULT,
    STATUS_COLORS,
    TREEVIEW_FONT_FAMILY,
    TREEVIEW_FONT_SIZE,
    TREEVIEW_HEADING_FONT_SIZE,
    TREEVIEW_ROW_HEIGHT,
    ZEBRA_COLOR_EVEN,
    ZEBRA_COLOR_ODD,
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
    """Create the main clients Treeview configured with column widths and bindings.

    Inclui melhorias visuais:
    - Altura de linha aumentada para melhor legibilidade
    - Fonte moderna (Segoe UI)
    - Zebra striping para linhas alternadas
    - Tags de status coloridas
    """
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

    # ========================================================================
    # CONFIGURAÇÃO DE ESTILO MODERNIZADO
    # ========================================================================

    style = tb.Style()

    # Configurar altura da linha (rowheight)
    try:
        style.configure("Treeview", rowheight=TREEVIEW_ROW_HEIGHT)
    except Exception as exc:
        log.debug("Falha ao configurar rowheight do Treeview: %s", exc)

    # Configurar fonte da Treeview
    try:
        tree_font = tkfont.Font(family=TREEVIEW_FONT_FAMILY, size=TREEVIEW_FONT_SIZE)
        heading_font = tkfont.Font(
            family=TREEVIEW_FONT_FAMILY, size=TREEVIEW_HEADING_FONT_SIZE, weight="bold"
        )
        style.configure("Treeview", font=tree_font)
        style.configure("Treeview.Heading", font=heading_font)
    except Exception as exc:
        log.debug("Falha ao configurar fonte do Treeview: %s", exc)

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

    # ========================================================================
    # CONFIGURAÇÃO DE TAGS VISUAIS
    # ========================================================================

    try:
        default_font = tkfont.Font(family=TREEVIEW_FONT_FAMILY, size=TREEVIEW_FONT_SIZE)
        bold_font = default_font.copy()
        bold_font.configure(weight="bold")
        tree.tag_configure("has_obs", font=bold_font, foreground=OBS_FG)
    except Exception as exc:
        log.debug("Falha ao configurar fonte em negrito: %s", exc)

    # Configurar zebra striping (linhas alternadas)
    try:
        tree.tag_configure("zebra_odd", background=ZEBRA_COLOR_ODD)
        tree.tag_configure("zebra_even", background=ZEBRA_COLOR_EVEN)
    except Exception as exc:
        log.debug("Falha ao configurar zebra striping: %s", exc)

    # Configurar tags de status com cores
    try:
        status_font = tkfont.Font(
            family=TREEVIEW_FONT_FAMILY, size=TREEVIEW_FONT_SIZE, weight="bold"
        )

        for status_name, colors in STATUS_COLORS.items():
            # Sanitizar nome do status para usar como tag (remover espaços e acentos)
            tag_name = f"status_{status_name.lower().replace(' ', '_').replace('á', 'a').replace('ã', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ç', 'c')}"
            tree.tag_configure(
                tag_name,
                foreground=colors.get("foreground", STATUS_COLOR_DEFAULT["foreground"]),
                background=colors.get("background", STATUS_COLOR_DEFAULT["background"]),
                font=status_font,
            )

        # Tag padrão para status não mapeados
        tree.tag_configure(
            "status_default",
            foreground=STATUS_COLOR_DEFAULT["foreground"],
            background=STATUS_COLOR_DEFAULT["background"],
        )
    except Exception as exc:
        log.debug("Falha ao configurar tags de status: %s", exc)

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
            tree.configure(cursor="hand2" if col in ("#5",) else "")
        except Exception:
            tree.configure(cursor="")

    tree.bind("<Motion>", _on_motion_hand_cursor, add="+")
    tree.bind("<Leave>", lambda _e: tree.configure(cursor=""), add="+")

    return tree
