# -*- coding: utf-8 -*-
"""Testes para modules_panel view helper."""

from __future__ import annotations

from unittest.mock import MagicMock
from tkinter import ttk

import pytest


from src.modules.hub.viewmodels.quick_actions_vm import (
    QuickActionItemView,
    QuickActionsViewState,
)
from src.modules.hub.views.modules_panel import build_modules_panel


@pytest.fixture
def parent_frame(tk_root):
    """Cria frame pai para testes."""
    return ttk.Frame(tk_root)


class TestBuildModulesPanel:
    """Testes para build_modules_panel helper."""

    def test_creates_labelframe(self, parent_frame):
        """Deve criar Labelframe com título correto."""
        state = QuickActionsViewState(actions=[])
        on_action_click = MagicMock()

        panel = build_modules_panel(
            parent=parent_frame,
            state=state,
            on_action_click=on_action_click,
        )

        assert isinstance(panel, ttk.Labelframe)
        assert panel.cget("text") == "Módulos"

    def test_renders_actions_grouped_by_category(self, parent_frame):
        """Deve renderizar ações agrupadas por categoria."""
        actions = [
            QuickActionItemView(
                id="clientes",
                label="Clientes",
                category="cadastros",
                order=10,
            ),
            QuickActionItemView(
                id="auditoria",
                label="Auditoria",
                category="gestao",
                order=20,
            ),
            QuickActionItemView(
                id="anvisa",
                label="Anvisa",
                category="regulatorio",
                order=30,
            ),
        ]
        state = QuickActionsViewState(actions=actions)
        on_action_click = MagicMock()

        panel = build_modules_panel(
            parent=parent_frame,
            state=state,
            on_action_click=on_action_click,
        )

        # Verificar que criou 3 labelframes (1 por categoria)
        children = list(panel.winfo_children())
        labelframes = [w for w in children if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) == 3

        # Verificar títulos das categorias
        category_titles = [lf.cget("text") for lf in labelframes]
        assert "Cadastros / Acesso" in category_titles
        assert "Gestão / Auditoria" in category_titles
        assert "Regulatório / Programas" in category_titles

    def test_creates_buttons_for_actions(self, parent_frame):
        """Deve criar botões para cada ação."""
        actions = [
            QuickActionItemView(
                id="action1",
                label="Action 1",
                category="cadastros",
                bootstyle="primary",
            ),
            QuickActionItemView(
                id="action2",
                label="Action 2",
                category="cadastros",
                bootstyle="secondary",
            ),
        ]
        state = QuickActionsViewState(actions=actions)
        on_action_click = MagicMock()

        panel = build_modules_panel(
            parent=parent_frame,
            state=state,
            on_action_click=on_action_click,
        )

        # Contar botões criados
        import tkinter as tk

        all_buttons = []
        for child in panel.winfo_children():
            if isinstance(child, ttk.Labelframe):
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Button):
                        all_buttons.append(subchild)

        assert len(all_buttons) == 2
        assert all_buttons[0].cget("text") == "Action 1"
        assert all_buttons[1].cget("text") == "Action 2"

    def test_disabled_actions_have_disabled_buttons(self, parent_frame):
        """Deve criar botões desabilitados para ações desabilitadas."""
        actions = [
            QuickActionItemView(
                id="enabled",
                label="Enabled",
                category="cadastros",
                is_enabled=True,
            ),
            QuickActionItemView(
                id="disabled",
                label="Disabled",
                category="cadastros",
                is_enabled=False,
            ),
        ]
        state = QuickActionsViewState(actions=actions)
        on_action_click = MagicMock()

        panel = build_modules_panel(
            parent=parent_frame,
            state=state,
            on_action_click=on_action_click,
        )

        # Encontrar botões
        import tkinter as tk

        buttons = []
        for child in panel.winfo_children():
            if isinstance(child, ttk.Labelframe):
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Button):
                        buttons.append(subchild)

        assert len(buttons) == 2
        assert str(buttons[0].cget("state")) == "normal"
        assert str(buttons[1].cget("state")) == "disabled"

    def test_button_click_calls_callback(self, parent_frame):
        """Deve chamar callback ao clicar em botão."""
        actions = [
            QuickActionItemView(
                id="test_action",
                label="Test Action",
                category="cadastros",
            ),
        ]
        state = QuickActionsViewState(actions=actions)
        on_action_click = MagicMock()

        panel = build_modules_panel(
            parent=parent_frame,
            state=state,
            on_action_click=on_action_click,
        )

        # Encontrar botão
        import tkinter as tk

        button = None
        for child in panel.winfo_children():
            if isinstance(child, ttk.Labelframe):
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Button):
                        button = subchild
                        break

        assert button is not None

        # Simular clique
        button.invoke()

        # Verificar que callback foi chamado com ID correto
        on_action_click.assert_called_once_with("test_action")

    def test_empty_state_creates_panel_without_buttons(self, parent_frame):
        """Deve criar painel vazio quando não há ações."""
        state = QuickActionsViewState(actions=[])
        on_action_click = MagicMock()

        panel = build_modules_panel(
            parent=parent_frame,
            state=state,
            on_action_click=on_action_click,
        )

        assert isinstance(panel, ttk.Labelframe)

        # Não deve ter labelframes filhos (sem categorias)
        children = list(panel.winfo_children())
        labelframes = [w for w in children if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) == 0
