# -*- coding: utf-8 -*-
"""Helper para configurar tema do ttk.Treeview no ClientesV2.

DEPRECATED: Use src.ui.ttk_treeview_manager.get_treeview_manager() para novos códigos.
Este módulo mantém wrappers de compatibilidade para códigos legados.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ui.ttk_treeview_theme import apply_treeview_theme as _apply_theme_new
from src.ui.ttk_treeview_theme import apply_zebra as _apply_zebra_new
from src.ui.ttk_treeview_theme import TreeColors


log = logging.getLogger(__name__)


def apply_clients_v2_treeview_theme(mode: str, master: Any = None) -> tuple[str, str, str, str, str]:
    """Configura ttk.Style para a Treeview do ClientesV2 no modo especificado.

    DEPRECATED: Wrapper de compatibilidade. Use get_treeview_manager().register() nos novos códigos.

    Args:
        mode: "Light" ou "Dark"
        master: Widget master para criar ttk.Style (None = root padrão)

    Returns:
        Tupla (even_bg, odd_bg, fg, heading_bg, heading_fg)
    """
    log.warning("[ClientesV2] DEPRECATED: apply_clients_v2_treeview_theme() - use TtkTreeviewManager")

    # Usar nova implementação centralizada
    _, colors = _apply_theme_new(mode, master, style_name="RC.ClientesV2")

    return colors.even_bg, colors.odd_bg, colors.fg, colors.heading_bg, colors.heading_fg


def apply_treeview_zebra_tags(tree: Any, even_bg: str, odd_bg: str, fg: str) -> None:
    """Aplica tags zebra (even/odd) em todas as linhas da Treeview.

    DEPRECATED: Wrapper de compatibilidade. Use apply_zebra() do ttk_treeview_theme.

    Args:
        tree: Instância da Treeview
        even_bg: Cor de fundo para linhas pares
        odd_bg: Cor de fundo para linhas ímpares
        fg: Cor do texto
    """
    log.warning("[ClientesV2] DEPRECATED: apply_treeview_zebra_tags() - use apply_zebra()")

    # Criar TreeColors temporário para compatibilidade

    colors = TreeColors(
        bg=even_bg,
        field_bg=even_bg,
        fg=fg,
        heading_bg="#e5e7eb",
        heading_fg=fg,
        sel_bg="#3b82f6",
        sel_fg="#ffffff",
        even_bg=even_bg,
        odd_bg=odd_bg,
        border="#d1d5db",
    )

    _apply_zebra_new(tree, colors)
