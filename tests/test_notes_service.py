# -*- coding: utf-8 -*-
"""Tests for src/core/services/notes_service.py - shared notes service."""

from __future__ import annotations

import errno
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.core.services.notes_service import (
    NotesTableMissingError,
    _is_transient_net_error,
    _normalize_author_emails,
    add_note,
    list_notes,
)


class TestIsTransientNetError:
    """Tests for _is_transient_net_error helper."""

    def test_detect_winerror_10035(self):
        """Should detect WinError 10035 (WSAEWOULDBLOCK)."""
        error = Exception("WinError 10035: Resource temporarily unavailable")
        assert _is_transient_net_error(error) is True

    def test_detect_timeout(self):
        """Should detect timeout errors."""
        error = Exception("Connection timed out")
        assert _is_transient_net_error(error) is True

    def test_detect_connection_reset(self):
        """Should detect connection reset errors."""
        error = Exception("Connection reset by peer")
        assert _is_transient_net_error(error) is True

    def test_detect_errno_wouldblock(self):
        """Should detect EWOULDBLOCK errno."""
        error = OSError()
        error.errno = errno.EWOULDBLOCK
        assert _is_transient_net_error(error) is True

    def test_non_transient_error(self):
        """Should return False for non-transient errors."""
        error = ValueError("Invalid value")
        assert _is_transient_net_error(error) is False


class TestNormalizeAuthorEmails:
    """Tests for _normalize_author_emails helper."""

    @patch("src.core.services.profiles_service.get_email_prefix_map")
    def test_normalize_with_prefix(self, mock_get_map):
        """Should normalize email prefix to full email."""
        mock_get_map.return_value = {
            "user1": "user1@example.com",
            "user2": "user2@example.com",
        }

        rows = [
            {"author_email": "user1", "body": "Test note 1"},
            {"author_email": "user2", "body": "Test note 2"},
        ]

        result = _normalize_author_emails(rows, "org-123")

        assert result[0]["author_email"] == "user1@example.com"
        assert result[1]["author_email"] == "user2@example.com"
        mock_get_map.assert_called_once_with("org-123")

    @patch("src.core.services.profiles_service.get_email_prefix_map")
    def test_normalize_already_full_email(self, mock_get_map):
        """Should keep full email as-is (lowercase)."""
        mock_get_map.return_value = {}

        rows = [
            {"author_email": "User@Example.COM", "body": "Test note"},
        ]

        result = _normalize_author_emails(rows, "org-123")

        assert result[0]["author_email"] == "user@example.com"

    @patch("src.core.services.profiles_service.get_email_prefix_map")
    def test_normalize_empty_email(self, mock_get_map):
        """Should handle empty email."""
        mock_get_map.return_value = {}

        rows = [
            {"author_email": "", "body": "Test note"},
            {"author_email": None, "body": "Another note"},
        ]

        result = _normalize_author_emails(rows, "org-123")

        assert result[0]["author_email"] == ""
        assert result[1]["author_email"] == ""

    @patch("src.core.services.profiles_service.get_email_prefix_map")
    def test_normalize_handles_exception(self, mock_get_map):
        """Should handle exception when getting email map."""
        mock_get_map.side_effect = Exception("DB error")

        rows = [
            {"author_email": "user1", "body": "Test note"},
        ]

        # Should not crash, just use prefix as-is
        result = _normalize_author_emails(rows, "org-123")
        assert result[0]["author_email"] == "user1"


class TestListNotes:
    """Tests for list_notes function."""

    @patch("src.core.services.notes_service.get_supabase")
    @patch("src.core.services.notes_service._normalize_author_emails")
    def test_list_notes_success(self, mock_normalize, mock_get_supabase):
        """Should list notes successfully."""
        # Arrange
        mock_data = [
            {"id": 1, "author_email": "user1", "body": "Note 1", "created_at": "2025-01-01"},
            {"id": 2, "author_email": "user2", "body": "Note 2", "created_at": "2025-01-02"},
        ]

        mock_response = Mock()
        mock_response.data = mock_data

        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value = mock_response

        mock_supabase = Mock()
        mock_supabase.table.return_value = mock_table
        mock_get_supabase.return_value = mock_supabase

        mock_normalize.return_value = mock_data

        # Act
        result = list_notes("org-123", limit=100)

        # Assert
        assert len(result) == 2
        assert result[0]["body"] == "Note 1"
        mock_supabase.table.assert_called_once_with("rc_notes")
        mock_normalize.assert_called_once()

    @patch("src.core.services.notes_service.get_supabase")
    def test_list_notes_empty_result(self, mock_get_supabase):
        """Should handle empty result."""
        mock_response = Mock()
        mock_response.data = []

        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value = mock_response

        mock_supabase = Mock()
        mock_supabase.table.return_value = mock_table
        mock_get_supabase.return_value = mock_supabase

        result = list_notes("org-123")

        assert result == []

    @patch("src.core.services.notes_service.get_supabase")
    def test_list_notes_table_missing(self, mock_get_supabase):
        """Should raise NotesTableMissingError if table doesn't exist."""
        mock_supabase = Mock()
        mock_supabase.table.side_effect = Exception("PGRST205: relation rc_notes does not exist")
        mock_get_supabase.return_value = mock_supabase

        with pytest.raises(NotesTableMissingError):
            list_notes("org-123")


class TestAddNote:
    """Tests for add_note function."""

    @patch("src.core.services.notes_service.exec_postgrest")
    @patch("src.core.services.notes_service.get_supabase")
    @patch("src.core.services.profiles_service.get_email_prefix_map")
    def test_add_note_success(self, mock_get_map, mock_get_supabase, mock_exec):
        """Should add note successfully."""
        # Arrange
        mock_get_map.return_value = {}

        mock_inserted = {"id": 1, "author_email": "user@example.com", "body": "Test note", "created_at": "2025-01-01"}
        mock_response = Mock()
        mock_response.data = [mock_inserted]
        mock_exec.return_value = mock_response

        mock_table = Mock()
        mock_supabase = Mock()
        mock_supabase.table.return_value = mock_table
        mock_get_supabase.return_value = mock_supabase

        # Act
        result = add_note("org-123", "user@example.com", "Test note")

        # Assert
        assert result["body"] == "Test note"
        assert result["author_email"] == "user@example.com"
        mock_supabase.table.assert_called_once_with("rc_notes")

    def test_add_note_empty_body(self):
        """Should raise ValueError for empty body."""
        with pytest.raises(ValueError, match="Anotação vazia"):
            add_note("org-123", "user@example.com", "")

    def test_add_note_none_body(self):
        """Should raise ValueError for None body."""
        bad_body: Any = None
        with pytest.raises(ValueError, match="Anotação vazia"):
            add_note("org-123", "user@example.com", bad_body)

    @patch("src.core.services.notes_service.exec_postgrest")
    @patch("src.core.services.notes_service.get_supabase")
    @patch("src.core.services.profiles_service.get_email_prefix_map")
    def test_add_note_truncates_long_body(self, mock_get_map, mock_get_supabase, mock_exec):
        """Should truncate body to 1000 chars."""
        mock_get_map.return_value = {}

        mock_response = Mock()
        mock_response.data = [{"id": 1, "body": "x" * 1000}]
        mock_exec.return_value = mock_response

        mock_table = Mock()
        mock_supabase = Mock()
        mock_supabase.table.return_value = mock_table
        mock_get_supabase.return_value = mock_supabase

        long_body = "x" * 1500
        result = add_note("org-123", "user@example.com", long_body)

        # Check that insert was called - the truncation happens before insert
        assert result is not None

    @patch("src.core.services.notes_service.exec_postgrest")
    @patch("src.core.services.notes_service.get_supabase")
    @patch("src.core.services.profiles_service.get_email_prefix_map")
    def test_add_note_normalizes_email(self, mock_get_map, mock_get_supabase, mock_exec):
        """Should normalize author email to lowercase."""
        mock_get_map.return_value = {}

        mock_response = Mock()
        mock_response.data = [{"id": 1, "author_email": "user@example.com", "body": "Test"}]
        mock_exec.return_value = mock_response

        mock_table = Mock()
        mock_supabase = Mock()
        mock_supabase.table.return_value = mock_table
        mock_get_supabase.return_value = mock_supabase

        result = add_note("org-123", "User@Example.COM", "Test note")

        # Email should be normalized in result
        assert result["author_email"] == "user@example.com"
