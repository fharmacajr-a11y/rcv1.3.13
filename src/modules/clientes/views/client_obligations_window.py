# -*- coding: utf-8 -*-
"""Dialog window for managing client regulatory obligations."""

from __future__ import annotations

import logging
from typing import Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH

from src.modules.clientes.views.client_obligations_frame import ClientObligationsFrame

logger = logging.getLogger(__name__)


class ClientObligationsWindow(tb.Toplevel):
    """Standalone window for managing client regulatory obligations."""

    def __init__(
        self,
        parent: tb.Window,
        org_id: str,
        created_by: str,
        client_id: int,
        client_name: str = "",
        *,
        on_refresh_hub: Callable[[], None] | None = None,
    ):
        """Initialize obligations window.

        Args:
            parent: Parent window.
            org_id: Organization ID.
            created_by: User ID for creating obligations.
            client_id: Client ID to show obligations for.
            client_name: Client name for window title.
            on_refresh_hub: Optional callback to refresh Hub dashboard.
        """
        super().__init__(parent)

        # Configure window
        display_name = client_name or f"Cliente #{client_id}"
        self.title(f"Obrigações Regulatórias - {display_name}")
        self.geometry("800x600")

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Create obligations frame
        self.obligations_frame = ClientObligationsFrame(
            self,  # type: ignore[arg-type]
            org_id=org_id,
            created_by=created_by,
            client_id=client_id,
            on_refresh_hub=on_refresh_hub,
        )
        self.obligations_frame.pack(fill=BOTH, expand=True)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")


def show_client_obligations_window(
    parent: tb.Window,
    org_id: str,
    created_by: str,
    client_id: int,
    client_name: str = "",
    *,
    on_refresh_hub: Callable[[], None] | None = None,
) -> None:
    """Show client obligations management window.

    Args:
        parent: Parent window.
        org_id: Organization ID.
        created_by: User ID for creating obligations.
        client_id: Client ID to show obligations for.
        client_name: Client name for window title.
        on_refresh_hub: Optional callback to refresh Hub dashboard.
    """
    window = ClientObligationsWindow(
        parent,
        org_id=org_id,
        created_by=created_by,
        client_id=client_id,
        client_name=client_name,
        on_refresh_hub=on_refresh_hub,
    )
    window.wait_window()
