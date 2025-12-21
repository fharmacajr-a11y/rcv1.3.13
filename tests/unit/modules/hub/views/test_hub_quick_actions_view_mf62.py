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
def fake_parent() -> FakeWidget:
    """Parent fake para testes."""
    return FakeWidget()


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
        self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """build() cria modules_panel e retorna ele."""
        from src.modules.hub.views import hub_quick_actions_view

        # Patch tb e constants
        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
            result = view.build()

            assert result is view.modules_panel
            assert view.modules_panel is not None
            assert isinstance(view.modules_panel, FakeLabelframe)

    def test_build_panel_has_correct_title_and_padding(
        self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """build() cria painel principal com título e padding corretos."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
            view.build()

            panel = cast(Any, view.modules_panel)
            assert panel.kwargs["text"] == "TITLE-X"
            assert panel.kwargs["padding"] == ("PAD",)

    def test_build_creates_three_blocks(self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]) -> None:
        """build() cria 3 blocos de botões (Labelframes filhos)."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
            view.build()

            # Encontrar labelframes filhos (exceto o principal)
            all_lfs = find_labelframes(cast(Any, view.modules_panel))
            # Remove o próprio modules_panel da lista
            child_lfs = [lf for lf in all_lfs if lf is not view.modules_panel]

            assert len(child_lfs) == 3

            # Verificar textos dos blocos
            block_texts = sorted([lf.text for lf in child_lfs])
            expected_texts = sorted(["Cadastros / Acesso", "Gestão / Auditoria", "Regulatório / Programas"])
            assert block_texts == expected_texts

    def test_build_blocks_have_correct_bootstyle_and_padding(
        self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """build() cria blocos com bootstyle='dark' e padding=(8, 6)."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
            view.build()

            all_lfs = find_labelframes(cast(Any, view.modules_panel))
            child_lfs = [lf for lf in all_lfs if lf is not view.modules_panel]

            for lf in child_lfs:
                assert lf.kwargs.get("bootstyle") == "dark"
                assert lf.kwargs.get("padding") == (8, 6)


# =============================================================================
# TEST: Botões
# =============================================================================


class TestButtons:
    """Testes dos botões criados."""

    def test_build_creates_eight_buttons(self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]) -> None:
        """build() cria exatamente 8 botões."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
            view.build()

            buttons = find_buttons(cast(Any, view.modules_panel))
            assert len(buttons) == 8

    def test_button_texts_are_correct(self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]) -> None:
        """build() cria botões com textos corretos."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
            view.build()

            buttons = find_buttons(cast(Any, view.modules_panel))
            button_texts = sorted([btn.text for btn in buttons])
            expected_texts = sorted(
                [
                    "Clientes",
                    "Senhas",
                    "Auditoria",
                    "Fluxo de Caixa",
                    "Anvisa",
                    "Farmácia Popular",
                    "Sngpc",
                    "Sifap",
                ]
            )
            assert button_texts == expected_texts

    def test_button_bootstyles_are_correct(self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]) -> None:
        """build() aplica bootstyles corretos aos botões."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
            view.build()

            buttons = find_buttons(cast(Any, view.modules_panel))

            # Criar dicionário text -> bootstyle
            btn_styles = {btn.text: btn.kwargs.get("bootstyle") for btn in buttons}

            # Verificar bootstyles
            assert btn_styles["Clientes"] == "STYLE_CLIENTES"
            assert btn_styles["Senhas"] == "STYLE_SENHAS"
            assert btn_styles["Auditoria"] == "STYLE_AUD"
            assert btn_styles["Fluxo de Caixa"] == "STYLE_FLUXO"
            assert btn_styles["Anvisa"] == "secondary"
            assert btn_styles["Farmácia Popular"] == "secondary"
            assert btn_styles["Sngpc"] == "secondary"
            assert btn_styles["Sifap"] == "secondary"

    def test_button_invoke_calls_correct_callback(
        self, fake_parent: FakeWidget, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """invoke() em cada botão chama callback correto exatamente 1x."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent, **mock_callbacks)
            view.build()

            buttons = find_buttons(cast(Any, view.modules_panel))

            # Mapeamento text -> callback esperado
            text_to_callback = {
                "Clientes": mock_callbacks["on_open_clientes"],
                "Senhas": mock_callbacks["on_open_senhas"],
                "Auditoria": mock_callbacks["on_open_auditoria"],
                "Fluxo de Caixa": mock_callbacks["on_open_cashflow"],
                "Anvisa": mock_callbacks["on_open_anvisa"],
                "Farmácia Popular": mock_callbacks["on_open_farmacia_popular"],
                "Sngpc": mock_callbacks["on_open_sngpc"],
                "Sifap": mock_callbacks["on_open_mod_sifap"],
            }

            # Testar cada botão
            for btn in buttons:
                expected_callback = text_to_callback[btn.text]
                btn.invoke()
                expected_callback.assert_called_once()


# =============================================================================
# TEST: Callbacks None
# =============================================================================


class TestCallbacksNone:
    """Testes com callbacks None."""

    def test_build_with_all_callbacks_none_creates_buttons(self, fake_parent: FakeWidget) -> None:
        """build() com todos callbacks None ainda cria os botões."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent)
            view.build()

            buttons = find_buttons(cast(Any, view.modules_panel))
            assert len(buttons) == 8

            # Verificar que todos têm command None
            for btn in buttons:
                assert btn.command is None

    def test_invoke_with_none_callback_does_not_crash(self, fake_parent: FakeWidget) -> None:
        """invoke() em botões com callback None não explode."""
        from src.modules.hub.views import hub_quick_actions_view

        with (
            patch.object(hub_quick_actions_view, "tb") as mock_tb,
            patch("src.modules.hub.constants.MODULES_TITLE", "TITLE-X"),
            patch("src.modules.hub.constants.PAD_OUTER", ("PAD",)),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_CLIENTES", "STYLE_CLIENTES"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_SENHAS", "STYLE_SENHAS"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_AUDITORIA", "STYLE_AUD"),
            patch("src.modules.hub.constants.HUB_BTN_STYLE_FLUXO_CAIXA", "STYLE_FLUXO"),
        ):
            mock_tb.Labelframe = FakeLabelframe
            mock_tb.Button = FakeButton

            view = hub_quick_actions_view.HubQuickActionsView(fake_parent)
            view.build()

            buttons = find_buttons(cast(Any, view.modules_panel))

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
