# -*- coding: utf-8 -*-
"""Dialog for creating/editing regulatory obligations."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, RIGHT, X
from ttkbootstrap.dialogs import Messagebox

from src.db.domain_types import RegObligationRow
from src.features.regulations.service import (
    create_obligation,
    update_obligation,
)

logger = logging.getLogger(__name__)

# Opções de tipo de obrigação
OBLIGATION_KINDS = [
    ("SNGPC", "SNGPC"),
    ("Farmácia Popular", "FARMACIA_POPULAR"),
    ("SIFAP", "SIFAP"),
    ("Licença Sanitária", "LICENCA_SANITARIA"),
    ("Outro", "OUTRO"),
]

# Opções de status
OBLIGATION_STATUSES = [
    ("Pendente", "pending"),
    ("Concluída", "done"),
    ("Atrasada", "overdue"),
    ("Cancelada", "canceled"),
]


class ObligationDialog(tb.Toplevel):
    """Dialog for creating or editing a regulatory obligation."""

    def __init__(
        self,
        parent: tb.Window,
        org_id: str,
        created_by: str,
        client_id: int,
        *,
        obligation: RegObligationRow | None = None,
        on_success: Callable[[], None] | None = None,
    ):
        """Initialize obligation dialog.

        Args:
            parent: Parent window.
            org_id: Organization ID.
            created_by: User ID creating/editing the obligation.
            client_id: Client ID this obligation belongs to.
            obligation: Existing obligation to edit (None for new).
            on_success: Callback to call after successful save.
        """
        super().__init__(parent)

        self.org_id = org_id
        self.created_by = created_by
        self.client_id = client_id
        self.obligation = obligation
        self.on_success = on_success
        self.result: RegObligationRow | None = None

        # Configure window
        is_edit = obligation is not None
        self.title("Editar Obrigação" if is_edit else "Nova Obrigação")
        self.geometry("500x550")
        self.minsize(500, 550)
        self.resizable(False, True)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Build UI
        self._build_ui()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        # Focus first field
        self.kind_combo.focus()

    def _build_ui(self) -> None:
        """Build dialog UI."""
        # Main container
        container = tb.Frame(self, padding=20)
        container.pack(fill=BOTH, expand=True)

        # Form fields
        row = 0

        # Kind
        tb.Label(container, text="Tipo de obrigação:", font=("Segoe UI", 10)).grid(
            row=row, column=0, sticky="w", pady=(0, 5)
        )
        row += 1

        self.kind_var = tb.StringVar(value=self.obligation["kind"] if self.obligation else "SNGPC")
        self.kind_combo = tb.Combobox(
            container,
            textvariable=self.kind_var,
            values=[label for label, _ in OBLIGATION_KINDS],
            state="readonly",
            width=40,
        )
        self.kind_combo.grid(row=row, column=0, sticky="ew", pady=(0, 15))

        # Map display value to kind value
        if self.obligation:
            kind_value = self.obligation["kind"]
            for label, value in OBLIGATION_KINDS:
                if value == kind_value:
                    self.kind_combo.set(label)
                    break

        row += 1

        # Title
        tb.Label(container, text="Título:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        self.title_var = tb.StringVar(value=self.obligation.get("title", "") if self.obligation else "")
        self.title_entry = tb.Entry(container, textvariable=self.title_var, width=40)
        self.title_entry.grid(row=row, column=0, sticky="ew", pady=(0, 15))
        row += 1

        # Due date
        tb.Label(container, text="Data de vencimento:", font=("Segoe UI", 10)).grid(
            row=row, column=0, sticky="w", pady=(0, 5)
        )
        row += 1

        due_date_value = self.obligation["due_date"] if self.obligation else date.today()
        if isinstance(due_date_value, str):
            due_date_value = datetime.fromisoformat(due_date_value).date()

        self.due_date_entry = tb.DateEntry(container, dateformat="%d/%m/%Y", firstweekday=6, width=40)
        self.due_date_entry.entry.delete(0, "end")
        self.due_date_entry.entry.insert(0, due_date_value.strftime("%d/%m/%Y"))
        self.due_date_entry.grid(row=row, column=0, sticky="ew", pady=(0, 15))
        row += 1

        # Status
        tb.Label(container, text="Status:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        self.status_var = tb.StringVar(value=self.obligation.get("status", "pending") if self.obligation else "pending")
        self.status_combo = tb.Combobox(
            container,
            textvariable=self.status_var,
            values=[label for label, _ in OBLIGATION_STATUSES],
            state="readonly",
            width=40,
        )
        self.status_combo.grid(row=row, column=0, sticky="ew", pady=(0, 15))

        # Map status value to display label
        if self.obligation:
            status_value = self.obligation.get("status", "pending")
            for label, value in OBLIGATION_STATUSES:
                if value == status_value:
                    self.status_combo.set(label)
                    break
        else:
            self.status_combo.set("Pendente")

        row += 1

        # Notes
        tb.Label(container, text="Notas:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        self.notes_text = tb.Text(container, height=4, width=40)
        self.notes_text.grid(row=row, column=0, sticky="ew", pady=(0, 15))

        if self.obligation:
            notes = self.obligation.get("notes")
            if notes:
                self.notes_text.insert("1.0", notes)

        row += 1

        # Configure grid
        container.columnconfigure(0, weight=1)

        # Buttons
        buttons_frame = tb.Frame(self)
        buttons_frame.pack(fill=X, padx=20, pady=(0, 20))

        tb.Button(
            buttons_frame,
            text="Cancelar",
            command=self._on_cancel,
            bootstyle="secondary",
            width=15,
        ).pack(side=RIGHT, padx=(5, 0))

        tb.Button(
            buttons_frame,
            text="Salvar",
            command=self._on_save,
            bootstyle="success",
            width=15,
        ).pack(side=RIGHT)

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        self.result = None
        self.destroy()

    def _on_save(self) -> None:
        """Handle save button."""
        # Validate
        title = self.title_var.get().strip()
        if not title:
            Messagebox.show_error("Título é obrigatório", "Validação", parent=self)
            self.title_entry.focus()
            return

        # Get kind value from display label
        kind_label = self.kind_combo.get()
        kind_value = next((value for label, value in OBLIGATION_KINDS if label == kind_label), "OUTRO")

        # Get status value from display label
        status_label = self.status_combo.get()
        status_value = next((value for label, value in OBLIGATION_STATUSES if label == status_label), "pending")

        # Get due date
        due_date_str = self.due_date_entry.entry.get()
        try:
            due_date = datetime.strptime(due_date_str, "%d/%m/%Y").date()
        except ValueError:
            Messagebox.show_error("Data de vencimento inválida", "Validação", parent=self)
            self.due_date_entry.focus()
            return

        # Get notes
        notes = self.notes_text.get("1.0", "end-1c").strip() or None

        try:
            if self.obligation:
                # Edit mode
                self.result = update_obligation(
                    org_id=self.org_id,
                    obligation_id=self.obligation["id"],
                    title=title,
                    kind=kind_value if kind_value else None,
                    due_date=due_date,
                    status=status_value if status_value else None,
                    notes=notes,
                )
            else:
                # Create mode
                self.result = create_obligation(
                    org_id=self.org_id,
                    created_by=self.created_by,
                    client_id=self.client_id,
                    kind=kind_value,
                    title=title,
                    due_date=due_date,
                    status=status_value,
                    notes=notes,
                )

            # Success
            if self.on_success:
                self.on_success()

            self.destroy()

        except Exception as exc:
            logger.error("Failed to save obligation: %s", exc)
            Messagebox.show_error(f"Erro ao salvar: {exc}", "Erro", parent=self)
