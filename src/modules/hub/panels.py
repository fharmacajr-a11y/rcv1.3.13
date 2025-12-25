"""Builders for HubScreen UI panels."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Callable

import ttkbootstrap as tb

from src.modules.hub.constants import HUB_TITLE, NEW_NOTE_LABEL, PAD_OUTER
from src.modules.hub.views.notes_text_renderer import render_notes_text
from src.modules.hub.views.notes_text_interactions import install_notes_context_menu

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
    current_user_email: str | None = None,
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
        current_user_email: Email do usuário atual (para validação de permissão).

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

    # Render notes from state using new renderer
    _render_notes_to_text_widget(notes_history, state)

    # Install context menu for notes (copiar/apagar)
    install_notes_context_menu(
        notes_history,
        on_delete_note_click=on_delete_note_click,
        current_user_email=current_user_email,
    )

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
    """Renderiza notas de NotesViewState no widget Text usando o renderer clean.

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

    # Usar o novo renderer para layout clean (estilo chat)
    # Converter NoteItemView objects para dicts para compatibilidade
    notes_dicts = []
    for note in state.notes:
        # Usar author_name do state se já estiver resolvido, senão email
        notes_dicts.append(
            {
                "id": note.id,
                "author_email": note.author_email,
                "author_name": note.author_name if note.author_name else note.author_email,
                "created_at": note.created_at,
                "body": note.body,
            }
        )

    # Callback para resolver nome (fallback caso author_name não venha preenchido)
    def resolve_name(email: str) -> str:
        """Resolve email para nome de exibição usando authors_service."""
        if not email:
            return "Usuário"

        # Tentar usar authors_service (with minimal screen mock)
        try:
            from src.modules.hub.services.authors_service import _load_env_author_names, AUTHOR_NAMES

            email_lower = email.strip().lower()

            # 1) Tentar RC_INITIALS_MAP do .env
            env_names = _load_env_author_names()
            if email_lower in env_names:
                return env_names[email_lower]

            # 2) Tentar AUTHOR_NAMES hardcoded
            if email_lower in AUTHOR_NAMES:
                return AUTHOR_NAMES[email_lower]

            # 3) Fallback: prefixo do email
            return email.split("@")[0].replace(".", " ").title()
        except Exception:
            # Fallback seguro
            return email.split("@")[0].replace(".", " ").title() if email else "Usuário"

    # Renderizar usando o helper
    render_notes_text(
        text_widget,
        notes_dicts,
        resolve_display_name=resolve_name,
        author_tags_dict={},  # Sem tags de cor neste contexto (panels.py não tem hub_screen)
        ensure_author_tag_fn=None,  # Sem ensure_author_tag (fallback usa get_author_color)
    )
