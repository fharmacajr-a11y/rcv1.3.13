# -*- coding: utf-8 -*-
"""Dialog window for managing client regulatory obligations."""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable

from src.modules.clientes.views.client_obligations_frame import ClientObligationsFrame

# CustomTkinter via SSoT
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

logger = logging.getLogger(__name__)

# Determina classe base para Toplevel
if HAS_CUSTOMTKINTER and ctk is not None:
    _TopLevelBase = ctk.CTkToplevel  # type: ignore[misc,assignment]
else:
    _TopLevelBase = tk.Toplevel  # type: ignore[misc,assignment]


class ClientObligationsWindow(_TopLevelBase):  # type: ignore[misc]
    """Standalone window for managing client regulatory obligations."""

    def __init__(
        self,
        parent: tk.Misc,
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
            self,
            org_id=org_id,
            created_by=created_by,
            client_id=client_id,
            on_refresh_hub=on_refresh_hub,
        )
        self.obligations_frame.pack(fill="both", expand=True)

        # Center on parent
        self.update_idletasks()
        if hasattr(parent, 'winfo_x'):
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
            self.geometry(f"+{max(0, x)}+{max(0, y)}")


def show_client_obligations_window(
    parent: tk.Misc,
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
