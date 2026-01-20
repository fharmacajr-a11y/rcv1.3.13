from __future__ import annotations

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import (
    APP_BG, SURFACE_DARK, SURFACE, TITLE_FONT, TEXT_PRIMARY, CARD_RADIUS
)

# -*- coding: utf-8 -*-
"""Módulos/Quick Actions panel view builder.

Este módulo contém apenas lógica de UI para construir o painel de módulos/atalhos.
Não acessa diretamente ViewModels ou Controllers - recebe state e callbacks.
"""

import tkinter as tk
from typing import TYPE_CHECKING, Callable

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

from src.modules.hub.constants import (
    MODULES_TITLE,
    PAD_OUTER,
)

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import QuickActionsViewState


# Tooltip simples (fallback sem ttkbootstrap)
class ToolTip:
    """Tooltip simples para widgets Tkinter."""
    def __init__(self, widget, text="", wraplength=200):
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self.tipwindow = None
        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        wraplength=self.wraplength, padx=4, pady=2)
        label.pack()

    def _on_leave(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


def build_modules_panel(
    parent: tk.Misc,
    state: "QuickActionsViewState",
    on_action_click: Callable[[str], None],
) -> tk.LabelFrame:
    """Constrói o painel de módulos (menu vertical à esquerda) com Quick Actions.

    Args:
        parent: Frame pai onde o painel será criado.
        state: Estado dos atalhos (QuickActionsViewState).
        on_action_click: Callback para clique em ação (recebe action_id).

    Returns:
        O Labelframe do painel de módulos.
    """
    # MICROFASE 35: Padrão consistente - card cinza sem borda
    modules_panel = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_DARK,
        bg_color=APP_BG,
        border_width=0,
        corner_radius=CARD_RADIUS,
    )
    
    # Título do painel
    title_label = ctk.CTkLabel(
        modules_panel,
        text=MODULES_TITLE,
        font=TITLE_FONT,
        text_color=TEXT_PRIMARY,
        fg_color="transparent"
    )
    title_label.pack(anchor="w", padx=14, pady=(12, 6))
    
    # Frame interno branco para conteúdo
    content_frame = ctk.CTkFrame(
        modules_panel,
        fg_color=SURFACE,
        corner_radius=max(10, CARD_RADIUS - 4),
        border_width=0,
        bg_color=SURFACE_DARK
    )
    content_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    # Construir os atalhos agrupados por categoria
    _build_quick_actions_by_category(content_frame, state, on_action_click)

    return modules_panel


def _build_quick_actions_by_category(
    parent_frame: tk.Misc,
    state: "QuickActionsViewState",
    on_action_click: Callable[[str], None],
) -> None:
    """Constrói os botões de atalhos agrupados por categoria.

    Args:
        parent_frame: Frame pai onde os blocos serão criados.
        state: Estado dos atalhos (QuickActionsViewState).
        on_action_click: Callback para clique em ação (recebe action_id).
    """
    # Agrupar ações por categoria
    actions_by_category: dict[str, list] = {}
    for action in state.actions:
        if action.category not in actions_by_category:
            actions_by_category[action.category] = []
        actions_by_category[action.category].append(action)

    # Mapa de categorias para títulos de blocos
    category_titles = {
        "cadastros": "Cadastros / Acesso",
        "gestao": "Gestão / Auditoria",
        "regulatorio": "Regulatório / Programas",
    }

    # Mapa de categorias para ordem de exibição
    category_order = {"cadastros": 0, "gestao": 1, "regulatorio": 2}

    # Ordenar categorias
    sorted_categories = sorted(
        actions_by_category.keys(),
        key=lambda cat: category_order.get(cat, 999),
    )

    # Criar blocos para cada categoria
    for idx, category in enumerate(sorted_categories):
        actions = actions_by_category[category]
        title = category_titles.get(category, category.title())

        # Criar labelframe para o bloco
        pady = (0, 8) if idx < len(sorted_categories) - 1 else (0, 0)
        frame_category = ctk.CTkFrame(parent_frame)  # TODO: text=title, padding=(8, 6) -> usar CTkLabel + pack/grid
        frame_category.pack(fill="x", pady=pady)
        frame_category.columnconfigure(0, weight=1)
        frame_category.columnconfigure(1, weight=1)

        # Criar botões para cada ação
        for row_idx, action in enumerate(actions):
            col = row_idx % 2
            row = row_idx // 2

            btn = tk.Button(
                frame_category,
                text=action.label,
                command=lambda a_id=action.id: on_action_click(a_id),
            )

            if not action.is_enabled:
                btn.configure(state="disabled")

            # Adicionar tooltip se descrição disponível
            if action.description:
                ToolTip(btn, text=action.description, wraplength=260)

            btn.grid(row=row, column=col, sticky="ew", padx=3, pady=3)
