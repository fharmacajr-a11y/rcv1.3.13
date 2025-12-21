# -*- coding: utf-8 -*-
"""Módulos/Quick Actions panel view builder.

Este módulo contém apenas lógica de UI para construir o painel de módulos/atalhos.
Não acessa diretamente ViewModels ou Controllers - recebe state e callbacks.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Callable

import ttkbootstrap as tb

from src.modules.hub.constants import (
    MODULES_TITLE,
    PAD_OUTER,
)

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import QuickActionsViewState


def build_modules_panel(
    parent: tk.Misc,
    state: "QuickActionsViewState",
    on_action_click: Callable[[str], None],
) -> tb.Labelframe:
    """Constrói o painel de módulos (menu vertical à esquerda) com Quick Actions.

    Args:
        parent: Frame pai onde o painel será criado.
        state: Estado dos atalhos (QuickActionsViewState).
        on_action_click: Callback para clique em ação (recebe action_id).

    Returns:
        O Labelframe do painel de módulos.
    """
    modules_panel = tb.Labelframe(parent, text=MODULES_TITLE, padding=PAD_OUTER)

    # Construir os atalhos agrupados por categoria
    _build_quick_actions_by_category(modules_panel, state, on_action_click)

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
        frame_category = tb.Labelframe(
            parent_frame,
            text=title,
            padding=(8, 6),
        )
        frame_category.pack(fill="x", pady=pady)
        frame_category.columnconfigure(0, weight=1)
        frame_category.columnconfigure(1, weight=1)

        # Criar botões para cada ação
        for row_idx, action in enumerate(actions):
            col = row_idx % 2
            row = row_idx // 2

            btn = tb.Button(
                frame_category,
                text=action.label,
                command=lambda a_id=action.id: on_action_click(a_id),
                bootstyle=action.bootstyle or "secondary",
            )

            if not action.is_enabled:
                btn.configure(state="disabled")

            if action.description:
                # TODO: Adicionar tooltip quando disponível
                pass

            btn.grid(row=row, column=col, sticky="ew", padx=3, pady=3)
