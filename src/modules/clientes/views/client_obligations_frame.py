# -*- coding: utf-8 -*-
"""Frame for managing client regulatory obligations."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Callable

from src.db.domain_types import RegObligationRow
from src.features.regulations.service import delete_obligation, list_obligations_for_client
from src.modules.clientes.views.obligation_dialog import ObligationDialog

# CustomTkinter via SSoT
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
from src.ui.widgets import CTkTableView

logger = logging.getLogger(__name__)

# Column definitions for Treeview
COLUMNS = {
    "kind": {"text": "Tipo", "width": 150},
    "title": {"text": "Título", "width": 250},
    "due_date": {"text": "Vencimento", "width": 100},
    "status": {"text": "Status", "width": 100},
}

# Status labels for display
STATUS_LABELS = {
    "pending": "Pendente",
    "done": "Concluída",
    "overdue": "Atrasada",
    "canceled": "Cancelada",
}

# Kind labels for display
KIND_LABELS = {
    "SNGPC": "SNGPC",
    "FARMACIA_POPULAR": "Farmácia Popular",
    "SIFAP": "SIFAP",
    "LICENCA_SANITARIA": "Licença Sanitária",
    "OUTRO": "Outro",
}


# Determina classe base
if HAS_CUSTOMTKINTER and ctk is not None:
    _ObligationsFrameBase = ctk.CTkFrame  # type: ignore[misc,assignment]
else:
    _ObligationsFrameBase = tk.Frame  # type: ignore[misc,assignment]


class ClientObligationsFrame(_ObligationsFrameBase):  # type: ignore[misc]
    """Frame for managing regulatory obligations for a client."""

    def __init__(
        self,
        parent: tk.Misc,
        org_id: str,
        created_by: str,
        client_id: int,
        *,
        on_refresh_hub: Callable[[], None] | None = None,
    ):
        """Initialize obligations frame.

        Args:
            parent: Parent widget.
            org_id: Organization ID.
            created_by: User ID for creating obligations.
            client_id: Client ID to show obligations for.
            on_refresh_hub: Optional callback to refresh Hub dashboard.
        """
        # Inicializar base
        if HAS_CUSTOMTKINTER and ctk is not None:
            super().__init__(parent, fg_color="transparent")
        else:
            super().__init__(parent)

        self.org_id = org_id
        self.created_by = created_by
        self.client_id = client_id
        self.on_refresh_hub = on_refresh_hub

        self._build_ui()
        self.load_obligations()

    def _build_ui(self) -> None:
        """Build frame UI."""
        # Toolbar
        if HAS_CUSTOMTKINTER and ctk is not None:
            toolbar = ctk.CTkFrame(self, fg_color="transparent")
        else:
            toolbar = tk.Frame(self)
        toolbar.pack(side="top", fill="x", padx=5, pady=5)

        # Botões da toolbar
        if HAS_CUSTOMTKINTER and ctk is not None:
            ctk.CTkButton(
                toolbar,
                text="➕ Nova Obrigação",
                command=self._on_new,
                width=150,
                fg_color="#28a745",
                hover_color="#218838",
            ).pack(side="left", padx=(0, 5))

            ctk.CTkButton(
                toolbar,
                text="✏️ Editar",
                command=self._on_edit,
                width=120,
            ).pack(side="left", padx=(0, 5))

            ctk.CTkButton(
                toolbar,
                text="🗑️ Excluir",
                command=self._on_delete,
                width=120,
                fg_color="#dc3545",
                hover_color="#c82333",
            ).pack(side="left", padx=(0, 5))

            ctk.CTkButton(
                toolbar,
                text="🔄 Atualizar",
                command=self.load_obligations,
                width=120,
                fg_color="#17a2b8",
                hover_color="#138496",
            ).pack(side="left")
        else:
            tk.Button(
                toolbar,
                text="➕ Nova Obrigação",
                command=self._on_new,
                width=18,
            ).pack(side="left", padx=(0, 5))

            tk.Button(
                toolbar,
                text="✏️ Editar",
                command=self._on_edit,
                width=15,
            ).pack(side="left", padx=(0, 5))

            tk.Button(
                toolbar,
                text="🗑️ Excluir",
                command=self._on_delete,
                width=15,
            ).pack(side="left", padx=(0, 5))

            tk.Button(
                toolbar,
                text="🔄 Atualizar",
                command=self.load_obligations,
                width=15,
            ).pack(side="left")

        # Treeview
        if HAS_CUSTOMTKINTER and ctk is not None:
            tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        else:
            tree_frame = tk.Frame(self)
        tree_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # Create Treeview
        self.tree = CTkTableView(
            tree_frame,
            columns=list(COLUMNS.keys()),
            show="headings",
            # selectmode="browse" handled internally
            zebra=True,
        )

        # Configure columns
        for col_id, col_info in COLUMNS.items():
            self.tree.heading(col_id, text=col_info["text"])
            self.tree.column(col_id, width=col_info["width"])

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Bind double-click
        self.tree.bind("<Double-Button-1>", lambda e: self._on_edit())

        # Status bar
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.status_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 9))
        else:
            self.status_label = tk.Label(self, text="", font=("Segoe UI", 9))
        self.status_label.pack(side="bottom", fill="x", padx=5, pady=5)

    def load_obligations(self) -> None:
        """Load and display obligations for the current client."""
        try:
            # Clear tree
            self.tree.clear()

            # Fetch obligations
            obligations = list_obligations_for_client(self.org_id, self.client_id)

            # Sort by due date
            obligations.sort(key=lambda x: x.get("due_date", "9999-12-31"))

            # Populate tree
            for obl in obligations:
                kind = obl.get("kind", "OUTRO")
                title = obl.get("title", "")
                due_date = obl.get("due_date", "")
                status = obl.get("status", "pending")

                # Format for display
                kind_label = KIND_LABELS.get(kind, kind)
                status_label = STATUS_LABELS.get(status, status)

                # Format date
                if isinstance(due_date, str):
                    try:
                        from datetime import datetime

                        due_date_obj = datetime.fromisoformat(due_date).date()
                        due_date_str = due_date_obj.strftime("%d/%m/%Y")
                    except Exception:
                        due_date_str = due_date
                else:
                    due_date_str = due_date.strftime("%d/%m/%Y")

                self.tree.insert(
                    "",
                    "end",
                    values=[kind_label, title, due_date_str, status_label],
                    tags=(obl["id"],),
                )

            # Update status
            count = len(obligations)
            self.status_label.configure(text=f"{count} obrigação(ões) encontrada(s)")

        except Exception as exc:
            logger.error("Failed to load obligations: %s", exc)
            messagebox.showerror("Erro", f"Erro ao carregar obrigações: {exc}", parent=self)

    def _get_selected_obligation(self) -> RegObligationRow | None:
        """Get currently selected obligation."""
        item = self.tree.get_selected_iid()
        if not item:
            return None

        tags = self.tree.item(item, "tags")
        if not tags:
            return None

        obligation_id = tags[0]

        # Fetch full obligation data
        try:
            obligations = list_obligations_for_client(self.org_id, self.client_id)
            for obl in obligations:
                if obl["id"] == obligation_id:
                    return obl
        except Exception as exc:
            logger.error("Failed to get obligation: %s", exc)

        return None

    def _on_new(self) -> None:
        """Handle new obligation button."""
        dialog = ObligationDialog(
            self.winfo_toplevel(),  # type: ignore[arg-type]
            org_id=self.org_id,
            created_by=self.created_by,
            client_id=self.client_id,
            on_success=self._on_obligation_saved,
        )
        dialog.wait_window()

    def _on_edit(self) -> None:
        """Handle edit obligation button."""
        obligation = self._get_selected_obligation()
        if not obligation:
            messagebox.showwarning("Atenção", "Selecione uma obrigação para editar", parent=self)
            return

        dialog = ObligationDialog(
            self.winfo_toplevel(),  # type: ignore[arg-type]
            org_id=self.org_id,
            created_by=self.created_by,
            client_id=self.client_id,
            obligation=obligation,
            on_success=self._on_obligation_saved,
        )
        dialog.wait_window()

    def _on_delete(self) -> None:
        """Handle delete obligation button."""
        obligation = self._get_selected_obligation()
        if not obligation:
            messagebox.showwarning("Atenção", "Selecione uma obrigação para excluir", parent=self)
            return

        # Confirm
        confirm = messagebox.askyesno(
            "Confirmar exclusão",
            f"Deseja realmente excluir a obrigação '{obligation['title']}'?",
            parent=self,
        )

        if not confirm:
            return

        try:
            delete_obligation(self.org_id, obligation["id"])
            self._on_obligation_saved()
        except Exception as exc:
            logger.error("Failed to delete obligation: %s", exc)
            messagebox.showerror("Erro", f"Erro ao excluir: {exc}", parent=self)

    def _on_obligation_saved(self) -> None:
        """Handle successful obligation save/delete."""
        self.load_obligations()

        # Refresh Hub if callback provided
        if self.on_refresh_hub:
            try:
                self.on_refresh_hub()
            except Exception as exc:
                logger.warning("Failed to refresh Hub: %s", exc)
