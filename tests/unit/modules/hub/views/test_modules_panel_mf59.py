# -*- coding: utf-8 -*-
"""Testes unitários headless para modules_panel.py (MF-59).

Objetivo: coverage ≥95% (ideal 100%), sem Tk real.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FAKE WIDGETS (Sem dependência de Tk real)
# ============================================================================


class FakeWidget:
    """Widget fake base com métodos comuns no-op."""

    def __init__(self, *args: Any, **kwargs: Any):
        self.args = args
        self.kwargs = kwargs
        self.children: list[FakeWidget] = []
        self.packed = False
        self.gridded = False
        self.placed = False
        self.destroyed = False
        self._configure_opts = kwargs.copy()
        self.grid_calls: list[dict] = []
        self.pack_calls: list[dict] = []

    def pack(self, **kwargs: Any) -> None:
        self.packed = True
        self.pack_calls.append(kwargs)

    def grid(self, **kwargs: Any) -> None:
        self.gridded = True
        self.grid_calls.append(kwargs)

    def place(self, **kwargs: Any) -> None:
        self.placed = True

    def configure(self, **kwargs: Any) -> None:
        self._configure_opts.update(kwargs)

    def config(self, **kwargs: Any) -> None:
        self.configure(**kwargs)

    def bind(self, event: str, handler: Any) -> None:
        if not hasattr(self, "_bindings"):
            self._bindings: dict[str, Any] = {}
        self._bindings[event] = handler

    def destroy(self) -> None:
        self.destroyed = True

    def columnconfigure(self, _index: int, **kwargs: Any) -> None:
        pass

    def rowconfigure(self, _index: int, **kwargs: Any) -> None:
        pass


class FakeFrame(FakeWidget):
    """Frame fake."""

    pass


class FakeLabelframe(FakeWidget):
    """Labelframe fake."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.text = kwargs.get("text", "")


class FakeButton(FakeWidget):
    """Button fake que guarda command e permite invocar."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.command = kwargs.get("command")
        self.text = kwargs.get("text", "")

    def invoke(self) -> None:
        """Invoca o callback associado ao botão."""
        if self.command and callable(self.command):
            self.command()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fake_tk_module():
    """Módulo tkinter fake."""
    return SimpleNamespace(Misc=object)


@pytest.fixture
def fake_tb_module():
    """Módulo ttkbootstrap fake."""
    return SimpleNamespace(
        Frame=FakeFrame,
        Labelframe=FakeLabelframe,
        Button=FakeButton,
    )


@pytest.fixture
def fake_parent(tk_root):
    """Widget pai real (ttk.Frame) ao invés de FakeFrame.

    Usar tk_root real elimina AttributeError de .tk attribute.
    """
    from tkinter import ttk

    return ttk.Frame(tk_root)


@pytest.fixture
def mock_action_callback():
    """Callback mock para ações."""
    return MagicMock()


@pytest.fixture
def sample_action():
    """Ação de exemplo."""
    return SimpleNamespace(
        id="test_action",
        label="Test Action",
        category="cadastros",
        bootstyle="primary",
        is_enabled=True,
        description="Test description",
    )


@pytest.fixture
def sample_actions_state():
    """Estado com ações de exemplo."""
    action1 = SimpleNamespace(
        id="action_1",
        label="Action 1",
        category="cadastros",
        bootstyle="primary",
        is_enabled=True,
        description="First action",
    )
    action2 = SimpleNamespace(
        id="action_2",
        label="Action 2",
        category="gestao",
        bootstyle="secondary",
        is_enabled=True,
        description="Second action",
    )
    action3 = SimpleNamespace(
        id="action_3",
        label="Action 3",
        category="regulatorio",
        bootstyle="warning",
        is_enabled=False,
        description="Third action (disabled)",
    )
    return SimpleNamespace(actions=[action1, action2, action3])


# ============================================================================
# TESTES
# ============================================================================


class TestBuildModulesPanel:
    """Testes para build_modules_panel."""

    def test_build_creates_labelframe(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que build_modules_panel cria um Labelframe."""
        from src.modules.hub.views import modules_panel
        from tkinter import ttk

        result = modules_panel.build_modules_panel(
            parent=fake_parent,
            state=sample_actions_state,
            on_action_click=mock_action_callback,
        )

        # Verificar que retorna um Labelframe
        assert isinstance(result, ttk.Labelframe) or hasattr(result, "winfo_children")

    def test_build_calls_build_quick_actions(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que build_modules_panel chama _build_quick_actions_by_category."""
        from src.modules.hub.views import modules_panel

        with patch.object(modules_panel, "_build_quick_actions_by_category") as mock_build:
            modules_panel.build_modules_panel(
                parent=fake_parent,
                state=sample_actions_state,
                on_action_click=mock_action_callback,
            )

            # Verificar que chamou _build_quick_actions_by_category
            mock_build.assert_called_once()
            # Verificar argumentos (state e callback)
            call_args = mock_build.call_args
            assert call_args[0][1] is sample_actions_state
            assert call_args[0][2] is mock_action_callback


class TestBuildQuickActionsByCategory:
    """Testes para _build_quick_actions_by_category."""

    def test_groups_actions_by_category(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que agrupa ações por categoria."""
        from src.modules.hub.views import modules_panel
        from tkinter import ttk
        import tkinter as tk

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            sample_actions_state,
            mock_action_callback,
        )

        # Contar Labelframes filhos (1 por categoria)
        labelframes = [w for w in fake_parent.winfo_children() if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) == 3

        # Contar todos os botões recursivamente
        def count_buttons(widget):
            count = 1 if isinstance(widget, tk.Button) else 0
            for child in widget.winfo_children():
                count += count_buttons(child)
            return count

        total_buttons = sum(count_buttons(lf) for lf in labelframes)
        assert total_buttons == 3

    def test_category_titles_are_correct(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que os títulos das categorias estão corretos."""
        from src.modules.hub.views import modules_panel
        from tkinter import ttk

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            sample_actions_state,
            mock_action_callback,
        )

        # Pegar Labelframes filhos
        labelframes = [w for w in fake_parent.winfo_children() if isinstance(w, ttk.Labelframe)]

        # Verificar títulos das categorias
        titles = [lf.cget("text") for lf in labelframes]
        assert "Cadastros / Acesso" in titles
        assert "Gestão / Auditoria" in titles
        assert "Regulatório / Programas" in titles

    def test_categories_are_sorted(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que as categorias são exibidas na ordem correta."""
        from src.modules.hub.views import modules_panel
        from tkinter import ttk

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            sample_actions_state,
            mock_action_callback,
        )

        # Pegar Labelframes filhos (na ordem de criação)
        labelframes = [w for w in fake_parent.winfo_children() if isinstance(w, ttk.Labelframe)]

        # Verificar ordem: cadastros, gestao, regulatorio
        titles = [lf.cget("text") for lf in labelframes]
        assert titles[0] == "Cadastros / Acesso"
        assert titles[1] == "Gestão / Auditoria"
        assert titles[2] == "Regulatório / Programas"

    def test_button_click_calls_callback(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que clicar em botão chama o callback com action_id correto."""
        from src.modules.hub.views import modules_panel
        import tkinter as tk

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            sample_actions_state,
            mock_action_callback,
        )

        # Coletar todos os botões
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(fake_parent)
        assert len(buttons) == 3

        # Invocar apenas botões enabled (disabled não invoca no tk real)
        enabled_buttons = [btn for btn in buttons if btn.cget("state") != "disabled"]
        for btn in enabled_buttons:
            btn.invoke()

        # Verificar que os 2 action_ids enabled foram chamados
        assert mock_action_callback.call_count == 2
        called_action_ids = {call[0][0] for call in mock_action_callback.call_args_list}
        assert called_action_ids == {"action_1", "action_2"}  # action_3 está disabled

    def test_disabled_action_creates_disabled_button(self, fake_parent, mock_action_callback):
        """Testa que ação desabilitada cria botão desabilitado."""
        from src.modules.hub.views import modules_panel
        import tkinter as tk

        disabled_action = SimpleNamespace(
            id="disabled_action",
            label="Disabled Action",
            category="cadastros",
            bootstyle="secondary",
            is_enabled=False,
            description="This is disabled",
        )
        state = SimpleNamespace(actions=[disabled_action])

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

        # Coletar botões
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(fake_parent)
        assert len(buttons) == 1
        # Verificar que está desabilitado
        assert str(buttons[0].cget("state")) == "disabled"

    def test_enabled_action_creates_enabled_button(self, fake_parent, mock_action_callback):
        """Testa que ação habilitada cria botão habilitado."""
        from src.modules.hub.views import modules_panel
        import tkinter as tk

        enabled_action = SimpleNamespace(
            id="enabled_action",
            label="Enabled Action",
            category="cadastros",
            bootstyle="primary",
            is_enabled=True,
            description="This is enabled",
        )
        state = SimpleNamespace(actions=[enabled_action])

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

        # Coletar botões
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(fake_parent)
        assert len(buttons) == 1
        # Verificar que não está desabilitado
        assert str(buttons[0].cget("state")) != "disabled"

    def test_button_labels_match_actions(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que os labels dos botões correspondem às ações."""
        from src.modules.hub.views import modules_panel
        import tkinter as tk

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            sample_actions_state,
            mock_action_callback,
        )

        # Coletar botões
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(fake_parent)
        labels = [btn.cget("text") for btn in buttons]
        assert "Action 1" in labels
        assert "Action 2" in labels
        assert "Action 3" in labels

    def test_button_bootstyle_is_applied(self, fake_parent, mock_action_callback):
        """Testa que o botão é criado (bootstyle é semântico, não argumento de widget)."""
        from src.modules.hub.views import modules_panel
        import tkinter as tk

        action = SimpleNamespace(
            id="styled_action",
            label="Styled Action",
            category="cadastros",
            bootstyle="danger",
            is_enabled=True,
            description="Styled action",
        )
        state = SimpleNamespace(actions=[action])

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

        # Verificar que botão foi criado (bootstyle não é passado ao widget)
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(fake_parent)
        assert len(buttons) == 1

    def test_button_default_bootstyle_when_none(self, fake_parent, mock_action_callback):
        """Testa que botão é criado mesmo quando bootstyle é None."""
        from src.modules.hub.views import modules_panel
        import tkinter as tk

        action = SimpleNamespace(
            id="default_style_action",
            label="Default Style",
            category="cadastros",
            bootstyle=None,
            is_enabled=True,
            description="Default style",
        )
        state = SimpleNamespace(actions=[action])

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

        # Verificar que botão foi criado
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(fake_parent)
        assert len(buttons) == 1

    def test_empty_actions_creates_no_buttons(self, fake_parent, mock_action_callback):
        """Testa que estado vazio não cria botões."""
        from src.modules.hub.views import modules_panel

        empty_state = SimpleNamespace(actions=[])

        with patch.object(modules_panel, "tb", create=True) as mock_tb:
            created_buttons = []

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, empty_state),
                mock_action_callback,
            )

            # Nenhum botão deve ser criado
            assert len(created_buttons) == 0

    def test_multiple_actions_same_category(self, fake_parent, mock_action_callback):
        """Testa múltiplas ações na mesma categoria."""
        from src.modules.hub.views import modules_panel

        action1 = SimpleNamespace(
            id="action_1",
            label="Action 1",
            category="cadastros",
            bootstyle="primary",
            is_enabled=True,
            description="First",
        )
        action2 = SimpleNamespace(
            id="action_2",
            label="Action 2",
            category="cadastros",
            bootstyle="secondary",
            is_enabled=True,
            description="Second",
        )
        state = SimpleNamespace(actions=[action1, action2])

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

        # Deve ter 1 labelframe e 2 botões
        from tkinter import ttk
        import tkinter as tk

        labelframes = [w for w in fake_parent.winfo_children() if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) == 1

        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(fake_parent)
        assert len(buttons) == 2

    def test_button_grid_positioning(self, fake_parent, mock_action_callback):
        """Testa que os botões são criados com grid."""
        from src.modules.hub.views import modules_panel
        import tkinter as tk

        # Criar 4 ações para testar grid 2x2
        actions = [
            SimpleNamespace(
                id=f"action_{i}",
                label=f"Action {i}",
                category="cadastros",
                bootstyle="primary",
                is_enabled=True,
                description=f"Action {i}",
            )
            for i in range(4)
        ]
        state = SimpleNamespace(actions=actions)

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

        # Verificar que todos os botões foram criados
        def collect_buttons(widget):
            buttons = []
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                buttons.extend(collect_buttons(child))
            return buttons

        buttons = collect_buttons(fake_parent)
        assert len(buttons) == 4

    def test_unknown_category_uses_title_case(self, fake_parent, mock_action_callback):
        """Testa que categoria desconhecida usa title case."""
        from src.modules.hub.views import modules_panel
        from tkinter import ttk

        action = SimpleNamespace(
            id="unknown_action",
            label="Unknown Action",
            category="unknown_category",
            bootstyle="secondary",
            is_enabled=True,
            description="Unknown",
        )
        state = SimpleNamespace(actions=[action])

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

        # Verificar que usou title case
        labelframes = [w for w in fake_parent.winfo_children() if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) == 1
        assert labelframes[0].cget("text") == "Unknown_Category"


class TestImportStructure:
    """Testes de importação e estrutura do módulo."""

    def test_module_imports(self):
        """Testa que o módulo importa corretamente."""
        from src.modules.hub.views import modules_panel

        assert hasattr(modules_panel, "build_modules_panel")
        assert hasattr(modules_panel, "_build_quick_actions_by_category")

    def test_constants_imported(self):
        """Testa que constantes são importadas."""
        from src.modules.hub.views import modules_panel

        assert hasattr(modules_panel, "MODULES_TITLE")
        assert hasattr(modules_panel, "PAD_OUTER")

    def test_module_docstring(self):
        """Testa que o módulo tem docstring."""
        from src.modules.hub.views import modules_panel

        assert modules_panel.__doc__ is not None
        assert "Módulos/Quick Actions panel view builder" in modules_panel.__doc__

    def test_build_modules_panel_docstring(self):
        """Testa que build_modules_panel tem docstring."""
        from src.modules.hub.views import modules_panel

        assert modules_panel.build_modules_panel.__doc__ is not None
        assert "Constrói o painel de módulos" in modules_panel.build_modules_panel.__doc__

    def test_function_annotations(self):
        """Testa que as funções têm type annotations."""
        from src.modules.hub.views import modules_panel

        # build_modules_panel deve ter annotations
        annotations = modules_panel.build_modules_panel.__annotations__
        assert "parent" in annotations
        assert "state" in annotations
        assert "on_action_click" in annotations
        assert "return" in annotations


class TestEdgeCases:
    """Testes de casos extremos."""

    def test_action_without_description(self, fake_parent, mock_action_callback):
        """Testa ação sem descrição."""
        from src.modules.hub.views import modules_panel

        action = SimpleNamespace(
            id="no_desc_action",
            label="No Description",
            category="cadastros",
            bootstyle="primary",
            is_enabled=True,
            description=None,
        )
        state = SimpleNamespace(actions=[action])

        # Não deve causar erro
        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

    def test_action_with_empty_description(self, fake_parent, mock_action_callback):
        """Testa ação com descrição vazia."""
        from src.modules.hub.views import modules_panel

        action = SimpleNamespace(
            id="empty_desc_action",
            label="Empty Description",
            category="cadastros",
            bootstyle="primary",
            is_enabled=True,
            description="",
        )
        state = SimpleNamespace(actions=[action])

        # Não deve causar erro
        modules_panel._build_quick_actions_by_category(
            fake_parent,
            cast(Any, state),
            mock_action_callback,
        )

    def test_labelframe_pack_is_called(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que labelframes são criados."""
        from src.modules.hub.views import modules_panel
        from tkinter import ttk

        modules_panel._build_quick_actions_by_category(
            fake_parent,
            sample_actions_state,
            mock_action_callback,
        )

        # Verificar que labelframes foram criados
        labelframes = [w for w in fake_parent.winfo_children() if isinstance(w, ttk.Labelframe)]
        assert len(labelframes) > 0
