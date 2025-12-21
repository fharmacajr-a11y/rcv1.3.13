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
def fake_parent():
    """Widget pai fake."""
    return FakeFrame()


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

        with patch.object(modules_panel, "tb") as mock_tb:
            mock_panel = FakeLabelframe()
            mock_labelframe_constructor = MagicMock(return_value=mock_panel)
            mock_tb.Labelframe = mock_labelframe_constructor

            with patch.object(modules_panel, "_build_quick_actions_by_category"):
                result = modules_panel.build_modules_panel(
                    parent=fake_parent,
                    state=sample_actions_state,
                    on_action_click=mock_action_callback,
                )

                # Verificar que criou labelframe
                mock_labelframe_constructor.assert_called_once()
                assert result is mock_panel

    def test_build_calls_build_quick_actions(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que build_modules_panel chama _build_quick_actions_by_category."""
        from src.modules.hub.views import modules_panel

        with patch.object(modules_panel, "tb") as mock_tb:
            mock_panel = FakeLabelframe()
            mock_tb.Labelframe.return_value = mock_panel

            with patch.object(modules_panel, "_build_quick_actions_by_category") as mock_build:
                result = modules_panel.build_modules_panel(
                    parent=fake_parent,
                    state=sample_actions_state,
                    on_action_click=mock_action_callback,
                )

                # Verificar que chamou _build_quick_actions_by_category
                mock_build.assert_called_once_with(
                    mock_panel,
                    sample_actions_state,
                    mock_action_callback,
                )
                assert result is mock_panel


class TestBuildQuickActionsByCategory:
    """Testes para _build_quick_actions_by_category."""

    def test_groups_actions_by_category(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que agrupa ações por categoria."""
        from src.modules.hub.views import modules_panel

        # Patch ttkbootstrap
        with patch.object(modules_panel, "tb") as mock_tb:
            created_labelframes = []
            created_buttons = []

            def create_labelframe(*args, **kwargs):
                lf = FakeLabelframe(*args, **kwargs)
                created_labelframes.append(lf)
                return lf

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.side_effect = create_labelframe
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                sample_actions_state,
                mock_action_callback,
            )

            # Verificar que criou 3 labelframes (1 por categoria)
            assert len(created_labelframes) == 3

            # Verificar que criou 3 botões (1 por ação)
            assert len(created_buttons) == 3

    def test_category_titles_are_correct(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que os títulos das categorias estão corretos."""
        from src.modules.hub.views import modules_panel

        with patch.object(modules_panel, "tb") as mock_tb:
            created_labelframes = []

            def create_labelframe(*args, **kwargs):
                lf = FakeLabelframe(*args, **kwargs)
                created_labelframes.append(lf)
                return lf

            mock_tb.Labelframe.side_effect = create_labelframe
            mock_tb.Button.return_value = FakeButton()

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                sample_actions_state,
                mock_action_callback,
            )

            # Verificar títulos das categorias
            titles = [lf.text for lf in created_labelframes]
            assert "Cadastros / Acesso" in titles
            assert "Gestão / Auditoria" in titles
            assert "Regulatório / Programas" in titles

    def test_categories_are_sorted(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que as categorias são exibidas na ordem correta."""
        from src.modules.hub.views import modules_panel

        with patch.object(modules_panel, "tb") as mock_tb:
            created_labelframes = []

            def create_labelframe(*args, **kwargs):
                lf = FakeLabelframe(*args, **kwargs)
                created_labelframes.append(lf)
                return lf

            mock_tb.Labelframe.side_effect = create_labelframe
            mock_tb.Button.return_value = FakeButton()

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                sample_actions_state,
                mock_action_callback,
            )

            # Verificar ordem: cadastros, gestao, regulatorio
            titles = [lf.text for lf in created_labelframes]
            assert titles[0] == "Cadastros / Acesso"
            assert titles[1] == "Gestão / Auditoria"
            assert titles[2] == "Regulatório / Programas"

    def test_button_click_calls_callback(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que clicar em botão chama o callback com action_id correto."""
        from src.modules.hub.views import modules_panel

        with patch.object(modules_panel, "tb") as mock_tb:
            created_buttons = []

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                sample_actions_state,
                mock_action_callback,
            )

            # Invocar cada botão e verificar callback
            assert len(created_buttons) == 3

            created_buttons[0].invoke()
            mock_action_callback.assert_called_with("action_1")

            created_buttons[1].invoke()
            mock_action_callback.assert_called_with("action_2")

            created_buttons[2].invoke()
            mock_action_callback.assert_called_with("action_3")

    def test_disabled_action_creates_disabled_button(self, fake_parent, mock_action_callback):
        """Testa que ação desabilitada cria botão desabilitado."""
        from src.modules.hub.views import modules_panel

        disabled_action = SimpleNamespace(
            id="disabled_action",
            label="Disabled Action",
            category="cadastros",
            bootstyle="secondary",
            is_enabled=False,
            description="This is disabled",
        )
        state = SimpleNamespace(actions=[disabled_action])

        with patch.object(modules_panel, "tb") as mock_tb:
            created_buttons = []

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, state),
                mock_action_callback,
            )

            # Verificar que o botão foi desabilitado
            assert len(created_buttons) == 1
            btn = created_buttons[0]
            assert btn._configure_opts.get("state") == "disabled"

    def test_enabled_action_creates_enabled_button(self, fake_parent, mock_action_callback):
        """Testa que ação habilitada cria botão habilitado."""
        from src.modules.hub.views import modules_panel

        enabled_action = SimpleNamespace(
            id="enabled_action",
            label="Enabled Action",
            category="cadastros",
            bootstyle="primary",
            is_enabled=True,
            description="This is enabled",
        )
        state = SimpleNamespace(actions=[enabled_action])

        with patch.object(modules_panel, "tb") as mock_tb:
            created_buttons = []

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, state),
                mock_action_callback,
            )

            # Verificar que o botão não foi explicitamente desabilitado
            assert len(created_buttons) == 1
            btn = created_buttons[0]
            # Se is_enabled=True, não deve ter state="disabled"
            assert btn._configure_opts.get("state") != "disabled"

    def test_button_labels_match_actions(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que os labels dos botões correspondem às ações."""
        from src.modules.hub.views import modules_panel

        with patch.object(modules_panel, "tb") as mock_tb:
            created_buttons = []

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                sample_actions_state,
                mock_action_callback,
            )

            # Verificar labels
            labels = [btn.text for btn in created_buttons]
            assert "Action 1" in labels
            assert "Action 2" in labels
            assert "Action 3" in labels

    def test_button_bootstyle_is_applied(self, fake_parent, mock_action_callback):
        """Testa que o bootstyle é aplicado aos botões."""
        from src.modules.hub.views import modules_panel

        action = SimpleNamespace(
            id="styled_action",
            label="Styled Action",
            category="cadastros",
            bootstyle="danger",
            is_enabled=True,
            description="Styled action",
        )
        state = SimpleNamespace(actions=[action])

        with patch.object(modules_panel, "tb") as mock_tb:
            created_buttons = []

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, state),
                mock_action_callback,
            )

            # Verificar que bootstyle foi passado
            assert len(created_buttons) == 1
            assert created_buttons[0].kwargs.get("bootstyle") == "danger"

    def test_button_default_bootstyle_when_none(self, fake_parent, mock_action_callback):
        """Testa que bootstyle padrão é 'secondary' quando None."""
        from src.modules.hub.views import modules_panel

        action = SimpleNamespace(
            id="default_style_action",
            label="Default Style",
            category="cadastros",
            bootstyle=None,
            is_enabled=True,
            description="Default style",
        )
        state = SimpleNamespace(actions=[action])

        with patch.object(modules_panel, "tb") as mock_tb:
            created_buttons = []

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, state),
                mock_action_callback,
            )

            # Verificar que usou bootstyle padrão
            assert len(created_buttons) == 1
            assert created_buttons[0].kwargs.get("bootstyle") == "secondary"

    def test_empty_actions_creates_no_buttons(self, fake_parent, mock_action_callback):
        """Testa que estado vazio não cria botões."""
        from src.modules.hub.views import modules_panel

        empty_state = SimpleNamespace(actions=[])

        with patch.object(modules_panel, "tb") as mock_tb:
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

        with patch.object(modules_panel, "tb") as mock_tb:
            created_labelframes = []
            created_buttons = []

            def create_labelframe(*args, **kwargs):
                lf = FakeLabelframe(*args, **kwargs)
                created_labelframes.append(lf)
                return lf

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.side_effect = create_labelframe
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, state),
                mock_action_callback,
            )

            # Deve ter 1 labelframe e 2 botões
            assert len(created_labelframes) == 1
            assert len(created_buttons) == 2

    def test_button_grid_positioning(self, fake_parent, mock_action_callback):
        """Testa que os botões são posicionados em grid corretamente."""
        from src.modules.hub.views import modules_panel

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

        with patch.object(modules_panel, "tb") as mock_tb:
            created_buttons = []

            def create_button(*args, **kwargs):
                btn = FakeButton(*args, **kwargs)
                created_buttons.append(btn)
                return btn

            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.side_effect = create_button

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, state),
                mock_action_callback,
            )

            # Verificar que todos os botões foram "gridados"
            assert len(created_buttons) == 4
            for btn in created_buttons:
                assert btn.gridded
                assert len(btn.grid_calls) > 0

    def test_unknown_category_uses_title_case(self, fake_parent, mock_action_callback):
        """Testa que categoria desconhecida usa title case."""
        from src.modules.hub.views import modules_panel

        action = SimpleNamespace(
            id="unknown_action",
            label="Unknown Action",
            category="unknown_category",
            bootstyle="secondary",
            is_enabled=True,
            description="Unknown",
        )
        state = SimpleNamespace(actions=[action])

        with patch.object(modules_panel, "tb") as mock_tb:
            created_labelframes = []

            def create_labelframe(*args, **kwargs):
                lf = FakeLabelframe(*args, **kwargs)
                created_labelframes.append(lf)
                return lf

            mock_tb.Labelframe.side_effect = create_labelframe
            mock_tb.Button.return_value = FakeButton()

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, state),
                mock_action_callback,
            )

            # Verificar que usou title case
            assert len(created_labelframes) == 1
            assert created_labelframes[0].text == "Unknown_Category"


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

        with patch.object(modules_panel, "tb") as mock_tb:
            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.return_value = FakeButton()

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

        with patch.object(modules_panel, "tb") as mock_tb:
            mock_tb.Labelframe.return_value = FakeLabelframe()
            mock_tb.Button.return_value = FakeButton()

            # Não deve causar erro
            modules_panel._build_quick_actions_by_category(
                fake_parent,
                cast(Any, state),
                mock_action_callback,
            )

    def test_labelframe_pack_is_called(self, fake_parent, sample_actions_state, mock_action_callback):
        """Testa que labelframes são empacotados."""
        from src.modules.hub.views import modules_panel

        with patch.object(modules_panel, "tb") as mock_tb:
            created_labelframes = []

            def create_labelframe(*args, **kwargs):
                lf = FakeLabelframe(*args, **kwargs)
                created_labelframes.append(lf)
                return lf

            mock_tb.Labelframe.side_effect = create_labelframe
            mock_tb.Button.return_value = FakeButton()

            modules_panel._build_quick_actions_by_category(
                fake_parent,
                sample_actions_state,
                mock_action_callback,
            )

            # Verificar que todos os labelframes foram empacotados
            for lf in created_labelframes:
                assert lf.packed
                assert len(lf.pack_calls) > 0
