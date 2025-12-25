# -*- coding: utf-8 -*-
"""hub_screen_layout.py - Funções de construção de layout do HUB.

MVC-REFAC-001: Layout separado do arquivo principal.
Mantém compatibilidade total via wrappers em hub_screen.py.

Responsabilidades:
- Construir painéis de UI (módulos, dashboard, notas)
- Aplicar grid layout de 3 colunas
- Configurar estilos e posicionamento de widgets
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


if TYPE_CHECKING:
    from src.modules.hub.views.hub_screen import HubScreen


logger = get_logger(__name__)


def build_notes_panel(screen: HubScreen) -> None:
    """Constrói painel de notas (MF-27: delega para HubNotesView).

    Args:
        screen: Instância do HubScreen
    """
    from src.modules.hub.views.hub_notes_view import HubNotesView

    # Get initial state from ViewModel
    org_id = screen.get_org_id()
    if org_id:
        # Load notes with author names cache
        state = screen._notes_vm.load(org_id, author_names_cache=screen.state.author_cache)
    else:
        # Empty state if no org_id
        state = screen._notes_vm.state

    # Preparar callbacks (wrappers para ignorar retorno tuple do controller)
    def wrap_edit(note_id: str) -> None:
        screen._notes_controller.handle_edit_note_click(note_id)

    def wrap_delete(note_id: str) -> None:
        screen._notes_controller.handle_delete_note_click(note_id)

    def wrap_pin(note_id: str) -> None:
        screen._notes_controller.handle_toggle_pin(note_id)

    def wrap_done(note_id: str) -> None:
        screen._notes_controller.handle_toggle_done(note_id)

    # Build panel using HubNotesView (MF-27)
    notes_view = HubNotesView(
        screen,
        state=state,
        on_add_note_click=screen._on_add_note_clicked,
        on_edit_note_click=wrap_edit,
        on_delete_note_click=wrap_delete,
        on_toggle_pin_click=wrap_pin,
        on_toggle_done_click=wrap_done,
        current_user_email=screen._get_email_safe(),
    )
    # MF-34: Guardar referência para usar em render_notes
    screen._notes_view = notes_view
    screen.notes_panel = notes_view.build()

    # Store references to widgets for compatibility with existing code
    screen.notes_history = notes_view.notes_history
    screen.new_note = notes_view.new_note
    screen.btn_add_note = notes_view.btn_add_note

    # Renderizar estado inicial (evita painel em branco)
    if org_id:
        notes_view.render_loading()
    else:
        notes_view.render_empty("Aguardando autenticação...")

    # MF-15-C: Injetar referência na HubScreenView também
    if hasattr(screen, "_hub_view") and screen._hub_view:
        screen._hub_view._notes_view = notes_view


def setup_layout(screen: HubScreen) -> None:
    """Configura layout grid de 3 colunas (módulos | dashboard | notas).

    Args:
        screen: Instância do HubScreen
    """
    from src.modules.hub.layout import apply_hub_notes_right

    widgets = {
        "modules_panel": screen.modules_panel,
        "spacer": screen.center_spacer,
        "notes_panel": screen.notes_panel,
    }
    apply_hub_notes_right(screen, widgets)
