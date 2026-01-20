from __future__ import annotations

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import (
    APP_BG, SURFACE_DARK, INNER_SURFACE, 
    FONT_TITLE, FONT_SECTION, FONT_BODY, TITLE_FONT, TEXT_PRIMARY,
    CARD_RADIUS,
)

"""Builders for HubScreen UI panels."""

import tkinter as tk
from typing import TYPE_CHECKING, Callable

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
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
) -> ctk.CTkFrame:  # Usando ctk.CTkFrame
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
    # Painel externo compatível com grid - MICROFASE 35: cinza escuro sem borda
    notes_panel = ctk.CTkFrame(
        parent_frame,
        fg_color=SURFACE_DARK,
        bg_color=APP_BG,  # MICROFASE 35: evita vazamento nos cantos
        border_width=0,
        corner_radius=CARD_RADIUS,
    )
    
    # Título interno - usando novo token TITLE_FONT
    title_label = ctk.CTkLabel(
        notes_panel, 
        text=HUB_TITLE, 
        font=TITLE_FONT,
        text_color=TEXT_PRIMARY,
        fg_color="transparent"
    )
    title_label.pack(fill="x", padx=PAD_OUTER, pady=(PAD_OUTER, 8))
    
    # Container de conteúdo
    content_frame = ctk.CTkFrame(notes_panel, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=PAD_OUTER, pady=(0, PAD_OUTER))
    content_frame.columnconfigure(0, weight=1)
    content_frame.rowconfigure(0, weight=1)  # history expands

    # --- History (read-only) ---
    if HAS_CUSTOMTKINTER and ctk is not None:
        history_frame = ctk.CTkFrame(content_frame)
    else:
        history_frame = tk.Frame(content_frame)
    history_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
    history_frame.columnconfigure(0, weight=1)
    history_frame.rowconfigure(0, weight=1)

    if HAS_CUSTOMTKINTER and ctk is not None:
        notes_history = ctk.CTkTextbox(
            history_frame,
            width=480,
            height=400,
            wrap="word",
            font=FONT_BODY,
            fg_color=INNER_SURFACE,
        )
        # Ajustar padding interno do textbox (acesso ao tk.Text interno)
        try:
            notes_history._textbox.configure(padx=10, pady=8)
            notes_history._textbox.configure(spacing1=2, spacing3=2)  # line spacing
        except (AttributeError, Exception):
            pass
        # Para read-only no CTkTextbox, usar helper em vez de state=disabled
        from src.ui.ctk_text_compat import configure_text_readonly
        configure_text_readonly(notes_history)
    else:
        notes_history = tk.Text(
            history_frame,
            width=48,
            height=20,
            wrap="word",
            font=FONT_BODY,
            state="disabled",  # read-only
        )
        # Usar ctk.CTkScrollbar apenas se CTk disponível
        if HAS_CUSTOMTKINTER and ctk is not None:
            scrollbar = ctk.CTkScrollbar(history_frame, command=notes_history.yview)
            scrollbar.grid(row=0, column=1, sticky="ns")
            notes_history.configure(yscrollcommand=scrollbar.set)
        
    notes_history.grid(row=0, column=0, sticky="nsew")

    # Render notes from state using new renderer
    _render_notes_to_text_widget(notes_history, state)

    # Install context menu for notes (copiar/apagar)
    install_notes_context_menu(
        notes_history,
        on_delete_note_click=on_delete_note_click,
        current_user_email=current_user_email,
    )

    # --- New note entry ---
    if HAS_CUSTOMTKINTER and ctk is not None:
        entry_frame = ctk.CTkFrame(content_frame, fg_color=SURFACE_DARK, corner_radius=8)
    else:
        entry_frame = tk.Frame(content_frame)
    entry_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
    entry_frame.columnconfigure(0, weight=1)

    if HAS_CUSTOMTKINTER and ctk is not None:
        label = ctk.CTkLabel(entry_frame, text=NEW_NOTE_LABEL, font=("", 9))
    else:
        label = tk.Label(entry_frame, text=NEW_NOTE_LABEL, font=("", 9))
    label.grid(row=0, column=0, sticky="w", pady=(0, 4))

    if HAS_CUSTOMTKINTER and ctk is not None:
        new_note_entry = ctk.CTkTextbox(
            entry_frame, 
            height=60, 
            wrap="word",
            fg_color=INNER_SURFACE,
            corner_radius=6
        )
    else:
        new_note_entry = tk.Text(entry_frame, height=3, wrap="word")
    new_note_entry.grid(row=1, column=0, sticky="ew", pady=(0, 6))

    if HAS_CUSTOMTKINTER and ctk is not None:
        btn_add_note = ctk.CTkButton(
            entry_frame,
            text="Adicionar",
            command=on_add_note_click if on_add_note_click else None,
        )
    else:
        btn_add_note = tk.Button(
            entry_frame,
            text="Adicionar",
            command=on_add_note_click if on_add_note_click else None,
        )
    btn_add_note.grid(row=2, column=0, sticky="e")

    # Store widgets for external access (HubScreen compatibility)
    notes_panel.notes_history = notes_history  # type: ignore[attr-defined]
    notes_panel.new_note = new_note_entry  # type: ignore[attr-defined]
    notes_panel.btn_add_note = btn_add_note  # type: ignore[attr-defined]

    return notes_panel


def _render_notes_to_text_widget(text_widget, state: "NotesViewState") -> None:
    """Renderiza notas de NotesViewState no widget Text usando o renderer clean.

    Args:
        text_widget: Widget Text ou CTkTextbox onde as notas serão renderizadas.
        state: NotesViewState com a lista de notas formatadas.
    """
    from src.ui.ctk_text_compat import get_inner_text_widget
    
    # Para CTkTextbox, usar widget interno para operações de texto
    inner_widget = get_inner_text_widget(text_widget)
    
    if hasattr(text_widget, '_textbox'):
        # CTkTextbox: desabilitar binds temporariamente para edição
        inner_widget.unbind("<Key>")
        inner_widget.unbind("<<Paste>>")
    else:
        # tk.Text: usar configure normal
        text_widget.configure(state="normal")
    
    # Operações de texto usando o widget interno
    inner_widget.delete("1.0", "end")

    # Show loading or error state
    if state.is_loading:
        inner_widget.insert("end", "Carregando notas...\n")
        if hasattr(text_widget, '_textbox'):
            # CTkTextbox: reconfigurar como read-only
            from src.ui.ctk_text_compat import configure_text_readonly
            configure_text_readonly(text_widget)
        else:
            text_widget.configure(state="disabled")
        return

    if state.error_message:
        inner_widget.insert("end", f"Erro ao carregar notas:\n{state.error_message}\n")
        if hasattr(text_widget, '_textbox'):
            # CTkTextbox: reconfigurar como read-only
            from src.ui.ctk_text_compat import configure_text_readonly
            configure_text_readonly(text_widget)
        else:
            text_widget.configure(state="disabled")
        return

    # Show notes from state
    if not state.notes:
        inner_widget.insert("end", "Nenhuma anotação ainda.\n")
        if hasattr(text_widget, '_textbox'):
            # CTkTextbox: reconfigurar como read-only
            from src.ui.ctk_text_compat import configure_text_readonly
            configure_text_readonly(text_widget)
        else:
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
        inner_widget,  # Usar widget interno para CTkTextbox
        notes_dicts,
        resolve_display_name=resolve_name,
        author_tags_dict={},  # Sem tags de cor neste contexto (panels.py não tem hub_screen)
        ensure_author_tag_fn=None,  # Sem ensure_author_tag (fallback usa get_author_color)
    )

    if hasattr(text_widget, '_textbox'):
        # CTkTextbox: reconfigurar como read-only
        from src.ui.ctk_text_compat import configure_text_readonly
        configure_text_readonly(text_widget)
    else:
        # tk.Text: usar state disabled
        text_widget.configure(state="disabled")
