"""Builders for HubScreen UI panels."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Callable

import ttkbootstrap as tb

from src.modules.hub.constants import HUB_TITLE, NEW_NOTE_LABEL, PAD_OUTER
from src.modules.hub.notes_rendering import get_author_color

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import NotesViewState


def build_notes_panel(
    parent_frame,
    state: "NotesViewState",
    on_add_note_click: Callable[[], None] | None = None,
    on_edit_note_click: Callable[[str], None] | None = None,
    on_delete_note_click: Callable[[str], None] | None = None,
    on_toggle_pin_click: Callable[[str], None] | None = None,
    on_toggle_done_click: Callable[[str], None] | None = None,
) -> tb.Labelframe:
    """Create the shared notes panel consuming NotesViewState.

    Args:
        parent_frame: Parent container widget.
        state: NotesViewState with notes list and metadata.
        on_add_note_click: Callback quando usuário adiciona nota.
        on_edit_note_click: Callback quando usuário edita nota (recebe note_id).
        on_delete_note_click: Callback quando usuário deleta nota (recebe note_id).
        on_toggle_pin_click: Callback quando usuário fixa/desfixa nota (recebe note_id).
        on_toggle_done_click: Callback quando usuário marca/desmarca como feita (recebe note_id).

    Returns:
        O Labelframe do painel de notas.
    """
    notes_panel = tb.Labelframe(parent_frame, text=HUB_TITLE, padding=PAD_OUTER)
    notes_panel.columnconfigure(0, weight=1)
    notes_panel.rowconfigure(0, weight=1)  # history expands

    # --- History (read-only) ---
    history_frame = tb.Frame(notes_panel)
    history_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
    history_frame.columnconfigure(0, weight=1)
    history_frame.rowconfigure(0, weight=1)

    notes_history = tk.Text(
        history_frame,
        width=48,
        height=20,
        wrap="word",
        state="disabled",  # read-only
    )
    notes_history.grid(row=0, column=0, sticky="nsew")

    scrollbar = tb.Scrollbar(history_frame, command=notes_history.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    notes_history.configure(yscrollcommand=scrollbar.set)

    # Render notes from state
    _render_notes_to_text_widget(notes_history, state)

    # --- New note entry ---
    entry_frame = tb.Frame(notes_panel)
    entry_frame.grid(row=1, column=0, sticky="ew", pady=(0, 0))
    entry_frame.columnconfigure(0, weight=1)

    tb.Label(entry_frame, text=NEW_NOTE_LABEL, font=("", 9)).grid(row=0, column=0, sticky="w", pady=(0, 4))

    new_note_entry = tk.Text(entry_frame, height=3, wrap="word")
    new_note_entry.grid(row=1, column=0, sticky="ew", pady=(0, 6))

    btn_add_note = tb.Button(
        entry_frame,
        text="Adicionar",
        command=on_add_note_click if on_add_note_click else None,
        bootstyle="primary",
    )
    btn_add_note.grid(row=2, column=0, sticky="e")

    # Store widgets for external access (HubScreen compatibility)
    notes_panel.notes_history = notes_history  # type: ignore[attr-defined]
    notes_panel.new_note = new_note_entry  # type: ignore[attr-defined]
    notes_panel.btn_add_note = btn_add_note  # type: ignore[attr-defined]

    return notes_panel


def _render_notes_to_text_widget(text_widget: tk.Text, state: "NotesViewState") -> None:
    """Renderiza notas de NotesViewState no widget Text.

    Args:
        text_widget: Widget Text onde as notas serão renderizadas.
        state: NotesViewState com a lista de notas formatadas.
    """
    text_widget.configure(state="normal")
    text_widget.delete("1.0", "end")

    # Show loading or error state
    if state.is_loading:
        text_widget.insert("end", "Carregando notas...\n")
        text_widget.configure(state="disabled")
        return

    if state.error_message:
        text_widget.insert("end", f"Erro ao carregar notas:\n{state.error_message}\n")
        text_widget.configure(state="disabled")
        return

    # Show notes from state
    if not state.notes:
        text_widget.insert("end", "Nenhuma anotação ainda.\n")
        text_widget.configure(state="disabled")
        return

    # Render each note
    for note in state.notes:
        # Use formatted_line from ViewModel
        line_text = note.formatted_line or f"[{note.created_at}] {note.author_name}: {note.body}"

        # Insert with tag for coloring (author-specific)
        tag_name = note.tag_name or note.author_email.lower()
        text_widget.insert("end", line_text + "\n", tag_name)

        # Configure tag color if needed (basic approach - could be enhanced)
        if tag_name and not text_widget.tag_cget(tag_name, "foreground"):
            # Use helper para obter cor do autor
            color = get_author_color(tag_name)
            text_widget.tag_configure(tag_name, foreground=color)

    text_widget.configure(state="disabled")
