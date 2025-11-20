"""Builders for HubScreen UI panels."""

from __future__ import annotations

import tkinter as tk

import ttkbootstrap as tb

from src.modules.hub.actions import on_add_note_clicked as actions_on_add_note_clicked
from src.modules.hub.constants import HUB_TITLE, NEW_NOTE_LABEL, PAD_OUTER
from src.modules.hub.state import ensure_state


def build_notes_panel(screen, parent=None):
    """Create the shared notes panel and bind it to the given screen."""
    container = parent or screen

    # Reset author tags cache because the widget is being recreated
    state = ensure_state(screen)
    state.author_tags.clear()

    screen.notes_panel = tb.Labelframe(container, text=HUB_TITLE, padding=PAD_OUTER)
    right = screen.notes_panel
    right.columnconfigure(0, weight=1)
    right.rowconfigure(0, weight=1)  # history expands

    # --- History (read-only) ---
    history_frame = tb.Frame(right)
    history_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
    history_frame.columnconfigure(0, weight=1)
    history_frame.rowconfigure(0, weight=1)

    screen.notes_history = tk.Text(
        history_frame,
        width=48,
        height=20,
        wrap="word",
        state="disabled",  # read-only
    )
    screen.notes_history.grid(row=0, column=0, sticky="nsew")

    scrollbar = tb.Scrollbar(history_frame, command=screen.notes_history.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    screen.notes_history.configure(yscrollcommand=scrollbar.set)

    # --- New note entry ---
    entry_frame = tb.Frame(right)
    entry_frame.grid(row=1, column=0, sticky="ew", pady=(0, 0))
    entry_frame.columnconfigure(0, weight=1)

    tb.Label(entry_frame, text=NEW_NOTE_LABEL, font=("", 9)).grid(row=0, column=0, sticky="w", pady=(0, 4))

    screen.new_note = tk.Text(entry_frame, height=3, wrap="word")
    screen.new_note.grid(row=1, column=0, sticky="ew", pady=(0, 6))

    screen.btn_add_note = tb.Button(
        entry_frame,
        text="Adicionar",
        command=lambda: actions_on_add_note_clicked(screen),
        bootstyle="primary",
    )
    screen.btn_add_note.grid(row=2, column=0, sticky="e")

    return screen.notes_panel
