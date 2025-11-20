"""Service fino para o módulo Notas/Hub."""

from __future__ import annotations

from src.core.services import notes_service

list_notes = notes_service.list_notes
add_note = notes_service.add_note
list_notes_since = notes_service.list_notes_since
NotesTransientError = notes_service.NotesTransientError
NotesAuthError = notes_service.NotesAuthError
NotesTableMissingError = notes_service.NotesTableMissingError

__all__ = [
    "list_notes",
    "add_note",
    "list_notes_since",
    "NotesTransientError",
    "NotesAuthError",
    "NotesTableMissingError",
]
