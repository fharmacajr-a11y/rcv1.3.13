# -*- coding: utf-8 -*-
"""Testes para notes_panel_view helper."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock

import pytest
import ttkbootstrap as tb

from src.modules.hub.viewmodels.notes_vm import NoteItemView, NotesViewState
from src.modules.hub.views.notes_panel_view import (
    NotesViewCallbacks,
    build_notes_side_panel,
)


@pytest.fixture
def parent_frame(tk_root):
    """Cria frame pai para testes."""
    return tb.Frame(tk_root)


@pytest.fixture
def sample_notes_state():
    """Sample NotesViewState com 2 notas."""
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
            body="Second note",
            created_at="2024-01-02T11:00:00Z",
            author_email="user2@example.com",
            author_name="User Two",
            formatted_line="[11:00] User Two: Second note",
            tag_name="user2@example.com",
        ),
    ]
    return NotesViewState(notes=notes, total_count=2)


@pytest.fixture
def empty_callbacks():
    """Callbacks vazios para testes."""
    return NotesViewCallbacks(
        on_add_note_click=MagicMock(),
        on_edit_note_click=MagicMock(),
        on_delete_note_click=MagicMock(),
        on_toggle_pin_click=MagicMock(),
        on_toggle_done_click=MagicMock(),
    )


class TestNotesViewCallbacks:
    """Testes para NotesViewCallbacks container."""

    def test_can_create_with_all_callbacks(self):
        """Deve criar container com todas as callbacks."""
        callbacks = NotesViewCallbacks(
            on_add_note_click=lambda: None,
            on_edit_note_click=lambda note_id: None,
            on_delete_note_click=lambda note_id: None,
            on_toggle_pin_click=lambda note_id: None,
            on_toggle_done_click=lambda note_id: None,
        )

        assert callbacks.on_add_note_click is not None
        assert callbacks.on_edit_note_click is not None
        assert callbacks.on_delete_note_click is not None
        assert callbacks.on_toggle_pin_click is not None
        assert callbacks.on_toggle_done_click is not None

    def test_can_create_with_none_callbacks(self):
        """Deve criar container com callbacks None."""
        callbacks = NotesViewCallbacks()

        assert callbacks.on_add_note_click is None
        assert callbacks.on_edit_note_click is None
        assert callbacks.on_delete_note_click is None
        assert callbacks.on_toggle_pin_click is None
        assert callbacks.on_toggle_done_click is None


class TestBuildNotesSidePanel:
    """Testes para build_notes_side_panel helper."""

    def test_creates_labelframe(self, parent_frame, sample_notes_state, empty_callbacks):
        """Deve criar Labelframe com título correto."""
        panel = build_notes_side_panel(
            parent=parent_frame,
            state=sample_notes_state,
            callbacks=empty_callbacks,
        )

        assert isinstance(panel, tb.Labelframe)
        assert panel.cget("text") == "Anotações Compartilhadas"

    def test_has_required_widgets(self, parent_frame, sample_notes_state, empty_callbacks):
        """Deve ter widgets necessários anexados."""
        panel = build_notes_side_panel(
            parent=parent_frame,
            state=sample_notes_state,
            callbacks=empty_callbacks,
        )

        # Verificar que widgets foram anexados
        assert hasattr(panel, "notes_history")
        assert hasattr(panel, "new_note")
        assert hasattr(panel, "btn_add_note")

        assert isinstance(panel.notes_history, tk.Text)
        assert isinstance(panel.new_note, tk.Text)
        assert isinstance(panel.btn_add_note, tb.Button)

    def test_add_button_calls_callback(self, parent_frame, sample_notes_state):
        """Deve chamar callback ao clicar no botão adicionar."""
        on_add_click = MagicMock()
        callbacks = NotesViewCallbacks(on_add_note_click=on_add_click)

        panel = build_notes_side_panel(
            parent=parent_frame,
            state=sample_notes_state,
            callbacks=callbacks,
        )

        # Simular clique no botão
        panel.btn_add_note.invoke()

        # Verificar que callback foi chamado
        on_add_click.assert_called_once()

    def test_empty_state_creates_panel(self, parent_frame, empty_callbacks):
        """Deve criar painel mesmo com estado vazio."""
        empty_state = NotesViewState()

        panel = build_notes_side_panel(
            parent=parent_frame,
            state=empty_state,
            callbacks=empty_callbacks,
        )

        assert isinstance(panel, tb.Labelframe)
        assert hasattr(panel, "notes_history")
        assert hasattr(panel, "new_note")
        assert hasattr(panel, "btn_add_note")

    def test_delegates_to_build_notes_panel(self, parent_frame, sample_notes_state, empty_callbacks):
        """Deve delegar para build_notes_panel de panels.py."""
        # Este teste verifica indiretamente que a delegação funciona
        # ao verificar que o painel resultante tem as características esperadas
        panel = build_notes_side_panel(
            parent=parent_frame,
            state=sample_notes_state,
            callbacks=empty_callbacks,
        )

        # Verificar estrutura do painel (grid com history + entry)
        children = list(panel.winfo_children())
        assert len(children) >= 2  # Pelo menos history_frame e entry_frame

    def test_respects_all_callbacks(self, parent_frame, sample_notes_state):
        """Deve respeitar todas as callbacks fornecidas."""
        mock_add = MagicMock()
        mock_edit = MagicMock()
        mock_delete = MagicMock()
        mock_pin = MagicMock()
        mock_done = MagicMock()

        callbacks = NotesViewCallbacks(
            on_add_note_click=mock_add,
            on_edit_note_click=mock_edit,
            on_delete_note_click=mock_delete,
            on_toggle_pin_click=mock_pin,
            on_toggle_done_click=mock_done,
        )

        panel = build_notes_side_panel(
            parent=parent_frame,
            state=sample_notes_state,
            callbacks=callbacks,
        )

        # Verificar que o painel foi criado (callbacks são usadas internamente)
        assert isinstance(panel, tb.Labelframe)
        assert hasattr(panel, "btn_add_note")

        # Testar callback de adicionar
        panel.btn_add_note.invoke()
        mock_add.assert_called_once()
