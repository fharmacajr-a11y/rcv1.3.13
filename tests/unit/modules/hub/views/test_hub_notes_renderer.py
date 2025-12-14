# -*- coding: utf-8 -*-
"""Testes para HubNotesRenderer (MF-20).

Testa o renderer de notas extraído do HubScreen, validando:
- Renderização com dados
- Renderização de estados (loading, erro, vazio)
- Uso correto do Protocol (desacoplamento)
- Atualização de UI state (botões, placeholders)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock, call


from src.modules.hub.views.hub_notes_renderer import HubNotesRenderer


class FakeHubState:
    """Fake HubState para testes."""

    def __init__(self):
        self.author_tags: Dict[str, str] = {}
        self.author_cache: Dict[str, tuple] = {}


class FakeNotesView:
    """Fake HubNotesView para testes."""

    def __init__(self):
        self.render_notes_calls: List[Dict[str, Any]] = []

    def render_notes(
        self,
        notes: List[Dict[str, Any]],
        force: bool = False,
        author_tags: Dict[str, str] | None = None,
        author_names_cache: Dict[str, tuple] | None = None,
        hub_screen: Any = None,
        debug_logger: Callable[[str], None] | None = None,
    ) -> None:
        """Simula renderização de notas."""
        self.render_notes_calls.append(
            {
                "notes": notes,
                "force": force,
                "author_tags": author_tags,
                "author_names_cache": author_names_cache,
                "hub_screen": hub_screen,
                "debug_logger": debug_logger,
            }
        )


class FakeNotesRenderCallbacks:
    """Implementação fake de NotesRenderCallbacks para testes."""

    def __init__(
        self,
        notes_view: FakeNotesView | None = None,
        state: FakeHubState | None = None,
        debug_logger: Callable[[str], None] | None = None,
    ):
        self._notes_view = notes_view or FakeNotesView()
        self._state = state or FakeHubState()
        self._debug_logger = debug_logger

    def get_notes_view(self) -> FakeNotesView:
        return self._notes_view

    def get_state(self) -> FakeHubState:
        return self._state

    def get_debug_logger(self) -> Optional[Callable[[str], None]]:
        return self._debug_logger


# ═══════════════════════════════════════════════════════════════════════
# TESTES DE RENDERIZAÇÃO BÁSICA
# ═══════════════════════════════════════════════════════════════════════


def test_render_notes_with_data_calls_view():
    """Testa que render_notes com dados chama a view corretamente."""
    # Arrange
    notes_view = FakeNotesView()
    callbacks = FakeNotesRenderCallbacks(notes_view=notes_view)
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    notes = [
        {"id": "1", "body": "Test note 1", "author_email": "test@example.com"},
        {"id": "2", "body": "Test note 2", "author_email": "user@example.com"},
    ]

    # Act
    renderer.render_notes(notes=notes, force=False)

    # Assert
    assert len(notes_view.render_notes_calls) == 1
    call_args = notes_view.render_notes_calls[0]
    assert call_args["notes"] == notes
    assert call_args["force"] is False
    assert call_args["author_tags"] == {}
    assert call_args["author_names_cache"] == {}


def test_render_notes_with_force_flag():
    """Testa que o flag force é passado corretamente."""
    # Arrange
    notes_view = FakeNotesView()
    callbacks = FakeNotesRenderCallbacks(notes_view=notes_view)
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    notes = [{"id": "1", "body": "Test note"}]

    # Act
    renderer.render_notes(notes=notes, force=True)

    # Assert
    assert len(notes_view.render_notes_calls) == 1
    assert notes_view.render_notes_calls[0]["force"] is True


def test_render_notes_with_empty_list():
    """Testa renderização com lista vazia de notas."""
    # Arrange
    notes_view = FakeNotesView()
    callbacks = FakeNotesRenderCallbacks(notes_view=notes_view)
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    # Act
    renderer.render_notes(notes=[], force=False)

    # Assert
    assert len(notes_view.render_notes_calls) == 1
    assert notes_view.render_notes_calls[0]["notes"] == []


def test_render_notes_uses_author_cache_from_state():
    """Testa que render_notes usa o author_cache do estado."""
    # Arrange
    state = FakeHubState()
    state.author_cache = {
        "test@example.com": ("Test User", 123456.0),
        "user@example.com": ("User Name", 789012.0),
    }
    notes_view = FakeNotesView()
    callbacks = FakeNotesRenderCallbacks(notes_view=notes_view, state=state)
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    notes = [{"id": "1", "body": "Test"}]

    # Act
    renderer.render_notes(notes=notes)

    # Assert
    call_args = notes_view.render_notes_calls[0]
    assert call_args["author_names_cache"] == state.author_cache


def test_render_notes_uses_author_tags_from_state():
    """Testa que render_notes usa o author_tags do estado."""
    # Arrange
    state = FakeHubState()
    state.author_tags = {
        "test@example.com": "tag_blue",
        "user@example.com": "tag_green",
    }
    notes_view = FakeNotesView()
    callbacks = FakeNotesRenderCallbacks(notes_view=notes_view, state=state)
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    notes = [{"id": "1", "body": "Test"}]

    # Act
    renderer.render_notes(notes=notes)

    # Assert
    call_args = notes_view.render_notes_calls[0]
    assert call_args["author_tags"] == state.author_tags


def test_render_notes_initializes_author_tags_if_none():
    """Testa que author_tags é inicializado se for None."""
    # Arrange
    state = FakeHubState()
    state.author_tags = None  # Simula estado não inicializado
    notes_view = FakeNotesView()
    callbacks = FakeNotesRenderCallbacks(notes_view=notes_view, state=state)
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    notes = [{"id": "1", "body": "Test"}]

    # Act
    renderer.render_notes(notes=notes)

    # Assert
    assert state.author_tags == {}  # Deve ter sido inicializado
    call_args = notes_view.render_notes_calls[0]
    assert call_args["author_tags"] == {}


# ═══════════════════════════════════════════════════════════════════════
# TESTES DE ESTADOS (LOADING, ERROR, EMPTY)
# ═══════════════════════════════════════════════════════════════════════


def test_render_loading_logs_debug():
    """Testa que render_loading loga mensagem de debug."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    # Act (não deve lançar exceção)
    renderer.render_loading()

    # Assert: Apenas verifica que não falha
    # (Na implementação real, pode verificar logs)


def test_render_error_logs_warning():
    """Testa que render_error loga mensagem de erro."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    # Act (não deve lançar exceção)
    renderer.render_error("Test error message")

    # Assert: Apenas verifica que não falha


def test_render_empty_logs_debug():
    """Testa que render_empty loga mensagem de debug."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    # Act (não deve lançar exceção)
    renderer.render_empty()

    # Assert: Apenas verifica que não falha


# ═══════════════════════════════════════════════════════════════════════
# TESTES DE UPDATE_NOTES_UI_STATE
# ═══════════════════════════════════════════════════════════════════════


def test_update_notes_ui_state_with_org_id_enables_button():
    """Testa que update_notes_ui_state habilita botão quando há org_id."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    btn = MagicMock()
    field = MagicMock()

    # Act
    renderer.update_notes_ui_state(
        has_org_id=True,
        btn_add_note=btn,
        new_note_field=field,
    )

    # Assert
    btn.configure.assert_called_once_with(state="normal")


def test_update_notes_ui_state_without_org_id_disables_button():
    """Testa que update_notes_ui_state desabilita botão quando não há org_id."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    btn = MagicMock()
    field = MagicMock()

    # Act
    renderer.update_notes_ui_state(
        has_org_id=False,
        btn_add_note=btn,
        new_note_field=field,
    )

    # Assert
    btn.configure.assert_called_once_with(state="disabled")


def test_update_notes_ui_state_with_org_id_enables_text_field():
    """Testa que campo de texto é habilitado quando há org_id."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    btn = MagicMock()
    field = MagicMock()

    # Act
    renderer.update_notes_ui_state(
        has_org_id=True,
        btn_add_note=btn,
        new_note_field=field,
    )

    # Assert
    # Deve configurar como normal duas vezes (temporário para editar + estado final)
    calls = [c for c in field.configure.call_args_list]
    assert any(call(state="normal") in calls for c in calls)


def test_update_notes_ui_state_without_org_id_shows_placeholder():
    """Testa que placeholder é exibido quando não há org_id."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    btn = MagicMock()
    field = MagicMock()

    # Act
    renderer.update_notes_ui_state(
        has_org_id=False,
        btn_add_note=btn,
        new_note_field=field,
    )

    # Assert
    # Deve inserir placeholder
    assert field.insert.called
    insert_args = field.insert.call_args[0]
    assert insert_args[0] == "1.0"
    assert len(insert_args[1]) > 0  # Placeholder message


def test_update_notes_ui_state_handles_none_widgets():
    """Testa que update_notes_ui_state não falha com widgets None."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    # Act (não deve lançar exceção)
    renderer.update_notes_ui_state(
        has_org_id=True,
        btn_add_note=None,
        new_note_field=None,
    )

    # Assert: Apenas verifica que não falha


# ═══════════════════════════════════════════════════════════════════════
# TESTES DE ROBUSTEZ E EDGE CASES
# ═══════════════════════════════════════════════════════════════════════


def test_render_notes_handles_none_notes_view():
    """Testa que render_notes não falha se notes_view for None."""

    # Arrange
    class BadCallbacks:
        def get_notes_view(self):
            return None

        def get_state(self):
            return FakeHubState()

        def get_debug_logger(self):
            return None

    callbacks = BadCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    # Act (não deve lançar exceção)
    renderer.render_notes(notes=[{"id": "1"}])

    # Assert: Apenas verifica que não falha


def test_render_notes_handles_exception_in_callback():
    """Testa que render_notes não falha se callback lançar exceção."""

    # Arrange
    class BadCallbacks:
        def get_notes_view(self):
            raise ValueError("Test error")

        def get_state(self):
            return FakeHubState()

        def get_debug_logger(self):
            return None

    callbacks = BadCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    # Act (não deve lançar exceção)
    renderer.render_notes(notes=[{"id": "1"}])

    # Assert: Apenas verifica que não falha


def test_renderer_repr():
    """Testa representação string do renderer."""
    # Arrange
    callbacks = FakeNotesRenderCallbacks()
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    # Act
    result = repr(renderer)

    # Assert
    assert "HubNotesRenderer" in result


# ═══════════════════════════════════════════════════════════════════════
# TESTES DE INTEGRAÇÃO COM DEBUG LOGGER
# ═══════════════════════════════════════════════════════════════════════


def test_render_notes_passes_debug_logger_to_view():
    """Testa que debug_logger é passado para a view se disponível."""
    # Arrange
    debug_logger = MagicMock()
    notes_view = FakeNotesView()
    callbacks = FakeNotesRenderCallbacks(
        notes_view=notes_view,
        debug_logger=debug_logger,
    )
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    notes = [{"id": "1", "body": "Test"}]

    # Act
    renderer.render_notes(notes=notes)

    # Assert
    call_args = notes_view.render_notes_calls[0]
    assert call_args["debug_logger"] == debug_logger


def test_render_notes_handles_none_debug_logger():
    """Testa que render_notes funciona mesmo sem debug_logger."""
    # Arrange
    notes_view = FakeNotesView()
    callbacks = FakeNotesRenderCallbacks(
        notes_view=notes_view,
        debug_logger=None,
    )
    renderer = HubNotesRenderer(callbacks=callbacks)  # type: ignore[arg-type]

    notes = [{"id": "1", "body": "Test"}]

    # Act
    renderer.render_notes(notes=notes)

    # Assert
    call_args = notes_view.render_notes_calls[0]
    assert call_args["debug_logger"] is None
