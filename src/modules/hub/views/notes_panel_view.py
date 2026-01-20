# -*- coding: utf-8 -*-
"""Notes panel view builder (lateral direito do HUB).

Este módulo contém apenas lógica de UI para construir o painel de notas.
Usa build_notes_panel de panels.py para renderizar a lista de notas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
import tkinter as tk

from src.modules.hub.panels import build_notes_panel

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import NotesViewState


class NotesViewCallbacks:
    """Container para callbacks do painel de notas."""

    def __init__(
        self,
        on_add_note_click: Callable[[], None] | None = None,
        on_edit_note_click: Callable[[str], None] | None = None,
        on_delete_note_click: Callable[[str], None] | None = None,
        on_toggle_pin_click: Callable[[str], None] | None = None,
        on_toggle_done_click: Callable[[str], None] | None = None,
        current_user_email: str | None = None,
    ):
        """Inicializa callbacks do painel de notas.

        Args:
            on_add_note_click: Callback quando usuário adiciona nota.
            on_edit_note_click: Callback quando usuário edita nota (recebe note_id).
            on_delete_note_click: Callback quando usuário deleta nota (recebe note_id).
            on_toggle_pin_click: Callback quando usuário fixa/desfixa nota (recebe note_id).
            on_toggle_done_click: Callback quando usuário marca/desmarca como feita (recebe note_id).
            current_user_email: Email do usuário atual (para validação de permissão).
        """
        self.on_add_note_click = on_add_note_click
        self.on_edit_note_click = on_edit_note_click
        self.on_delete_note_click = on_delete_note_click
        self.on_toggle_pin_click = on_toggle_pin_click
        self.on_toggle_done_click = on_toggle_done_click
        self.current_user_email = current_user_email


def build_notes_side_panel(
    parent: tk.Frame,
    state: "NotesViewState",
    callbacks: NotesViewCallbacks,
) -> tk.LabelFrame:
    """Constrói o painel de notas compartilhadas (lateral direita).

    Delega para build_notes_panel de panels.py para renderizar a lista.

    Args:
        parent: Frame pai onde o painel será criado.
        state: Estado das notas (NotesViewState).
        callbacks: Container com callbacks do painel.

    Returns:
        O Labelframe do painel de notas.
    """
    # Delegar para build_notes_panel (mantém compatibilidade)
    notes_panel = build_notes_panel(
        parent_frame=parent,
        state=state,
        on_add_note_click=callbacks.on_add_note_click,
        on_edit_note_click=callbacks.on_edit_note_click,
        on_delete_note_click=callbacks.on_delete_note_click,
        on_toggle_pin_click=callbacks.on_toggle_pin_click,
        on_toggle_done_click=callbacks.on_toggle_done_click,
        current_user_email=callbacks.current_user_email,
    )

    return notes_panel
