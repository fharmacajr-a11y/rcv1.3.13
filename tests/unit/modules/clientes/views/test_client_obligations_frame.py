# -*- coding: utf-8 -*-
"""Unit tests for client_obligations_frame."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
import ttkbootstrap as tb

from src.modules.clientes.views.client_obligations_frame import ClientObligationsFrame


@pytest.fixture
def tk_root(tk_root_session):
    """Use session root for UI tests."""
    return tk_root_session


@pytest.fixture
def mock_obligations():
    """Sample obligations for testing."""
    return [
        {
            "id": "obl-1",
            "org_id": "org-123",
            "client_id": 5,
            "kind": "SNGPC",
            "title": "Envio SNGPC Dezembro",
            "due_date": date(2025, 12, 31),
            "status": "pending",
            "created_by": "user-1",
            "created_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
        },
        {
            "id": "obl-2",
            "org_id": "org-123",
            "client_id": 5,
            "kind": "FARMACIA_POPULAR",
            "title": "Relatório FP",
            "due_date": date(2025, 12, 15),
            "status": "done",
            "created_by": "user-1",
            "created_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 12, 2, tzinfo=timezone.utc),
        },
    ]


class TestClientObligationsFrame:
    """Tests for ClientObligationsFrame."""

    def test_creates_frame_successfully(self, tk_root):
        """Should create frame without errors."""
        with patch("src.modules.clientes.views.client_obligations_frame.list_obligations_for_client", return_value=[]):
            frame = ClientObligationsFrame(
                tk_root,
                org_id="org-123",
                created_by="user-1",
                client_id=5,
            )

            assert frame is not None
            assert isinstance(frame, tb.Frame)

    def test_loads_obligations_on_init(self, tk_root, mock_obligations):
        """Should load obligations when initialized."""
        with patch(
            "src.modules.clientes.views.client_obligations_frame.list_obligations_for_client",
            return_value=mock_obligations,
        ):
            frame = ClientObligationsFrame(
                tk_root,
                org_id="org-123",
                created_by="user-1",
                client_id=5,
            )
            frame.update()

            # Should have 2 items in tree
            children = frame.tree.get_children()
            assert len(children) == 2

    def test_displays_obligation_data_correctly(self, tk_root, mock_obligations):
        """Should display obligation data in tree."""
        with patch(
            "src.modules.clientes.views.client_obligations_frame.list_obligations_for_client",
            return_value=mock_obligations,
        ):
            frame = ClientObligationsFrame(
                tk_root,
                org_id="org-123",
                created_by="user-1",
                client_id=5,
            )
            frame.update()

            # Check that obligations are displayed
            children = frame.tree.get_children()
            assert len(children) == 2

            # Get all values
            all_values = [frame.tree.item(child, "values") for child in children]

            # Check that both obligations are displayed (order may vary due to sorting)
            titles = [values[1] for values in all_values]
            assert "Envio SNGPC Dezembro" in titles
            assert "Relatório FP" in titles

    def test_updates_status_label(self, tk_root, mock_obligations):
        """Should update status label with count."""
        with patch(
            "src.modules.clientes.views.client_obligations_frame.list_obligations_for_client",
            return_value=mock_obligations,
        ):
            frame = ClientObligationsFrame(
                tk_root,
                org_id="org-123",
                created_by="user-1",
                client_id=5,
            )
            frame.update()

            status_text = frame.status_label.cget("text")
            assert "2" in status_text
            assert "obrigação" in status_text.lower()

    def test_shows_empty_message_when_no_obligations(self, tk_root):
        """Should show 0 obligations when list is empty."""
        with patch("src.modules.clientes.views.client_obligations_frame.list_obligations_for_client", return_value=[]):
            frame = ClientObligationsFrame(
                tk_root,
                org_id="org-123",
                created_by="user-1",
                client_id=5,
            )
            frame.update()

            children = frame.tree.get_children()
            assert len(children) == 0

            status_text = frame.status_label.cget("text")
            assert "0" in status_text

    def test_has_new_button(self, tk_root):
        """Should have new obligation button."""
        with patch("src.modules.clientes.views.client_obligations_frame.list_obligations_for_client", return_value=[]):
            frame = ClientObligationsFrame(
                tk_root,
                org_id="org-123",
                created_by="user-1",
                client_id=5,
            )
            frame.update()

            # Find button with "Nova" text
            found_button = False
            for widget in frame.winfo_children():
                if isinstance(widget, tb.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tb.Button):
                            text = child.cget("text")
                            if "Nova" in text:
                                found_button = True
                                break

            assert found_button, "Should have 'Nova Obrigação' button"

    def test_has_edit_and_delete_buttons(self, tk_root):
        """Should have edit and delete buttons."""
        with patch("src.modules.clientes.views.client_obligations_frame.list_obligations_for_client", return_value=[]):
            frame = ClientObligationsFrame(
                tk_root,
                org_id="org-123",
                created_by="user-1",
                client_id=5,
            )
            frame.update()

            # Check for buttons
            buttons = []
            for widget in frame.winfo_children():
                if isinstance(widget, tb.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tb.Button):
                            buttons.append(child.cget("text"))

            assert any("Editar" in btn for btn in buttons)
            assert any("Excluir" in btn for btn in buttons)
