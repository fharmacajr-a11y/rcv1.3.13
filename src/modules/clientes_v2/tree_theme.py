# -*- coding: utf-8 -*-
"""Helper para configurar tema do ttk.Treeview no ClientesV2.

TAREFA 3: Configuração COMPLETA do ttk.Style com background E fieldbackground.
CRÍTICO: fieldbackground é obrigatório para remover branco residual em áreas vazias.
"""

from __future__ import annotations

import logging
from tkinter import ttk
from typing import Any


log = logging.getLogger(__name__)


def apply_clients_v2_treeview_theme(mode: str) -> tuple[str, str, str, str, str]:
    """Configura ttk.Style para a Treeview do ClientesV2 no modo especificado.

    REGRA B: Configura background E fieldbackground para eliminar branco residual.
    REGRA C: Força tema clam para styling consistente no Windows.

    Args:
        mode: "Light" ou "Dark"

    Returns:
        Tupla (even_bg, odd_bg, fg, heading_bg, heading_fg)
    """
    is_dark = mode == "Dark"

    # Cores para Dark e Light
    if is_dark:
        even_bg = "#2b2b2b"
        odd_bg = "#1e1e1e"
        fg = "#ffffff"
        heading_bg = "#1a1a1a"
        heading_fg = "#ffffff"
        sel_bg = "#3b82f6"
        sel_fg = "#ffffff"
    else:
        even_bg = "#ffffff"
        odd_bg = "#f0f0f0"
        fg = "#000000"
        heading_bg = "#e5e7eb"
        heading_fg = "#000000"
        sel_bg = "#3b82f6"
        sel_fg = "#ffffff"

    log.info(f"🎨 [ClientesV2] Aplicando tema Treeview: {mode}")

    try:
        style = ttk.Style()  # type: ignore[attr-defined]

        # REGRA C: Forçar tema clam (único que aceita customização no Windows)
        try:
            current_theme = style.theme_use()
            if current_theme != "clam":
                style.theme_use("clam")
                log.info(f"✅ [ClientesV2] Tema ttk alterado: {current_theme} → clam")
        except Exception as exc:
            log.warning(f"⚠️ [ClientesV2] Falha ao aplicar tema clam: {exc}")

        # Style customizado "RC.ClientesV2.Treeview"
        style.configure(
            "RC.ClientesV2.Treeview",
            background=even_bg,
            fieldbackground=even_bg,  # CRÍTICO: remove branco residual
            foreground=fg,
            insertcolor=fg,
            borderwidth=0,
            relief="flat",
            rowheight=24,
        )

        # Heading customizado
        style.configure(
            "RC.ClientesV2.Treeview.Heading", background=heading_bg, foreground=heading_fg, relief="flat", borderwidth=0
        )

        # Map de seleção
        style.map("RC.ClientesV2.Treeview", background=[("selected", sel_bg)], foreground=[("selected", sel_fg)])

        # REGRA B: Fallback para "Treeview" padrão (caso wrapper ignore style custom)
        style.configure(
            "Treeview",
            background=even_bg,
            fieldbackground=even_bg,  # CRÍTICO
            foreground=fg,
        )
        style.configure("Treeview.Heading", background=heading_bg, foreground=heading_fg)

        # TAREFA 6: Validação - logar lookup do style
        try:
            test_bg = style.lookup("RC.ClientesV2.Treeview", "background")
            test_field = style.lookup("RC.ClientesV2.Treeview", "fieldbackground")
            test_heading = style.lookup("RC.ClientesV2.Treeview.Heading", "background")
            log.info(f"✅ [ClientesV2] Style aplicado - bg:{test_bg}, field:{test_field}, heading:{test_heading}")
        except Exception:
            pass

    except Exception as exc:
        log.exception(f"❌ [ClientesV2] Erro ao configurar ttk.Style: {exc}")

    return even_bg, odd_bg, fg, heading_bg, heading_fg


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
