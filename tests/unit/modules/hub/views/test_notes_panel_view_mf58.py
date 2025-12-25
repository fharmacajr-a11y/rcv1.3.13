# -*- coding: utf-8 -*-
"""Testes unitários headless para notes_panel_view.py (MF-58).

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

    def pack(self, **kwargs: Any) -> None:
        self.packed = True
        self.pack_info_data = kwargs

    def grid(self, **kwargs: Any) -> None:
        self.gridded = True
        self.grid_info_data = kwargs

    def place(self, **kwargs: Any) -> None:
        self.placed = True
        self.place_info_data = kwargs

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

    def columnconfigure(self, index: int, **kwargs: Any) -> None:
        pass

    def rowconfigure(self, index: int, **kwargs: Any) -> None:
        pass


class FakeFrame(FakeWidget):
    """Frame fake."""

    pass


class FakeLabelframe(FakeWidget):
    """Labelframe fake."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        # Simulate storing widgets as attributes
        self.notes_history = None
        self.new_note = None
        self.btn_add_note = None


class FakeButton(FakeWidget):
    """Button fake que guarda command e permite invocar."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.command = kwargs.get("command")

    def invoke(self) -> None:
        """Invoca o callback associado ao botão."""
        if self.command and callable(self.command):
            self.command()


class FakeText(FakeWidget):
    """Text fake que guarda conteúdo."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.content = ""
        self.state_value = kwargs.get("state", "normal")
        self.tag_configs: dict[str, dict[str, str]] = {}

    def insert(self, index: str, text: str, *tags: str) -> None:
        """Simula inserção de texto."""
        if self.state_value == "disabled":
            # Tk real não permite insert quando disabled
            raise RuntimeError("Text widget is disabled")
        self.content += text

    def delete(self, start: str, end: str) -> None:
        """Simula remoção de texto."""
        if self.state_value == "disabled":
            raise RuntimeError("Text widget is disabled")
        self.content = ""

    def get(self, start: str, end: str) -> str:
        """Simula obtenção de texto."""
        return self.content

    def configure(self, **kwargs: Any) -> None:
        """Atualiza configuração (ex: state)."""
        super().configure(**kwargs)
        if "state" in kwargs:
            self.state_value = kwargs["state"]

    def tag_configure(self, tag_name: str, **kwargs: Any) -> None:
        """Simula configuração de tag."""
        if tag_name not in self.tag_configs:
            self.tag_configs[tag_name] = {}
        self.tag_configs[tag_name].update(kwargs)

    def tag_cget(self, tag_name: str, option: str) -> str:
        """Simula obtenção de config de tag."""
        return self.tag_configs.get(tag_name, {}).get(option, "")


class FakeScrollbar(FakeWidget):
    """Scrollbar fake."""

    pass


class FakeLabel(FakeWidget):
    """Label fake."""

    pass


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fake_tk_module():
    """Módulo tkinter fake."""
    return SimpleNamespace(Text=FakeText)


@pytest.fixture
def fake_tb_module():
    """Módulo ttkbootstrap fake."""
    return SimpleNamespace(
        Frame=FakeFrame,
        Labelframe=FakeLabelframe,
        Button=FakeButton,
        Scrollbar=FakeScrollbar,
        Label=FakeLabel,
    )


@pytest.fixture
def fake_parent():
    """Frame pai fake."""
    return FakeFrame()


@pytest.fixture
def mock_callbacks():
    """Callbacks mock."""
    return SimpleNamespace(
        on_add_note_click=MagicMock(),
        on_edit_note_click=MagicMock(),
        on_delete_note_click=MagicMock(),
        on_toggle_pin_click=MagicMock(),
        on_toggle_done_click=MagicMock(),
    )


@pytest.fixture
def fake_notes_state():
    """Estado de notas fake."""
    note1 = SimpleNamespace(
        note_id="n1",
        body="Test note",
        author_name="Alice",
        author_email="alice@test.com",
        created_at="2025-12-16 10:00",
        formatted_line="[2025-12-16 10:00] Alice: Test note",
        tag_name="alice@test.com",
    )
    note2 = SimpleNamespace(
        note_id="n2",
        body="Another note",
        author_name="Bob",
        author_email="bob@test.com",
        created_at="2025-12-16 11:00",
        formatted_line="[2025-12-16 11:00] Bob: Another note",
        tag_name="bob@test.com",
    )
    return SimpleNamespace(
        notes=[note1, note2],
        is_loading=False,
        error_message=None,
    )


# ============================================================================
# TESTES
# ============================================================================


class TestNotesViewCallbacks:
    """Testes para NotesViewCallbacks."""

    def test_init_all_callbacks(self):
        """Testa inicialização com todos os callbacks."""
        from src.modules.hub.views import notes_panel_view

        cb_add = MagicMock()
        cb_edit = MagicMock()
        cb_delete = MagicMock()
        cb_pin = MagicMock()
        cb_done = MagicMock()

        callbacks = notes_panel_view.NotesViewCallbacks(
            on_add_note_click=cb_add,
            on_edit_note_click=cb_edit,
            on_delete_note_click=cb_delete,
            on_toggle_pin_click=cb_pin,
            on_toggle_done_click=cb_done,
        )

        assert callbacks.on_add_note_click is cb_add
        assert callbacks.on_edit_note_click is cb_edit
        assert callbacks.on_delete_note_click is cb_delete
        assert callbacks.on_toggle_pin_click is cb_pin
        assert callbacks.on_toggle_done_click is cb_done

    def test_init_no_callbacks(self):
        """Testa inicialização sem callbacks (todos None)."""
        from src.modules.hub.views import notes_panel_view

        callbacks = notes_panel_view.NotesViewCallbacks()

        assert callbacks.on_add_note_click is None
        assert callbacks.on_edit_note_click is None
        assert callbacks.on_delete_note_click is None
        assert callbacks.on_toggle_pin_click is None
        assert callbacks.on_toggle_done_click is None

    def test_init_partial_callbacks(self):
        """Testa inicialização com callbacks parciais."""
        from src.modules.hub.views import notes_panel_view

        cb_add = MagicMock()
        cb_edit = MagicMock()

        callbacks = notes_panel_view.NotesViewCallbacks(
            on_add_note_click=cb_add,
            on_edit_note_click=cb_edit,
        )

        assert callbacks.on_add_note_click is cb_add
        assert callbacks.on_edit_note_click is cb_edit
        assert callbacks.on_delete_note_click is None
        assert callbacks.on_toggle_pin_click is None
        assert callbacks.on_toggle_done_click is None


class TestBuildNotesSidePanel:
    """Testes para build_notes_side_panel."""

    def test_build_delegates_to_build_notes_panel(self, fake_parent, fake_notes_state, mock_callbacks):
        """Testa que build_notes_side_panel delega para build_notes_panel."""
        from src.modules.hub.views import notes_panel_view

        # Criar callbacks reais
        callbacks = notes_panel_view.NotesViewCallbacks(
            on_add_note_click=mock_callbacks.on_add_note_click,
            on_edit_note_click=mock_callbacks.on_edit_note_click,
            on_delete_note_click=mock_callbacks.on_delete_note_click,
            on_toggle_pin_click=mock_callbacks.on_toggle_pin_click,
            on_toggle_done_click=mock_callbacks.on_toggle_done_click,
        )

        # Mock build_notes_panel
        mock_panel = FakeLabelframe()
        with patch(
            "src.modules.hub.views.notes_panel_view.build_notes_panel",
            return_value=mock_panel,
        ) as mock_build:
            result = notes_panel_view.build_notes_side_panel(
                parent=fake_parent,
                state=fake_notes_state,
                callbacks=callbacks,
            )

            # Verificar que build_notes_panel foi chamado corretamente
            mock_build.assert_called_once_with(
                parent_frame=fake_parent,
                state=fake_notes_state,
                on_add_note_click=mock_callbacks.on_add_note_click,
                on_edit_note_click=mock_callbacks.on_edit_note_click,
                on_delete_note_click=mock_callbacks.on_delete_note_click,
                on_toggle_pin_click=mock_callbacks.on_toggle_pin_click,
                on_toggle_done_click=mock_callbacks.on_toggle_done_click,
                current_user_email=None,  # Parâmetro adicionado ao build_notes_panel
            )

            # Verificar que retornou o painel
            assert result is mock_panel

    def test_build_with_none_callbacks(self, fake_parent, fake_notes_state):
        """Testa build com callbacks None."""
        from src.modules.hub.views import notes_panel_view

        callbacks = notes_panel_view.NotesViewCallbacks()

        mock_panel = FakeLabelframe()
        with patch(
            "src.modules.hub.views.notes_panel_view.build_notes_panel",
            return_value=mock_panel,
        ) as mock_build:
            result = notes_panel_view.build_notes_side_panel(
                parent=fake_parent,
                state=fake_notes_state,
                callbacks=callbacks,
            )

            # Verificar que build_notes_panel foi chamado com callbacks None
            mock_build.assert_called_once_with(
                parent_frame=fake_parent,
                state=fake_notes_state,
                on_add_note_click=None,
                on_edit_note_click=None,
                on_delete_note_click=None,
                on_toggle_pin_click=None,
                on_toggle_done_click=None,
                current_user_email=None,  # Parâmetro adicionado ao build_notes_panel
            )

            assert result is mock_panel


class TestImportStructure:
    """Testes de importação e estrutura do módulo."""

    def test_module_imports(self):
        """Testa que o módulo importa corretamente."""
        from src.modules.hub.views import notes_panel_view

        # Verificar atributos principais
        assert hasattr(notes_panel_view, "NotesViewCallbacks")
        assert hasattr(notes_panel_view, "build_notes_side_panel")
        assert hasattr(notes_panel_view, "build_notes_panel")

    def test_type_checking_imports(self):
        """Testa que TYPE_CHECKING imports não quebram em runtime."""
        from src.modules.hub.views import notes_panel_view

        # NotesViewState só deve estar disponível durante type checking
        # Em runtime, não deve causar erro
        assert notes_panel_view.__name__ == "src.modules.hub.views.notes_panel_view"

    def test_callbacks_class_attributes(self):
        """Testa que NotesViewCallbacks tem os atributos esperados."""
        from src.modules.hub.views import notes_panel_view

        callbacks = notes_panel_view.NotesViewCallbacks()

        # Verificar que tem os 5 atributos de callback
        expected_attrs = [
            "on_add_note_click",
            "on_edit_note_click",
            "on_delete_note_click",
            "on_toggle_pin_click",
            "on_toggle_done_click",
        ]

        for attr in expected_attrs:
            assert hasattr(callbacks, attr), f"Missing attribute: {attr}"


class TestCallbacksEdgeCases:
    """Testes de edge cases para callbacks."""

    def test_callbacks_with_lambda(self):
        """Testa callbacks com funções lambda."""
        from src.modules.hub.views import notes_panel_view

        lambda_add = lambda: None  # noqa: E731
        lambda_edit = lambda note_id: None  # noqa: E731

        callbacks = notes_panel_view.NotesViewCallbacks(
            on_add_note_click=lambda_add,
            on_edit_note_click=lambda_edit,
        )

        assert callbacks.on_add_note_click is lambda_add
        assert callbacks.on_edit_note_click is lambda_edit

    def test_callbacks_with_regular_functions(self):
        """Testa callbacks com funções regulares."""
        from src.modules.hub.views import notes_panel_view

        def add_handler():
            pass

        def edit_handler(note_id: str):
            pass

        callbacks = notes_panel_view.NotesViewCallbacks(
            on_add_note_click=add_handler,
            on_edit_note_click=edit_handler,
        )

        assert callbacks.on_add_note_click is add_handler
        assert callbacks.on_edit_note_click is edit_handler


class TestBuildIntegrationScenarios:
    """Testes de cenários de integração."""

    def test_build_with_empty_state(self, fake_parent):
        """Testa build com estado vazio."""
        from src.modules.hub.views import notes_panel_view

        empty_state = SimpleNamespace(
            notes=[],
            is_loading=False,
            error_message=None,
        )

        callbacks = notes_panel_view.NotesViewCallbacks()
        mock_panel = FakeLabelframe()

        with patch(
            "src.modules.hub.views.notes_panel_view.build_notes_panel",
            return_value=mock_panel,
        ) as mock_build:
            result = notes_panel_view.build_notes_side_panel(
                parent=fake_parent,
                state=cast(Any, empty_state),
                callbacks=callbacks,
            )

            mock_build.assert_called_once()
            assert result is mock_panel

    def test_build_with_loading_state(self, fake_parent):
        """Testa build com estado de carregamento."""
        from src.modules.hub.views import notes_panel_view

        loading_state = SimpleNamespace(
            notes=[],
            is_loading=True,
            error_message=None,
        )

        callbacks = notes_panel_view.NotesViewCallbacks()
        mock_panel = FakeLabelframe()

        with patch(
            "src.modules.hub.views.notes_panel_view.build_notes_panel",
            return_value=mock_panel,
        ) as mock_build:
            result = notes_panel_view.build_notes_side_panel(
                parent=fake_parent,
                state=cast(Any, loading_state),
                callbacks=callbacks,
            )

            mock_build.assert_called_once()
            assert result is mock_panel

    def test_build_with_error_state(self, fake_parent):
        """Testa build com estado de erro."""
        from src.modules.hub.views import notes_panel_view

        error_state = SimpleNamespace(
            notes=[],
            is_loading=False,
            error_message="Falha ao carregar notas",
        )

        callbacks = notes_panel_view.NotesViewCallbacks()
        mock_panel = FakeLabelframe()

        with patch(
            "src.modules.hub.views.notes_panel_view.build_notes_panel",
            return_value=mock_panel,
        ) as mock_build:
            result = notes_panel_view.build_notes_side_panel(
                parent=fake_parent,
                state=cast(Any, error_state),
                callbacks=callbacks,
            )

            mock_build.assert_called_once()
            assert result is mock_panel

    def test_build_multiple_calls(self, fake_parent, fake_notes_state):
        """Testa múltiplas chamadas a build_notes_side_panel."""
        from src.modules.hub.views import notes_panel_view

        callbacks = notes_panel_view.NotesViewCallbacks()

        with patch(
            "src.modules.hub.views.notes_panel_view.build_notes_panel",
            return_value=FakeLabelframe(),
        ) as mock_build:
            # Primeira chamada
            result1 = notes_panel_view.build_notes_side_panel(
                parent=fake_parent,
                state=fake_notes_state,
                callbacks=callbacks,
            )

            # Segunda chamada
            result2 = notes_panel_view.build_notes_side_panel(
                parent=fake_parent,
                state=fake_notes_state,
                callbacks=callbacks,
            )

            # Verificar que foi chamado 2 vezes
            assert mock_build.call_count == 2
            assert result1 is not None
            assert result2 is not None


class TestDocstringsAndAnnotations:
    """Testes de documentação e anotações."""

    def test_module_docstring(self):
        """Testa que o módulo tem docstring."""
        from src.modules.hub.views import notes_panel_view

        assert notes_panel_view.__doc__ is not None
        assert "Notes panel view builder" in notes_panel_view.__doc__

    def test_callbacks_class_docstring(self):
        """Testa que NotesViewCallbacks tem docstring."""
        from src.modules.hub.views import notes_panel_view

        assert notes_panel_view.NotesViewCallbacks.__doc__ is not None
        assert "Container para callbacks" in notes_panel_view.NotesViewCallbacks.__doc__

    def test_build_function_docstring(self):
        """Testa que build_notes_side_panel tem docstring."""
        from src.modules.hub.views import notes_panel_view

        assert notes_panel_view.build_notes_side_panel.__doc__ is not None
        assert "Constrói o painel de notas" in notes_panel_view.build_notes_side_panel.__doc__

    def test_function_annotations(self):
        """Testa que as funções têm type annotations."""
        from src.modules.hub.views import notes_panel_view

        # build_notes_side_panel deve ter annotations
        annotations = notes_panel_view.build_notes_side_panel.__annotations__
        assert "parent" in annotations
        assert "state" in annotations
        assert "callbacks" in annotations
        assert "return" in annotations
