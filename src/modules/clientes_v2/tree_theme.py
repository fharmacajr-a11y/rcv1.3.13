# -*- coding: utf-8 -*-
"""Helper para configurar tema do ttk.Treeview no ClientesV2.

TAREFA 3: Configuração COMPLETA do ttk.Style com background E fieldbackground.
CRÍTICO: fieldbackground é obrigatório para remover branco residual em áreas vazias.

MICROFASE 36: Refatorado para usar src/ui/ttk_compat.py (SSoT para temas Treeview).
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Literal

from src.ui.ttk_compat import apply_treeview_theme

log = logging.getLogger(__name__)


def get_treeview_zebra_colors(mode: Literal["Light", "Dark"]) -> tuple[str, str, str, str, str]:
    """Retorna cores para tags zebra baseadas no modo.

    Args:
        mode: "Light" ou "Dark"

    Returns:
        Tupla (even_bg, odd_bg, fg, heading_bg, heading_fg)
    """
    if mode == "Dark":
        return "#2b2b2b", "#1e1e1e", "#ffffff", "#1a1a1a", "#ffffff"
    else:  # Light
        return "#ffffff", "#f0f0f0", "#000000", "#e5e7eb", "#000000"


def apply_clients_v2_treeview_theme(
    mode: Literal["Light", "Dark"],
    tree: ttk.Treeview,
    *,
    master: tk.Misc | None = None,
) -> tuple[str, str, str, str, str]:
    """Configura ttk.Style para a Treeview do ClientesV2 no modo especificado.

    BASELINE CODEC: Usa ttk_compat.apply_treeview_theme (SSoT).

    Args:
        mode: "Light" ou "Dark"
        tree: Instância da Treeview a ser tematizada
        master: Widget master para ttk.Style (default: parent do tree)

    Returns:
        Tupla (even_bg, odd_bg, fg, heading_bg, heading_fg) para tags zebra
    """
    log.info(f"🎨 [ClientesV2] Aplicando tema Treeview: {mode}")

    # Delegar para helper genérico
    apply_treeview_theme(
        tree,
        mode,
        master=master,
        style_name="RC.ClientesV2.Treeview",
    )

    # Retornar cores para tags zebra (compatibilidade com código existente)
    return get_treeview_zebra_colors(mode)


def apply_treeview_zebra_tags(tree: Any, even_bg: str, odd_bg: str, fg: str) -> None:
    """Aplica tags zebra (even/odd) em todas as linhas da Treeview.

    Args:
        tree: Instância da Treeview
        even_bg: Cor de fundo para linhas pares
        odd_bg: Cor de fundo para linhas ímpares
        fg: Cor do texto
    """
    try:
        # Configurar tags
        tree.tag_configure("even", background=even_bg, foreground=fg)
        tree.tag_configure("odd", background=odd_bg, foreground=fg)

        # Reaplicar em todas as linhas existentes
        all_items = tree.get_children()
        for idx, item_id in enumerate(all_items):
            tag = "even" if idx % 2 == 0 else "odd"
            current_tags = tree.item(item_id, "tags")
            new_tags = [t for t in current_tags if t not in ("even", "odd")]
            new_tags.append(tag)
            tree.item(item_id, tags=new_tags)

        log.debug(f"[ClientesV2] Tags zebra reaplicadas em {len(all_items)} linhas")
    except Exception:
        log.exception("[ClientesV2] Erro ao aplicar tags zebra")

    """Aplica tags zebra (even/odd) em todas as linhas da Treeview.

    Args:
        tree: Instância da Treeview
        even_bg: Cor de fundo para linhas pares
        odd_bg: Cor de fundo para linhas ímpares
        fg: Cor do texto
    """
    try:
        # Configurar tags
        tree.tag_configure("even", background=even_bg, foreground=fg)
        tree.tag_configure("odd", background=odd_bg, foreground=fg)

        # Reaplicar em todas as linhas existentes
        all_items = tree.get_children()
        for idx, item_id in enumerate(all_items):
            tag = "even" if idx % 2 == 0 else "odd"
            current_tags = tree.item(item_id, "tags")
            new_tags = [t for t in current_tags if t not in ("even", "odd")]
            new_tags.append(tag)
            tree.item(item_id, tags=new_tags)

        log.debug(f"[ClientesV2] Tags zebra reaplicadas em {len(all_items)} linhas")
    except Exception:
        log.exception("[ClientesV2] Erro ao aplicar tags zebra")
