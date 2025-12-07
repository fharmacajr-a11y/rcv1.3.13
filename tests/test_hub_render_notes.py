"""Tests for HubScreen render_notes method."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock, patch

import pytest

from src.modules.hub.views.hub_screen import HubScreen


class TestHubScreen:
    """Tests for HubScreen class."""

    def test_render_notes_with_valid_widget(self):
        """Test render_notes with a valid widget."""
        # Setup
        root = tk.Tk()
        try:
            screen = HubScreen(root)
            notes = [
                ("Note 1", "Author 1", "2025-12-07"),
                ("Note 2", "Author 2", "2025-12-07"),
            ]

            # Execute
            screen.render_notes(notes)

            # Verify - notes should be rendered without error
            assert screen.notes_history is not None
            content = screen.notes_history.get("1.0", tk.END)
            assert "Note 1" in content
            assert "Note 2" in content
        finally:
            root.destroy()

    def test_render_notes_with_destroyed_widget(self):
        """Test render_notes handles destroyed widget gracefully."""
        # Setup
        root = tk.Tk()
        screen = HubScreen(root)
        notes = [("Note 1", "Author 1", "2025-12-07")]

        # Destroy the notes_history widget
        if screen.notes_history:
            screen.notes_history.destroy()

        # Execute - should not raise TclError
        try:
            screen.render_notes(notes)
            # If we get here without exception, the test passes
            assert True
        except tk.TclError:
            pytest.fail("render_notes raised TclError on destroyed widget")
        finally:
            root.destroy()

    def test_render_notes_with_destroyed_parent(self):
        """Test render_notes handles destroyed parent gracefully."""
        # Setup
        root = tk.Tk()
        screen = HubScreen(root)
        notes = [("Note 1", "Author 1", "2025-12-07")]

        # Destroy the parent
        root.destroy()

        # Execute - should not raise TclError
        try:
            screen.render_notes(notes)
            # If we get here without exception, the test passes
            assert True
        except tk.TclError:
            pytest.fail("render_notes raised TclError on destroyed parent")

    def test_guard_widgets_returns_false_when_destroyed(self):
        """Test _guard_widgets returns False when widget is destroyed."""
        # Setup
        root = tk.Tk()
        screen = HubScreen(root)

        # Verify it returns True initially
        assert screen._guard_widgets() is True

        # Destroy the widget
        if screen.notes_history:
            screen.notes_history.destroy()

        # Verify it returns False after destruction
        assert screen._guard_widgets() is False

        root.destroy()
