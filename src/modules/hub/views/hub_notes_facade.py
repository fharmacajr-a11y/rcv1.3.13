# -*- coding: utf-8 -*-
"""MF-23: HubNotesFacade - Encapsula lógica de notas do HubScreen.

Este módulo centraliza toda a lógica relacionada a notas (criação, edição,
renderização, polling, realtime) do HubScreen, transformando-o em um
thin orchestrator.

Responsabilidades:
- Coordenar operações de notas (adicionar, editar, excluir, pin, done)
- Gerenciar renderização de notas via HubNotesRenderer
- Coordenar polling e refresh de notas
- Gerenciar eventos realtime de notas
- Atualizar estado de UI de notas
- Coletar informações de debug sobre notas

Benefícios:
- Reduz linhas em hub_screen.py (~60-80 linhas removidas)
- Centraliza lógica de notas em uma façade
- Facilita testes de notas isoladamente
- Melhora separação de concerns
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    pass

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


from src.modules.hub.services.authors_service import debug_resolve_author
from src.modules.hub.views.hub_debug_helpers import collect_full_notes_debug

logger = get_logger(__name__)


class HubNotesFacade:
    """MF-23: Centraliza operações de notas do HubScreen.

    Esta façade encapsula toda a lógica de notas, incluindo:
    - Criação, edição, exclusão de notas
    - Renderização e atualização de UI
    - Polling e eventos realtime
    - Debug e diagnóstico

    Args:
        parent: Widget pai (HubScreen) para posicionar diálogos e acessar widgets
        notes_controller: Controller de notas (handle_add_note_click, etc.)
        hub_controller: Controller principal do Hub (refresh_notes, etc.)
        notes_renderer: Renderer de notas para atualização de UI
        polling_service: Serviço de polling de notas
        state_manager: StateManager para mutações de estado
        get_org_id: Callable que retorna org_id atual
        get_email: Callable que retorna email do usuário
        debug_logger: Logger opcional para debug
    """

    def __init__(
        self,
        parent: Any,
        notes_controller: Any,
        hub_controller: Any,
        notes_renderer: Any,
        polling_service: Any,
        state_manager: Any,
        get_org_id: Callable[[], Optional[str]],
        get_email: Callable[[], Optional[str]],
        debug_logger: Optional[Any] = None,
    ) -> None:
        """Inicializa façade de notas.

        Args:
            parent: Widget pai (HubScreen)
            notes_controller: NotesController
            hub_controller: HubScreenController
            notes_renderer: HubNotesRenderer
            polling_service: HubPollingService
            state_manager: HubStateManager
            get_org_id: Callable para obter org_id
            get_email: Callable para obter email do usuário
            debug_logger: Logger opcional para debug
        """
        self._parent = parent
        self._notes_controller = notes_controller
        self._hub_controller = hub_controller
        self._notes_renderer = notes_renderer
        self._polling_service = polling_service
        self._state = state_manager
        self._get_org_id = get_org_id
        self._get_email = get_email
        self._debug_logger = debug_logger

    # ==============================================================================
    # OPERAÇÕES DE NOTAS (CRUD + Pin/Done)
    # ==============================================================================

    def on_add_note(self, note_text: str) -> Tuple[bool, str]:
        """Adiciona nova nota (MF-23).

        Args:
            note_text: Texto da nota a ser adicionada

        Returns:
            Tuple (success, message)
        """
        if self._debug_logger:
            self._debug_logger("NotesFacade: on_add_note")

        try:
            # Delegar ao controller
            success, message = self._notes_controller.handle_add_note_click(note_text)

            if success:
                logger.debug("Nota adicionada com sucesso via NotesFacade")
            else:
                if message:
                    logger.debug(f"Falha ao adicionar nota: {message}")

            return success, message
        except Exception as e:
            logger.exception("Erro ao adicionar nota via NotesFacade")
            return False, str(e)

    def on_edit_note(self, note_id: str) -> Tuple[bool, Optional[str]]:
        """Edita nota existente (MF-23).

        Args:
            note_id: ID da nota a ser editada

        Returns:
            Tuple (success, message opcional)
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: on_edit_note({note_id})")

        return self._notes_controller.handle_edit_note_click(note_id)

    def on_delete_note(self, note_id: str) -> Tuple[bool, Optional[str]]:
        """Exclui nota existente (MF-23).

        Args:
            note_id: ID da nota a ser excluída

        Returns:
            Tuple (success, message opcional)
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: on_delete_note({note_id})")

        return self._notes_controller.handle_delete_note_click(note_id)

    def on_toggle_pin(self, note_id: str) -> Tuple[bool, Optional[str]]:
        """Alterna estado de pin da nota (MF-23).

        Args:
            note_id: ID da nota

        Returns:
            Tuple (success, message opcional)
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: on_toggle_pin({note_id})")

        return self._notes_controller.handle_toggle_pin(note_id)

    def on_toggle_done(self, note_id: str) -> Tuple[bool, Optional[str]]:
        """Alterna estado de done da nota (MF-23).

        Args:
            note_id: ID da nota

        Returns:
            Tuple (success, message opcional)
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: on_toggle_done({note_id})")

        return self._notes_controller.handle_toggle_done(note_id)

    # ==============================================================================
    # RENDERIZAÇÃO E ATUALIZAÇÃO DE UI
    # ==============================================================================

    def render_notes(self, notes: List[Dict[str, Any]], force: bool = False) -> None:
        """Renderiza lista de notas no histórico (MF-23).

        Args:
            notes: Lista de dicionários com dados das notas
            force: Se True, ignora cache de hash e força re-renderização
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: render_notes({len(notes)} notas, force={force})")

        # Delegar para HubNotesRenderer
        self._notes_renderer.render_notes(
            notes=notes,
            force=force,
            hub_screen=self._parent,  # Para compatibilidade com código existente
        )

    def update_notes_ui_state(self) -> None:
        """Atualiza estado do botão/placeholder baseado em org_id (MF-23)."""
        if self._debug_logger:
            self._debug_logger("NotesFacade: update_notes_ui_state")

        org_id = self._get_org_id()
        self._notes_renderer.update_notes_ui_state(
            has_org_id=bool(org_id),
            btn_add_note=self._parent.btn_add_note,
            new_note_field=self._parent.new_note,
        )

    # ==============================================================================
    # POLLING E REFRESH
    # ==============================================================================

    def start_notes_polling(self) -> None:
        """Inicia polling de notas e refresh de cache de autores (MF-23)."""
        if self._debug_logger:
            self._debug_logger("NotesFacade: start_notes_polling")

        self._polling_service.start_notes_polling()

    def poll_notes_if_needed(self) -> None:
        """Polling de notas se necessário (MF-23)."""
        if self._debug_logger:
            self._debug_logger("NotesFacade: poll_notes_if_needed")

        self._hub_controller.refresh_notes(force=False)

    def poll_notes_impl(self, force: bool = False) -> None:
        """Implementação de polling de notas (MF-23).

        Args:
            force: Se True, força refresh mesmo que recente
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: poll_notes_impl(force={force})")

        self._polling_service.poll_notes(force=force)

    def refresh_notes_async(self, force: bool = False) -> None:
        """Refresh assíncrono de notas (MF-23).

        Args:
            force: Se True, força refresh mesmo que recente
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: refresh_notes_async(force={force})")

        self._hub_controller.refresh_notes(force=force)

    def retry_after_table_missing(self) -> None:
        """Retry após erro de tabela ausente (MF-23)."""
        if self._debug_logger:
            self._debug_logger("NotesFacade: retry_after_table_missing")

        self._hub_controller.refresh_notes(force=True)

    # ==============================================================================
    # REALTIME E EVENTOS
    # ==============================================================================

    def on_realtime_note(self, row: dict) -> None:
        """Handler de eventos realtime de notas (MF-23).

        Args:
            row: Dados da nota do evento realtime
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: on_realtime_note({row.get('id', 'unknown')})")

        self._hub_controller.on_realtime_note(row)

    def append_note_incremental(self, row: dict) -> None:
        """Adiciona nota incremental (MF-23).

        Args:
            row: Dados da nota a ser adicionada incrementalmente
        """
        if self._debug_logger:
            self._debug_logger(f"NotesFacade: append_note_incremental({row.get('id', 'unknown')})")

        self._hub_controller._append_note_incremental(row)

    # ==============================================================================
    # DEBUG E DIAGNÓSTICO
    # ==============================================================================

    def collect_notes_debug(self) -> dict:
        """Coleta informações de debug sobre notas (MF-23).

        Returns:
            Dicionário com informações de debug
        """
        if self._debug_logger:
            self._debug_logger("NotesFacade: collect_notes_debug")

        state = self._state.state

        return collect_full_notes_debug(
            get_org_id=self._get_org_id,
            notes_last_data=state.notes_last_data,
            notes_last_snapshot=state.notes_last_snapshot,
            author_names_cache=state.author_cache,
            email_prefix_map=state.email_prefix_map,
            notes_cache_loaded=state.names_cache_loaded,
            notes_last_refresh=getattr(self._parent, "_names_last_refresh", None),
            polling_active=state.polling_active,
            live_sync_on=state.live_sync_on,
            current_user_email=self._get_email(),
            debug_resolve_author_fn=lambda row, author_email: debug_resolve_author(self._parent, author_email),
        )
