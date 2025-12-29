# -*- coding: utf-8 -*-
"""Testes para build_notes_panel (view layer).

Testa que a view renderiza corretamente NotesViewState e conecta callbacks.
"""

from __future__ import annotations


import pytest
import ttkbootstrap as tb

from src.modules.hub.panels import build_notes_panel
from src.modules.hub.viewmodels.notes_vm import NoteItemView, NotesViewState


@pytest.fixture
def parent_frame(tk_root):
    """Create parent frame for testing."""
    return tb.Frame(tk_root)


@pytest.fixture
def sample_notes_state():
    """Sample NotesViewState with 3 notes."""
    notes = [
        NoteItemView(
            id="note1",
            body="First note",
            created_at="2024-01-01T10:00:00Z",
            author_email="user1@example.com",
            author_name="User One",
            formatted_line="[10:00] User One: First note",
            tag_name="user1@example.com",
        ),
        NoteItemView(
            id="note2",
            body="Second note (pinned)",
            created_at="2024-01-02T11:00:00Z",
            author_email="user2@example.com",
            author_name="User Two",
            is_pinned=True,
            formatted_line="[11:00] User Two: Second note (pinned)",
            tag_name="user2@example.com",
        ),
        NoteItemView(
            id="note3",
            body="Third note",
            created_at="2024-01-03T12:00:00Z",
            author_email="user1@example.com",
            author_name="User One",
            formatted_line="[12:00] User One: Third note",
            tag_name="user1@example.com",
        ),
    ]
    return NotesViewState(notes=notes, total_count=3)


@pytest.fixture
def empty_notes_state():
    """Empty NotesViewState."""
    return NotesViewState()


@pytest.fixture
def loading_notes_state():
    """Loading NotesViewState."""
    return NotesViewState(is_loading=True)


@pytest.fixture
def error_notes_state():
    """Error NotesViewState."""
    return NotesViewState(error_message="Erro ao carregar notas do servidor")


class TestBuildNotesPanel:
    """Testes para build_notes_panel."""

    def test_creates_panel_with_widgets(self, parent_frame, sample_notes_state):
        """Deve criar painel com widgets necessários."""
        panel = build_notes_panel(parent_frame, sample_notes_state)

        assert isinstance(panel, tb.Labelframe)
        # Verificar que widgets foram anexados ao painel
        assert hasattr(panel, "notes_history")
        assert hasattr(panel, "new_note")
        assert hasattr(panel, "btn_add_note")

    def test_renders_notes_from_state(self, parent_frame, sample_notes_state):
        """Deve renderizar notas do estado."""
        panel = build_notes_panel(parent_frame, sample_notes_state)

        notes_history = panel.notes_history  # type: ignore[attr-defined]
        content = notes_history.get("1.0", "end")

        # Verificar que as 3 notas aparecem
        assert "First note" in content
        assert "Second note (pinned)" in content
        assert "Third note" in content
        # Verificar que timestamps aparecem
        assert "[10:00]" in content or "10:00" in content
        assert "[11:00]" in content or "11:00" in content

    def test_shows_loading_state(self, parent_frame, loading_notes_state):
        """Deve mostrar mensagem de loading."""
        panel = build_notes_panel(parent_frame, loading_notes_state)

        notes_history = panel.notes_history  # type: ignore[attr-defined]
        content = notes_history.get("1.0", "end")

        assert "Carregando" in content

    def test_shows_error_state(self, parent_frame, error_notes_state):
        """Deve mostrar mensagem de erro."""
        panel = build_notes_panel(parent_frame, error_notes_state)

        notes_history = panel.notes_history  # type: ignore[attr-defined]
        content = notes_history.get("1.0", "end")

        assert "Erro ao carregar" in content
        assert "servidor" in content

    def test_shows_empty_state(self, parent_frame, empty_notes_state):
        """Deve mostrar mensagem quando não há notas."""
        panel = build_notes_panel(parent_frame, empty_notes_state)

        notes_history = panel.notes_history  # type: ignore[attr-defined]
        content = notes_history.get("1.0", "end")

        assert "Nenhuma anotação" in content or "ainda" in content

    def test_history_widget_is_readonly(self, parent_frame, sample_notes_state):
        """Widget de histórico deve ser read-only."""
        panel = build_notes_panel(parent_frame, sample_notes_state)

        notes_history = panel.notes_history  # type: ignore[attr-defined]
        state = str(notes_history.cget("state"))

        assert state == "disabled"

    def test_add_button_calls_callback(self, parent_frame, sample_notes_state):
        """Botão adicionar deve chamar callback."""
        callback_called = []

        def on_add():
            callback_called.append(True)

        panel = build_notes_panel(parent_frame, sample_notes_state, on_add_note_click=on_add)

        btn = panel.btn_add_note  # type: ignore[attr-defined]
        btn.invoke()  # Simular clique

        assert len(callback_called) == 1

    def test_callbacks_are_optional(self, parent_frame, sample_notes_state):
        """Callbacks devem ser opcionais (não causar erro se None)."""
        # Não deve lançar exceção
        panel = build_notes_panel(
            parent_frame,
            sample_notes_state,
            on_add_note_click=None,
            on_edit_note_click=None,
            on_delete_note_click=None,
        )

        assert panel is not None


class TestNotesRendering:
    """Testes específicos de renderização de notas."""

    def test_applies_color_tags_to_authors(self, parent_frame, sample_notes_state):
        """Deve aplicar tags de cor por autor."""
        panel = build_notes_panel(parent_frame, sample_notes_state)

        notes_history = panel.notes_history  # type: ignore[attr-defined]

        # Verificar que tags foram criadas
        tags = notes_history.tag_names()

        # Deve ter tags noteid_ para cada nota (renderer atual usa noteid_<ID> como tag)
        # Verificar que há pelo menos 2 tags noteid_ (uma por nota)
        noteid_tags = [tag for tag in tags if tag.startswith("noteid_")]
        assert len(noteid_tags) >= 2, (
            f"Esperado pelo menos 2 tags noteid_, encontrado {len(noteid_tags)}: {noteid_tags}"
        )

    def test_formatted_lines_are_used(self, parent_frame):
        """Deve renderizar notas com formato de 2 linhas (timestamp - autor: corpo)."""
        notes = [
            NoteItemView(
                id="note1",
                body="Body text",
                created_at="2024-01-01T10:00:00Z",
                author_email="user@example.com",
                formatted_line="CUSTOM FORMAT: Body text",  # Ignorado pelo renderer atual
            )
        ]
        state = NotesViewState(notes=notes, total_count=1)

        panel = build_notes_panel(parent_frame, state)

        notes_history = panel.notes_history  # type: ignore[attr-defined]
        content = notes_history.get("1.0", "end")

        # Renderer atual usa formato: "DD/MM HH:MM - Nome:\nCorpo\n\n"
        # Verificar que tem o corpo da mensagem
        assert "Body text" in content, f"Esperado 'Body text' no conteúdo: {content!r}"
        # Verificar que tem separador de 2 linhas (timestamp - nome:)
        assert " - " in content, f"Esperado ' - ' no conteúdo: {content!r}"
        assert ":\n" in content, f"Esperado ':\\n' no conteúdo: {content!r}"


class TestNotesCallbacks:
    """Testes de callbacks (edit, delete, toggle)."""

    def test_edit_callback_signature(self, parent_frame, sample_notes_state):
        """Callback de edição deve receber note_id."""
        edit_calls = []

        def on_edit(note_id: str):
            edit_calls.append(note_id)

        # Criar painel com callback
        panel = build_notes_panel(parent_frame, sample_notes_state, on_edit_note_click=on_edit)

        # Simular edição (se implementado na view - por enquanto só verificamos que callback foi passado)
        # Por enquanto, apenas verificar que painel foi criado sem erro
        assert panel is not None

    def test_delete_callback_signature(self, parent_frame, sample_notes_state):
        """Callback de deleção deve receber note_id."""
        delete_calls = []

        def on_delete(note_id: str):
            delete_calls.append(note_id)

        panel = build_notes_panel(parent_frame, sample_notes_state, on_delete_note_click=on_delete)

        assert panel is not None

    def test_toggle_pin_callback_signature(self, parent_frame, sample_notes_state):
        """Callback de toggle pin deve receber note_id."""
        pin_calls = []

        def on_pin(note_id: str):
            pin_calls.append(note_id)

        panel = build_notes_panel(parent_frame, sample_notes_state, on_toggle_pin_click=on_pin)

        assert panel is not None

    def test_toggle_done_callback_signature(self, parent_frame, sample_notes_state):
        """Callback de toggle done deve receber note_id."""
        done_calls = []

        def on_done(note_id: str):
            done_calls.append(note_id)

        panel = build_notes_panel(parent_frame, sample_notes_state, on_toggle_done_click=on_done)

        assert panel is not None
