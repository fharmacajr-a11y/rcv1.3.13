# -*- coding: utf-8 -*-
"""Testes unitários para NotesServiceAdapter (MF-5).

Valida o adapter que fornece interface consistente para NotesController,
incluindo operações de toggle para is_pinned e is_done.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.services.notes_service_adapter import NotesServiceAdapter


@pytest.fixture
def mock_notes_service():
    """Mock do módulo notes_service."""
    with patch("src.core.services.notes_service_adapter.notes_service") as mock:
        yield mock


@pytest.fixture
def mock_supabase():
    """Mock do cliente Supabase."""
    with (
        patch("infra.supabase_client.get_supabase") as mock_get,
        patch("infra.supabase_client.exec_postgrest") as mock_exec,
    ):
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client, mock_exec


class TestNotesServiceAdapterCreate:
    """Testes para create_note."""

    def test_create_note_success(self, mock_notes_service):
        """Deve criar nota usando notes_service.add_note."""
        mock_notes_service.add_note.return_value = {
            "id": "new_note_id",
            "org_id": "org123",
            "author_email": "user@example.com",
            "body": "Test note",
            "created_at": "2024-01-01T10:00:00Z",
        }

        adapter = NotesServiceAdapter()
        result = adapter.create_note(
            org_id="org123",
            author_email="user@example.com",
            body="Test note",
        )

        assert result["id"] == "new_note_id"
        mock_notes_service.add_note.assert_called_once_with(
            org_id="org123",
            author_email="user@example.com",
            body="Test note",
        )

    def test_create_note_propagates_error(self, mock_notes_service):
        """Deve propagar exceções do notes_service."""
        mock_notes_service.add_note.side_effect = ValueError("Nota vazia")

        adapter = NotesServiceAdapter()
        with pytest.raises(ValueError, match="Nota vazia"):
            adapter.create_note(
                org_id="org123",
                author_email="user@example.com",
                body="",
            )


class TestNotesServiceAdapterUpdate:
    """Testes para update_note."""

    def test_update_note_body_only(self, mock_supabase):
        """Deve atualizar apenas body."""
        mock_client, mock_exec = mock_supabase
        mock_exec.return_value = MagicMock(
            data=[
                {
                    "id": "note1",
                    "body": "Updated body",
                    "is_pinned": False,
                    "is_done": False,
                }
            ]
        )

        adapter = NotesServiceAdapter()
        result = adapter.update_note(note_id="note1", body="Updated body")

        assert result["body"] == "Updated body"
        # Verificar que update foi chamado
        mock_client.table.assert_called_with("rc_notes")

    def test_update_note_is_pinned_only(self, mock_supabase):
        """Deve atualizar apenas is_pinned."""
        mock_client, mock_exec = mock_supabase
        mock_exec.return_value = MagicMock(
            data=[
                {
                    "id": "note1",
                    "body": "Original body",
                    "is_pinned": True,
                    "is_done": False,
                }
            ]
        )

        adapter = NotesServiceAdapter()
        result = adapter.update_note(note_id="note1", is_pinned=True)

        assert result["is_pinned"] is True

    def test_update_note_is_done_only(self, mock_supabase):
        """Deve atualizar apenas is_done."""
        mock_client, mock_exec = mock_supabase
        mock_exec.return_value = MagicMock(
            data=[
                {
                    "id": "note1",
                    "body": "Original body",
                    "is_pinned": False,
                    "is_done": True,
                }
            ]
        )

        adapter = NotesServiceAdapter()
        result = adapter.update_note(note_id="note1", is_done=True)

        assert result["is_done"] is True

    def test_update_note_multiple_fields(self, mock_supabase):
        """Deve atualizar múltiplos campos."""
        mock_client, mock_exec = mock_supabase
        mock_exec.return_value = MagicMock(
            data=[
                {
                    "id": "note1",
                    "body": "New body",
                    "is_pinned": True,
                    "is_done": True,
                }
            ]
        )

        adapter = NotesServiceAdapter()
        result = adapter.update_note(
            note_id="note1",
            body="New body",
            is_pinned=True,
            is_done=True,
        )

        assert result["body"] == "New body"
        assert result["is_pinned"] is True
        assert result["is_done"] is True

    def test_update_note_no_fields_raises_error(self):
        """Deve lançar erro se nenhum campo fornecido."""
        adapter = NotesServiceAdapter()

        with pytest.raises(ValueError, match="Nenhum campo fornecido"):
            adapter.update_note(note_id="note1")

    def test_update_note_not_found(self, mock_supabase):
        """Deve lançar erro se nota não encontrada."""
        mock_client, mock_exec = mock_supabase
        # Simular update retornando vazio E SELECT também retornando vazio
        mock_exec.side_effect = [
            MagicMock(data=[]),  # update retorna vazio
            MagicMock(data=[]),  # SELECT fallback também retorna vazio
        ]

        adapter = NotesServiceAdapter()

        with pytest.raises(ValueError, match="não encontrada ou sem permissão"):
            adapter.update_note(note_id="nonexistent", body="Test")

    def test_update_note_fallback_select(self, mock_supabase):
        """Deve fazer SELECT fallback quando update retorna data vazio."""
        mock_client, mock_exec = mock_supabase
        # Simular update retornando vazio, mas SELECT retornando a nota
        expected_note = {
            "id": "note1",
            "body": "__RC_DELETED__",
            "org_id": "org123",
            "author_email": "user@example.com",
            "created_at": "2024-01-01T10:00:00Z",
            "is_pinned": False,
            "is_done": False,
        }
        mock_exec.side_effect = [
            MagicMock(data=[]),  # update retorna vazio
            MagicMock(data=[expected_note]),  # SELECT fallback retorna nota
        ]

        adapter = NotesServiceAdapter()
        result = adapter.update_note(note_id="note1", body="__RC_DELETED__")

        # Deve retornar a nota do SELECT fallback
        assert result["id"] == "note1"
        assert result["body"] == "__RC_DELETED__"
        # Verificar que foram 2 chamadas (update + select)
        assert mock_exec.call_count == 2

    def test_update_note_handles_exception(self, mock_supabase):
        """Deve propagar exceções do Supabase."""
        mock_client, mock_exec = mock_supabase
        mock_exec.side_effect = Exception("Database error")

        adapter = NotesServiceAdapter()

        with pytest.raises(Exception, match="Database error"):
            adapter.update_note(note_id="note1", body="Test")


class TestNotesServiceAdapterDelete:
    """Testes para delete_note."""

    def test_delete_note_success(self, mock_supabase):
        """Deve deletar nota com sucesso."""
        mock_client, mock_exec = mock_supabase

        adapter = NotesServiceAdapter()
        adapter.delete_note(note_id="note1")

        # Verificar que delete foi chamado
        mock_client.table.assert_called_with("rc_notes")

    def test_delete_note_handles_exception(self, mock_supabase):
        """Deve propagar exceções do Supabase."""
        mock_client, mock_exec = mock_supabase
        mock_exec.side_effect = Exception("Permission denied")

        adapter = NotesServiceAdapter()

        with pytest.raises(Exception, match="Permission denied"):
            adapter.delete_note(note_id="note1")


class TestNotesServiceAdapterList:
    """Testes para list_notes."""

    def test_list_notes_delegates_to_service(self, mock_notes_service):
        """Deve delegar para notes_service.list_notes."""
        mock_notes_service.list_notes.return_value = [
            {"id": "note1", "body": "First"},
            {"id": "note2", "body": "Second"},
        ]

        adapter = NotesServiceAdapter()
        result = adapter.list_notes(org_id="org123", limit=100)

        assert len(result) == 2
        mock_notes_service.list_notes.assert_called_once_with(org_id="org123", limit=100)
