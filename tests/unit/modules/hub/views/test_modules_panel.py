# -*- coding: utf-8 -*-
"""Testes para modules_panel view helper."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock
from tkinter import ttk

import pytest


from src.modules.hub.viewmodels.quick_actions_vm import (
    QuickActionItemView,
    QuickActionsViewState,
)
from src.modules.hub.views.modules_panel import build_modules_panel


def _collect_buttons(widget):
    """Coleta recursivamente todos os tk.Button em uma hierarquia de widgets."""
    buttons = []
    if isinstance(widget, tk.Button):
        buttons.append(widget)
    try:
        for child in widget.winfo_children():
            buttons.extend(_collect_buttons(child))
    except Exception:
        pass
    return buttons


@pytest.fixture
def parent_frame(tk_root):
    """Cria frame pai para testes."""
    return ttk.Frame(tk_root)


class TestBuildModulesPanel:
    """Testes para build_modules_panel helper."""

    def test_creates_labelframe(self, parent_frame):
        """Deve criar widget container com winfo_children (CTkFrame na produção)."""
        state = QuickActionsViewState(actions=[])
        on_action_click = MagicMock()

        panel = build_modules_panel(
            parent=parent_frame,
            state=state,
            on_action_click=on_action_click,
        )

        # Produção retorna CTkFrame, não ttk.Labelframe
        assert hasattr(panel, "winfo_children")
        assert panel is not None

    def test_renders_actions_grouped_by_category(self, parent_frame):
        """Deve renderizar ações agrupadas por categoria com botões."""
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

        # Produção usa CTkFrame por categoria (não ttk.Labelframe)
        # Verificar que 3 botões foram criados (1 por ação)
        all_buttons = _collect_buttons(panel)
        assert len(all_buttons) == 3

        # Verificar labels dos botões
        button_texts = [btn.cget("text") for btn in all_buttons]
        assert "Clientes" in button_texts
        assert "Auditoria" in button_texts
        assert "Anvisa" in button_texts

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

        # Coleta recursiva de botões (CTkFrame hierarquia profunda)
        all_buttons = _collect_buttons(panel)

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

        # Coleta recursiva de botões
        buttons = _collect_buttons(panel)

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

        # Coleta recursiva de botões
        buttons = _collect_buttons(panel)

        assert len(buttons) == 1
        button = buttons[0]

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

        # Produção retorna CTkFrame (não ttk.Labelframe)
        assert hasattr(panel, "winfo_children")

        # Não deve ter botões
        all_buttons = _collect_buttons(panel)
        assert len(all_buttons) == 0
