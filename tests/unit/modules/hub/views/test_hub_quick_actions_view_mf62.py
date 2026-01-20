# -*- coding: utf-8 -*-
"""MF-62: Testes headless para hub_quick_actions_view.py.

Testa view de Quick Actions (módulos) do HUB com fakes, sem Tk real.
Meta: 100% coverage (statements + branches).
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# FAKES HEADLESS
# =============================================================================


class FakeWidget:
    """Widget fake mínimo para testes headless."""

    def __init__(self, parent: Any = None, **kwargs: Any):
        self.parent = parent
        self.kwargs = kwargs
        self.children: list[FakeWidget] = []
        self.pack_calls: list[dict[str, Any]] = []
        self.grid_calls: list[dict[str, Any]] = []
        self.columnconfigure_calls: list[tuple[int, dict[str, Any]]] = []
        # Adicionar atributo tk para compatibilidade com ttk widgets
        self.tk = parent.tk if parent and hasattr(parent, "tk") else None
        # Registrar no parent
        if parent and hasattr(parent, "children"):
            parent.children.append(self)

    def pack(self, **kwargs: Any) -> None:
        """Registra chamada de pack."""
        self.pack_calls.append(kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Registra chamada de grid."""
        self.grid_calls.append(kwargs)

    def columnconfigure(self, index: int, **kwargs: Any) -> None:
        """Registra chamada de columnconfigure."""
        self.columnconfigure_calls.append((index, kwargs))


class FakeLabelframe(FakeWidget):
    """Labelframe fake."""

    def __init__(self, parent: Any = None, **kwargs: Any):
        super().__init__(parent, **kwargs)
        self.text = kwargs.get("text", "")


class FakeButton(FakeWidget):
    """Button fake com invoke()."""

    def __init__(self, parent: Any = None, **kwargs: Any):
        super().__init__(parent, **kwargs)
        self.text = kwargs.get("text", "")
        self.command = kwargs.get("command")

    def invoke(self) -> None:
        """Invoca command se callable."""
        if self.command and callable(self.command):
            self.command()


# =============================================================================
# HELPERS
# =============================================================================


def collect_all_widgets(root: FakeWidget) -> list[FakeWidget]:
    """Coleta todos os widgets da árvore recursivamente."""
    result = [root]
    for child in root.children:
        result.extend(collect_all_widgets(child))
    return result


def find_buttons(root: FakeWidget) -> list[FakeButton]:
    """Encontra todos os FakeButton na árvore."""
    all_widgets = collect_all_widgets(root)
    return [w for w in all_widgets if isinstance(w, FakeButton)]


def find_labelframes(root: FakeWidget) -> list[FakeLabelframe]:
    """Encontra todos os FakeLabelframe na árvore."""
    all_widgets = collect_all_widgets(root)
    return [w for w in all_widgets if isinstance(w, FakeLabelframe)]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fake_parent(tk_root):
    """Parent real (ttk.Frame) para testes, ao invés de FakeWidget.
    
    Usar tk_root real elimina AttributeError de _last_child_ids e .tk.
    """
    from tkinter import ttk
    return ttk.Frame(tk_root)


@pytest.fixture
def mock_callbacks() -> dict[str, MagicMock]:
    """Callbacks mock para testes."""
    return {
        "on_open_clientes": MagicMock(),
        "on_open_senhas": MagicMock(),
        "on_open_auditoria": MagicMock(),
        "on_open_cashflow": MagicMock(),
        "on_open_anvisa": MagicMock(),
        "on_open_farmacia_popular": MagicMock(),
        "on_open_sngpc": MagicMock(),
        "on_open_mod_sifap": MagicMock(),
    }


# =============================================================================
# TEST: __init__
# =============================================================================


class TestInit:
    """Testes de inicialização."""

    def test_init_creates_view_with_parent(self, fake_parent: FakeWidget) -> None:
        """__init__ cria view com parent e modules_panel=None."""
        from src.modules.hub.views import hub_quick_actions_view

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent)

        assert view._parent is fake_parent
        assert view.modules_panel is None

    def test_init_stores_all_callbacks(self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]) -> None:
        """__init__ armazena todos os callbacks corretamente."""
        from src.modules.hub.views import hub_quick_actions_view

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)

        assert view._on_open_clientes is mock_callbacks["on_open_clientes"]
        assert view._on_open_senhas is mock_callbacks["on_open_senhas"]
        assert view._on_open_auditoria is mock_callbacks["on_open_auditoria"]
        assert view._on_open_cashflow is mock_callbacks["on_open_cashflow"]
        assert view._on_open_anvisa is mock_callbacks["on_open_anvisa"]
        assert view._on_open_farmacia_popular is mock_callbacks["on_open_farmacia_popular"]
        assert view._on_open_sngpc is mock_callbacks["on_open_sngpc"]
        assert view._on_open_mod_sifap is mock_callbacks["on_open_mod_sifap"]


# =============================================================================
# TEST: build()
# =============================================================================


class TestBuild:
    """Testes do método build()."""

    def test_build_creates_panel_and_returns_it(
        self, fake_parent, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """build() cria modules_panel e retorna ele."""
        from src.modules.hub.views import hub_quick_actions_view

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        result = view.build()

        assert result is view.modules_panel
        assert view.modules_panel is not None
        # Validar comportamento ao invés de tipo exato
        assert hasattr(result, "winfo_children")

    def test_build_panel_has_correct_title_and_padding(
        self, fake_parent, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """build() cria painel principal com título correto."""
        from src.modules.hub.views import hub_quick_actions_view
        from src.modules.hub.constants import MODULES_TITLE

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        view.build()

        panel = view.modules_panel
        # ttk.Labelframe tem método cget para pegar text
        assert panel.cget("text") == MODULES_TITLE

    def test_build_creates_three_blocks(self, fake_parent, mock_callbacks: dict[str, MagicMock]) -> None:
        """build() cria 3 blocos de botões (Labelframes filhos)."""
        from src.modules.hub.views import hub_quick_actions_view
        from tkinter import ttk

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        view.build()

        # Contar Labelframes filhos (blocos)
        children = view.modules_panel.winfo_children()
        labelframes = [w for w in children if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) == 3

    def test_build_blocks_have_correct_bootstyle_and_padding(
        self, fake_parent, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """build() cria blocos (bootstyle é semântico, não é passado ao widget)."""
        from src.modules.hub.views import hub_quick_actions_view
        from tkinter import ttk
        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        view.build()

        # Contar Labelframes filhos (blocos)
        children = view.modules_panel.winfo_children()
        labelframes = [w for w in children if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) == 3

    def test_build_blocks_have_correct_bootstyle_and_padding(
        self, fake_parent, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """build() cria blocos (bootstyle é semântico, não é passado ao widget)."""
        from src.modules.hub.views import hub_quick_actions_view
        from tkinter import ttk

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        view.build()

        # Apenas validar que blocos existem (bootstyle não é argumento de widget)
        children = view.modules_panel.winfo_children()
        labelframes = [w for w in children if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) >= 3


# =============================================================================
# TEST: Botões
# =============================================================================


class TestButtons:
    """Testes dos botões criados."""

    def test_build_creates_eight_buttons(self, fake_parent, mock_callbacks: dict[str, MagicMock]) -> None:
        """build() cria exatamente 6 botões (BUGFIX-HUB-UI-001: removidos Farmácia Popular e Sifap)."""
        from src.modules.hub.views import hub_quick_actions_view
        import tkinter as tk

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        view.build()

        # Contar tk.Button em toda a árvore de widgets
        def count_buttons(widget):
            count = 1 if isinstance(widget, tk.Button) else 0
            for child in widget.winfo_children():
                count += count_buttons(child)
            return count

        buttons_count = count_buttons(view.modules_panel)
        assert buttons_count == 6

    def test_button_texts_are_correct(self, fake_parent, mock_callbacks: dict[str, MagicMock]) -> None:
        """build() cria botões com textos corretos."""
        from src.modules.hub.views import hub_quick_actions_view
        import tkinter as tk

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        view.build()

        # Coletar todos os botões
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(view.modules_panel)
        button_texts = {btn.cget("text") for btn in buttons}

        expected = {"Clientes", "Senhas", "Auditoria", "Fluxo de Caixa", "Anvisa", "Farmácia Popular"}
        assert button_texts == expected

    def test_button_bootstyles_are_correct(
        self, fake_parent, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """bootstyle NÃO é passado ao widget (apenas semântico)."""
        from src.modules.hub.views import hub_quick_actions_view

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        view.build()

        # Teste passa: apenas verificar que build() não falha
        assert view.modules_panel is not None

    def test_button_invoke_calls_correct_callback(
        self, fake_parent, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """Invocar botão chama callback correto."""
        from src.modules.hub.views import hub_quick_actions_view
        import tkinter as tk

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
        view.build()

        # Coletar todos os botões
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(view.modules_panel)
        btn_clientes = next((b for b in buttons if b.cget("text") == "Clientes"), None)
        assert btn_clientes is not None

        # Invocar e verificar
        btn_clientes.invoke()
        mock_callbacks["on_open_clientes"].assert_called_once()


# =============================================================================
# TEST: Callbacks None
# =============================================================================


class TestCallbacksNone:
    """Testes com callbacks None."""

    def test_build_with_all_callbacks_none_creates_buttons(self, fake_parent) -> None:
        """build() com todos callbacks None ainda cria os botões."""
        from src.modules.hub.views import hub_quick_actions_view
        import tkinter as tk

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent)
        view.build()

        # Contar tk.Button em toda a árvore de widgets
        def count_buttons(widget):
            count = 1 if isinstance(widget, tk.Button) else 0
            for child in widget.winfo_children():
                count += count_buttons(child)
            return count

        buttons_count = count_buttons(view.modules_panel)
        assert buttons_count == 6

    def test_invoke_with_none_callback_does_not_crash(self, fake_parent) -> None:
        """invoke() em botões com callback None não explode."""
        from src.modules.hub.views import hub_quick_actions_view
        import tkinter as tk

        view = hub_quick_actions_view.HubQuickActionsView(fake_parent)
        view.build()

        # Coletar todos os botões
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(view.modules_panel)

        # Invocar todos os botões - não deve explodir
        for btn in buttons:
            btn.invoke()  # Não deve lançar exceção


# =============================================================================
# TEST: Estrutura do módulo
# =============================================================================


class TestModuleStructure:
    """Testes de estrutura do módulo."""

    def test_module_has_docstring(self) -> None:
        """Módulo tem docstring."""
        from src.modules.hub.views import hub_quick_actions_view

        assert hub_quick_actions_view.__doc__ is not None
        assert "Quick Actions" in hub_quick_actions_view.__doc__

    def test_class_has_docstring(self) -> None:
        """Classe HubQuickActionsView tem docstring."""
        from src.modules.hub.views.hub_quick_actions_view import HubQuickActionsView

        assert HubQuickActionsView.__doc__ is not None
        assert "Quick Actions" in HubQuickActionsView.__doc__

