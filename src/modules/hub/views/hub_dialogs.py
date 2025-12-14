# -*- coding: utf-8 -*-
"""HubDialogs - Diálogos modais do HUB (edição de notas, confirmações).

Este módulo contém diálogos especializados que eram anteriormente métodos
do HubScreen. Extraído em MF-10 para reduzir tamanho e complexidade.

Responsabilidades:
- show_note_editor: Diálogo para criar/editar notas
- confirm_delete_note: Diálogo de confirmação de exclusão
- show_error/show_info: Wrappers de messageboxes
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any

import ttkbootstrap as tb


def show_note_editor(
    parent: tk.Misc,
    note_data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Mostra editor de nota em diálogo modal.

    Args:
        parent: Widget pai (para modal)
        note_data: Dados da nota para editar (None para criar nova).

    Returns:
        Dict com dados atualizados se confirmado, None se cancelado.

    Dict retornado contém:
        - body: str - Texto da nota
        - id: str | None - ID da nota (None para nova)
        - is_pinned: bool - Se está fixada
        - is_done: bool - Se está marcada como concluída
    """
    # Dialog setup
    dialog = tk.Toplevel(parent)
    dialog.title("Editar Nota" if note_data else "Nova Nota")
    dialog.geometry("500x350")
    dialog.transient(parent)
    dialog.grab_set()

    # Center dialog
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

    # Result container (mutable para closures)
    result = {"confirmed": False, "data": None}

    # Build UI
    frame = tb.Frame(dialog, padding=10)
    frame.pack(fill="both", expand=True)

    # Label
    tb.Label(frame, text="Texto da nota:").pack(anchor="w", pady=(0, 5))

    # Text widget with scrollbar
    text_frame = tb.Frame(frame)
    text_frame.pack(fill="both", expand=True, pady=(0, 10))

    scrollbar = tb.Scrollbar(text_frame)
    scrollbar.pack(side="right", fill="y")

    text_widget = tk.Text(
        text_frame,
        wrap="word",
        yscrollcommand=scrollbar.set,
        font=("Segoe UI", 10),
    )
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=text_widget.yview)

    # Populate text if editing
    if note_data and "body" in note_data:
        text_widget.insert("1.0", note_data["body"])
        text_widget.mark_set("insert", "1.0")  # Cursor no início

    # Focus on text
    text_widget.focus_set()

    # Buttons frame
    btn_frame = tb.Frame(frame)
    btn_frame.pack(fill="x")

    def on_confirm():
        """Handler para confirmação."""
        body = text_widget.get("1.0", "end-1c").strip()
        if not body:
            messagebox.showwarning(
                "Campo vazio",
                "O texto da nota não pode estar vazio.",
                parent=dialog,
            )
            return

        result["confirmed"] = True
        result["data"] = {
            "body": body,
            "id": note_data.get("id") if note_data else None,
            "is_pinned": note_data.get("is_pinned", False) if note_data else False,
            "is_done": note_data.get("is_done", False) if note_data else False,
        }
        dialog.destroy()

    def on_cancel():
        """Handler para cancelamento."""
        result["confirmed"] = False
        dialog.destroy()

    # Buttons
    tb.Button(
        btn_frame,
        text="Confirmar",
        bootstyle="success",
        command=on_confirm,
    ).pack(side="left", padx=(0, 5))

    tb.Button(
        btn_frame,
        text="Cancelar",
        bootstyle="secondary",
        command=on_cancel,
    ).pack(side="left")

    # Keyboard bindings
    dialog.bind("<Control-Return>", lambda e: on_confirm())
    dialog.bind("<Escape>", lambda e: on_cancel())

    # Wait for dialog
    dialog.wait_window()

    # Return result
    return result["data"] if result["confirmed"] else None


def confirm_delete_note(parent: tk.Misc, note_data: dict[str, Any]) -> bool:
    """Confirma exclusão de nota.

    Args:
        parent: Widget pai (para modal)
        note_data: Dados da nota a ser deletada.

    Returns:
        True se confirmado, False se cancelado.
    """
    body = note_data.get("body", "")
    preview = body[:50] + "..." if len(body) > 50 else body
    return messagebox.askyesno(
        "Confirmar exclusão",
        f"Excluir anotação:\n\n{preview}",
        parent=parent,
    )


def show_error(parent: tk.Misc, title: str, message: str) -> None:
    """Mostra mensagem de erro.

    Args:
        parent: Widget pai (para modal)
        title: Título do diálogo
        message: Mensagem de erro
    """
    messagebox.showerror(title, message, parent=parent)


def show_info(parent: tk.Misc, title: str, message: str) -> None:
    """Mostra mensagem informativa.

    Args:
        parent: Widget pai (para modal)
        title: Título do diálogo
        message: Mensagem informativa
    """
    messagebox.showinfo(title, message, parent=parent)
