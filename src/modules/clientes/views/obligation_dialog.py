# -*- coding: utf-8 -*-
"""Dialog for creating/editing regulatory obligations."""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox
from typing import Callable

from src.db.domain_types import RegObligationRow
from src.features.regulations.service import (
    create_obligation,
    update_obligation,
)

# CustomTkinter via SSoT
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

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


# Determina classe base para Toplevel
if HAS_CUSTOMTKINTER and ctk is not None:
    _DialogBase = ctk.CTkToplevel  # type: ignore[misc,assignment]
else:
    _DialogBase = tk.Toplevel  # type: ignore[misc,assignment]


class ObligationDialog(_DialogBase):  # type: ignore[misc]
    """Dialog for creating or editing a regulatory obligation."""

    def __init__(
        self,
        parent: tk.Misc,
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
        if hasattr(parent, 'winfo_x'):
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
            self.geometry(f"+{x}+{y}")

        # Focus first field
        self.kind_combo.focus()

    def _build_ui(self) -> None:
        """Build dialog UI."""
        # Main container
        if HAS_CUSTOMTKINTER and ctk is not None:
            container = ctk.CTkFrame(self, fg_color="transparent")
        else:
            container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Form fields
        row = 0

        # Kind
        if HAS_CUSTOMTKINTER and ctk is not None:
            ctk.CTkLabel(container, text="Tipo de obrigação:", font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky="w", pady=(0, 5)
            )
        else:
            tk.Label(container, text="Tipo de obrigação:", font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky="w", pady=(0, 5)
            )
        row += 1

        self.kind_var = tk.StringVar(value=self.obligation["kind"] if self.obligation else "SNGPC")
        
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.kind_combo = ctk.CTkOptionMenu(
                container,
                variable=self.kind_var,
                values=[label for label, _ in OBLIGATION_KINDS],
                width=400,
            )
        else:
            
            self.kind_combo = ctk.CTkComboBox(
                container,
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
        if HAS_CUSTOMTKINTER and ctk is not None:
            ctk.CTkLabel(container, text="Título:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        else:
            tk.Label(container, text="Título:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        self.title_var = tk.StringVar(value=self.obligation.get("title", "") if self.obligation else "")
        
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.title_entry = ctk.CTkEntry(container, textvariable=self.title_var, width=400)
        else:
            self.title_entry = tk.Entry(container, textvariable=self.title_var, width=40)
        self.title_entry.grid(row=row, column=0, sticky="ew", pady=(0, 15))
        row += 1

        # Due date
        if HAS_CUSTOMTKINTER and ctk is not None:
            ctk.CTkLabel(container, text="Data de vencimento:", font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky="w", pady=(0, 5)
            )
        else:
            tk.Label(container, text="Data de vencimento:", font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky="w", pady=(0, 5)
            )
        row += 1

        due_date_value = self.obligation["due_date"] if self.obligation else date.today()
        if isinstance(due_date_value, str):
            due_date_value = datetime.fromisoformat(due_date_value).date()

        # DateEntry: usando tk.Entry com formato de data validado
        self.due_date_entry = tk.Entry(container, width=40)
        self.due_date_entry.insert(0, due_date_value.strftime("%d/%m/%Y"))
        # Adiciona atributo .entry para compatibilidade com o resto do código
        self.due_date_entry.entry = self.due_date_entry  # type: ignore[attr-defined]
        
        self.due_date_entry.grid(row=row, column=0, sticky="ew", pady=(0, 15))
        row += 1

        # Status
        if HAS_CUSTOMTKINTER and ctk is not None:
            ctk.CTkLabel(container, text="Status:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        else:
            tk.Label(container, text="Status:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        self.status_var = tk.StringVar(value=self.obligation.get("status", "pending") if self.obligation else "pending")
        
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.status_combo = ctk.CTkOptionMenu(
                container,
                variable=self.status_var,
                values=[label for label, _ in OBLIGATION_STATUSES],
                width=400,
            )
        else:
            
            self.status_combo = ctk.CTkComboBox(
                container,
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
        if HAS_CUSTOMTKINTER and ctk is not None:
            ctk.CTkLabel(container, text="Notas:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        else:
            tk.Label(container, text="Notas:", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        if HAS_CUSTOMTKINTER and ctk is not None:
            self.notes_text = ctk.CTkTextbox(container, height=100, width=400)
        else:
            from tkinter import scrolledtext
            self.notes_text = scrolledtext.ScrolledText(container, height=4, width=40)
        self.notes_text.grid(row=row, column=0, sticky="ew", pady=(0, 15))

        if self.obligation:
            notes = self.obligation.get("notes")
            if notes:
                if HAS_CUSTOMTKINTER and isinstance(self.notes_text, ctk.CTkTextbox):
                    self.notes_text.insert("1.0", notes)
                else:
                    self.notes_text.insert("1.0", notes)

        row += 1

        # Configure grid
        container.columnconfigure(0, weight=1)

        # Buttons
        if HAS_CUSTOMTKINTER and ctk is not None:
            buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        else:
            buttons_frame = tk.Frame(self)
        buttons_frame.pack(fill="x", padx=20, pady=(0, 20))

        if HAS_CUSTOMTKINTER and ctk is not None:
            ctk.CTkButton(
                buttons_frame,
                text="Cancelar",
                command=self._on_cancel,
                width=120,
                fg_color="#6c757d",
                hover_color="#5a6268",
            ).pack(side="right", padx=(5, 0))

            ctk.CTkButton(
                buttons_frame,
                text="Salvar",
                command=self._on_save,
                width=120,
                fg_color="#28a745",
                hover_color="#218838",
            ).pack(side="right")
        else:
            tk.Button(
                buttons_frame,
                text="Cancelar",
                command=self._on_cancel,
                width=15,
            ).pack(side="right", padx=(5, 0))

            tk.Button(
                buttons_frame,
                text="Salvar",
                command=self._on_save,
                width=15,
            ).pack(side="right")

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        self.result = None
        self.destroy()

    def _on_save(self) -> None:
        """Handle save button."""
        # Validate
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Validação", "Título é obrigatório", parent=self)
            self.title_entry.focus()
            return

        # Get kind value from display label
        kind_label = self.kind_var.get()  # CTkOptionMenu usa variable diretamente
        kind_value = next((value for label, value in OBLIGATION_KINDS if label == kind_label), "OUTRO")

        # Get status value from display label
        status_label = self.status_var.get()
        status_value = next((value for label, value in OBLIGATION_STATUSES if label == status_label), "pending")

        # Get due date
        due_date_str = self.due_date_entry.entry.get()
        try:
            due_date = datetime.strptime(due_date_str, "%d/%m/%Y").date()
        except ValueError:
            messagebox.showerror("Validação", "Data de vencimento inválida", parent=self)
            self.due_date_entry.focus()
            return

        # Get notes
        if HAS_CUSTOMTKINTER and isinstance(self.notes_text, ctk.CTkTextbox):
            notes = self.notes_text.get("1.0", "end-1c").strip() or None
        else:
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
            messagebox.showerror("Erro", f"Erro ao salvar: {exc}", parent=self)
