# -*- coding: utf-8 -*-
"""Tema centralizado para ttk.Treeview com suporte a Light/Dark mode.

Fornece cores e funções para aplicar tema consistente em todos os Treeviews do app.
Usa TABLE_UI_SPEC para padronizar visual (fonte, rowheight, padding, etc).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from tkinter import ttk
from typing import Any

from src.ui.table_ui_spec import TABLE_UI_SPEC, get_table_font

log = logging.getLogger(__name__)


@dataclass
class TreeColors:
    """Cores para Treeview em um modo específico."""

    bg: str  # Background principal
    field_bg: str  # Field background (áreas vazias)
    fg: str  # Foreground (texto)
    heading_bg: str  # Background do heading
    heading_fg: str  # Foreground do heading
    sel_bg: str  # Background quando selecionado
    sel_fg: str  # Foreground quando selecionado
    even_bg: str  # Background linhas pares (zebra)
    odd_bg: str  # Background linhas ímpares (zebra)
    border: str  # Cor da borda


def get_tree_colors(mode: str) -> TreeColors:
    """Retorna cores do Treeview para o modo especificado.

    Args:
        mode: "Light" ou "Dark"

    Returns:
        TreeColors com todas as cores do tema
    """
    if mode == "Dark":
        return TreeColors(
            bg="#2b2b2b",
            field_bg="#2b2b2b",
            fg="#f5f5f5",
            heading_bg="#1a1a1a",
            heading_fg="#f5f5f5",
            sel_bg="#2563eb",
            sel_fg="#ffffff",
            even_bg="#2b2b2b",
            odd_bg="#242424",
            border="#1a1a1a",
        )
    else:  # Light
        return TreeColors(
            bg="#ffffff",
            field_bg="#ffffff",
            fg="#111111",
            heading_bg="#e5e7eb",
            heading_fg="#111111",
            sel_bg="#3b82f6",
            sel_fg="#ffffff",
            even_bg="#ffffff",
            odd_bg="#e6eaf0",  # Cinza mais escuro para melhor contraste
            border="#d1d5db",
        )


def apply_treeview_theme(mode: str, master: Any, style_name: str = "RC.Treeview") -> tuple[str, TreeColors]:
    """Aplica tema no ttk.Style para Treeview.

    CRÍTICO: Passa master correto para ttk.Style funcionar em Toplevels.
    CRÍTICO: Usa tema "clam" para fieldbackground funcionar (vista/xpnative ignoram).

    Args:
        mode: "Light" ou "Dark"
        master: Widget master para criar ttk.Style
        style_name: Nome base do style (ex: "RC.Treeview")

    Returns:
        Tupla (nome_style_completo, TreeColors)
    """
    colors = get_tree_colors(mode)

    try:
        # Criar Style com master correto
        # IMPORTANTE: ttk.Style() retorna a instância singleton, não cria nova
        style = ttk.Style(master)  # type: ignore[attr-defined]

        # CRÍTICO: Forçar tema "clam" para fieldbackground funcionar
        try:
            current = style.theme_use()
            if current != "clam":
                style.theme_use("clam")
                log.debug(f"[TtkTreeTheme] Tema alterado: {current} → clam (mode={mode})")
        except Exception as exc:
            log.warning(f"[TtkTreeTheme] Erro ao definir tema clam: {exc}")

        # Normalizar style_name (remover .Treeview se já existe)
        base_name = style_name.removesuffix(".Treeview")
        full_style_name = f"{base_name}.Treeview"

        log.debug(
            f"[TtkTreeTheme] Aplicando: {full_style_name}, mode={mode}, bg={colors.bg}, field_bg={colors.field_bg}"
        )

        # Aplicar TABLE_UI_SPEC para consistência visual
        font_tuple = get_table_font(heading=False)
        heading_font_tuple = get_table_font(heading=True)

        style.configure(
            full_style_name,
            background=colors.bg,
            fieldbackground=colors.field_bg,  # CRÍTICO: remove branco residual
            foreground=colors.fg,
            insertcolor=colors.fg,
            borderwidth=TABLE_UI_SPEC.border_width,
            relief=TABLE_UI_SPEC.relief,
            rowheight=TABLE_UI_SPEC.row_height,
            font=font_tuple,  # Fonte padronizada
        )

        # Configurar Heading com fonte e dimensões padronizadas
        style.configure(
            f"{full_style_name}.Heading",
            background=colors.heading_bg,
            foreground=colors.heading_fg,
            relief=TABLE_UI_SPEC.heading_relief,
            borderwidth=TABLE_UI_SPEC.heading_border_width,
            font=heading_font_tuple,  # Fonte do header (bold)
        )

        # Map de seleção
        # CRÍTICO: NÃO forçar background="" no map, isso mata o zebra por tags
        style.map(
            full_style_name,
            background=[("selected", colors.sel_bg)],
            foreground=[("selected", colors.sel_fg)],
            fieldbackground=[("", colors.field_bg)],
        )

        # Fallback para "Treeview" padrão
        style.configure(
            "Treeview",
            background=colors.bg,
            fieldbackground=colors.field_bg,
            foreground=colors.fg,
        )
        style.configure(
            "Treeview.Heading",
            background=colors.heading_bg,
            foreground=colors.heading_fg,
        )

        log.debug(f"[TtkTreeTheme] Tema aplicado: {mode} style={full_style_name}")

    except Exception as exc:
        log.exception(f"[TtkTreeTheme] Erro ao aplicar tema: {exc}")

    return full_style_name, colors


def apply_zebra(tree: Any, colors: TreeColors, parent_iid: str = "") -> None:
    """Aplica tags zebra (even/odd) nas linhas da Treeview.

    IMPORTANTE: Configura tag 'selected' PRIMEIRO para ganhar precedência (ordem de criação).
    Preserva a tag 'selected' por último na lista de tags de cada item.

    Args:
        tree: Instância do ttk.Treeview
        colors: TreeColors com as cores do tema
        parent_iid: ID do item pai (vazio = raiz)
    """
    try:
        # CRÍTICO: Configurar tag "selected" PRIMEIRO (ordem de criação = prioridade no ttk.Treeview)
        # Tag criada primeiro tem MAIOR prioridade visual
        tree.tag_configure("selected", background=colors.sel_bg, foreground=colors.sel_fg)

        # Configurar tags zebra COM background (necessário para zebra funcionar)
        # Em Dark mode: even=#2b2b2b, odd=#242424
        # Em Light mode: even=#ffffff, odd=#e6eaf0
        tree.tag_configure("even", background=colors.even_bg, foreground=colors.fg)
        tree.tag_configure("odd", background=colors.odd_bg, foreground=colors.fg)

        log.debug(f"[TtkTreeTheme] Tags configuradas: selected={colors.sel_bg}, even={colors.even_bg}, odd={colors.odd_bg}")

        # Aplicar tags em todos os filhos do parent
        items = tree.get_children(parent_iid)
        for idx, iid in enumerate(items):
            tag = "even" if idx % 2 == 0 else "odd"
            # Preservar outras tags, mas garantir 'selected' por último
            current_tags = tree.item(iid, "tags")
            new_tags = [t for t in current_tags if t not in ("even", "odd", "selected")]
            new_tags.append(tag)
            # Se tinha 'selected', adicionar por último (maior precedência)
            if "selected" in current_tags:
                new_tags.append("selected")
            tree.item(iid, tags=tuple(new_tags))

        log.debug(f"[TtkTreeTheme] Zebra aplicada: {len(items)} itens")

    except Exception as exc:
        log.exception(f"[TtkTreeTheme] Erro ao aplicar zebra: {exc}")


def apply_selected_tag(tree: Any, colors: TreeColors) -> None:
    """Aplica tag 'selected' na linha atualmente selecionada.

    Remove 'selected' de todos os itens e adiciona apenas no item selecionado.
    A tag 'selected' deve ficar por último para ter precedência sobre even/odd.

    Args:
        tree: Instância do ttk.Treeview
        colors: TreeColors com as cores do tema
    """
    try:
        # Configurar tag selected
        tree.tag_configure("selected", background=colors.sel_bg, foreground=colors.sel_fg)

        # Remover 'selected' de todos os itens (preservando outras tags)
        for iid in tree.get_children(""):
            current_tags = tree.item(iid, "tags")
            new_tags = [t for t in current_tags if t != "selected"]
            tree.item(iid, tags=tuple(new_tags))

        # Adicionar 'selected' SOMENTE no item atualmente selecionado
        selection = tree.selection()
        if selection:
            iid = selection[0]
            current_tags = tree.item(iid, "tags")
            # Remover 'selected' se já existe e adicionar por último
            new_tags = [t for t in current_tags if t != "selected"]
            new_tags.append("selected")
            tree.item(iid, tags=tuple(new_tags))
            log.debug(f"[TtkTreeTheme] Tag 'selected' aplicada ao item: {iid}")

    except Exception as exc:
        log.exception(f"[TtkTreeTheme] Erro ao aplicar selected tag: {exc}")
