"""View do painel de Notas do Hub (lateral direita).

Extraído de HubScreen na MF-27 para reduzir o tamanho do monolito.
MF-33: Adiciona métodos de cenário (loading/error/empty/notes) para centralizar renderização.
MF-34: Adiciona implementação completa de render_notes (movida de HubScreen).

Este módulo é responsável APENAS pela construção visual do painel lateral
direito com as notas compartilhadas.
"""

import logging
from tkinter import TclError
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
import tkinter as tk

from src.modules.hub.colors import _ensure_author_tag
from src.modules.hub.services.authors_service import get_author_display_name
from src.modules.hub.utils import _normalize_note
from src.modules.hub.views.hub_notes_view_constants import (
    MSG_EMPTY_DEFAULT,
    MSG_ERROR_PREFIX,
    MSG_LOADING,
)
from src.modules.hub.views.hub_screen_helpers import (
    calculate_notes_content_hash,
    should_skip_render_empty_notes,
)
from src.modules.hub.views.notes_panel_view import NotesViewCallbacks, build_notes_side_panel
from src.modules.hub.views.notes_text_renderer import render_notes_text
from src.modules.hub.views.notes_text_interactions import install_notes_context_menu

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import NotesViewState

logger = logging.getLogger(__name__)


class HubNotesView:
    """View do painel de Notas do Hub (lateral direita).

    Responsabilidades:
    - Preparar callbacks para as ações de notas
    - Construir o painel de notas usando o helper existente
    - Expor widgets do painel para compatibilidade

    Esta classe NÃO conhece HubScreen diretamente, apenas recebe:
    - parent: widget pai onde o painel será anexado
    - state: estado das notas (NotesViewState)
    - callbacks: callbacks para ações de notas
    """

    def __init__(
        self,
        parent: Any,
        *,
        state: "NotesViewState",
        on_add_note_click: Optional[Callable[[], None]] = None,
        on_edit_note_click: Optional[Callable[[str], None]] = None,
        on_delete_note_click: Optional[Callable[[str], None]] = None,
        on_toggle_pin_click: Optional[Callable[[str], None]] = None,
        on_toggle_done_click: Optional[Callable[[str], None]] = None,
        current_user_email: Optional[str] = None,
    ):
        """Inicializa a view do painel de notas.

        Args:
            parent: Widget pai (onde o painel será criado)
            state: Estado das notas (NotesViewState)
            on_add_note_click: Callback para adicionar nota
            on_edit_note_click: Callback para editar nota (recebe note_id)
            on_delete_note_click: Callback para deletar nota (recebe note_id)
            on_toggle_pin_click: Callback para fixar/desafixar nota (recebe note_id)
            on_toggle_done_click: Callback para marcar/desmarcar como feita (recebe note_id)
            current_user_email: Email do usuário atual (para validação de permissão)
        """
        self._parent = parent
        self._state = state
        self._on_add_note_click = on_add_note_click
        self._on_edit_note_click = on_edit_note_click
        self._on_delete_note_click = on_delete_note_click
        self._on_toggle_pin_click = on_toggle_pin_click
        self._on_toggle_done_click = on_toggle_done_click
        self._current_user_email = current_user_email

        self.notes_panel: tk.LabelFrame | None = None
        self.notes_history: Any = None
        self.new_note: Any = None
        self.btn_add_note: Any = None

        # MF-34: Atributo para cache de hash de renderização
        self._last_render_hash: Optional[str] = None

    def build(self) -> tk.LabelFrame:
        """Constrói e retorna o frame do painel de notas.

        Este método cria:
        - Frame lateral direito com notas compartilhadas
        - Lista de notas com botões de ação
        - Botão de adicionar nova nota

        Returns:
            O frame do painel de notas (Labelframe)
        """
        # Preparar callbacks usando o container NotesViewCallbacks
        callbacks = NotesViewCallbacks(
            on_add_note_click=self._on_add_note_click,
            on_edit_note_click=self._on_edit_note_click,
            on_delete_note_click=self._on_delete_note_click,
            on_toggle_pin_click=self._on_toggle_pin_click,
            on_toggle_done_click=self._on_toggle_done_click,
            current_user_email=self._current_user_email,
        )

        # Build panel using helper (extrai lógica de UI)
        self.notes_panel = build_notes_side_panel(
            parent=self._parent,
            state=self._state,
            callbacks=callbacks,
        )

        # Store references to widgets for compatibility with existing code
        self.notes_history = self.notes_panel.notes_history  # type: ignore[attr-defined]
        self.new_note = self.notes_panel.new_note  # type: ignore[attr-defined]
        self.btn_add_note = self.notes_panel.btn_add_note  # type: ignore[attr-defined]

        # Install context menu for notes (copiar/apagar)
        if self.notes_history:
            install_notes_context_menu(
                self.notes_history,
                on_delete_note_click=self._on_delete_note_click,
                current_user_email=self._current_user_email,
            )

        return self.notes_panel

    # =========================================================================
    # MF-33: Métodos de cenário para renderização (loading/error/empty/notes)
    # =========================================================================

    def render_loading(self) -> None:
        """Renderiza estado de loading (carregando notas).

        MF-33: Centraliza renderização de loading na view.

        Notas:
            - Limpa o histórico de notas
            - Exibe mensagem "Carregando notas..."
            - Desabilita botão de adicionar nota
        """
        if not self.notes_history:
            return

        try:
            if not self.notes_history.winfo_exists():
                return

            self.notes_history.configure(state="normal")
            self.notes_history.delete("1.0", "end")
            self.notes_history.insert("1.0", MSG_LOADING)
            self.notes_history.configure(state="disabled")

            # Desabilitar botão de adicionar durante loading
            if self.btn_add_note and self.btn_add_note.winfo_exists():
                self.btn_add_note.configure(state="disabled")
        except Exception:
            logger.debug("Erro ao renderizar loading de notas (widget pode não existir)", exc_info=True)
            pass  # Fail silently se widget não existir

    def render_empty(self, message: str = MSG_EMPTY_DEFAULT) -> None:
        """Renderiza estado vazio (sem notas).

        MF-33: Centraliza renderização de estado vazio na view.

        Args:
            message: Mensagem a ser exibida (padrão: MSG_EMPTY_DEFAULT)
        """
        if not self.notes_history:
            return

        try:
            if not self.notes_history.winfo_exists():
                return

            self.notes_history.configure(state="normal")
            self.notes_history.delete("1.0", "end")
            self.notes_history.insert("1.0", message)
            self.notes_history.configure(state="disabled")

            # Habilitar botão de adicionar (estado vazio = pode adicionar)
            if self.btn_add_note and self.btn_add_note.winfo_exists():
                self.btn_add_note.configure(state="normal")
        except Exception:
            logger.debug("Erro ao renderizar estado vazio de notas (widget pode não existir)", exc_info=True)
            pass

    def render_error(self, message: str) -> None:
        """Renderiza estado de erro.

        MF-33: Centraliza renderização de erro na view.

        Args:
            message: Mensagem de erro a ser exibida
        """
        if not self.notes_history:
            return

        try:
            if not self.notes_history.winfo_exists():
                return

            self.notes_history.configure(state="normal")
            self.notes_history.delete("1.0", "end")
            self.notes_history.insert("1.0", f"{MSG_ERROR_PREFIX}{message}")
            self.notes_history.configure(state="disabled")

            # Habilitar botão de adicionar mesmo em erro (pode tentar adicionar)
            if self.btn_add_note and self.btn_add_note.winfo_exists():
                self.btn_add_note.configure(state="normal")
        except Exception:
            logger.debug("Erro ao renderizar estado de erro de notas (widget pode não existir)", exc_info=True)
            pass

    def render_notes(
        self,
        notes: List[Dict[str, Any]],
        *,
        force: bool = False,
        author_tags: Dict[str, str],
        author_names_cache: Optional[Dict[str, Tuple[str, float]]] = None,
        hub_screen: Any = None,
        debug_logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Renderiza lista de notas no histórico usando o renderer clean (estilo chat).

        MF-34: Implementação completa movida de HubScreen.render_notes.
        Atualizada para usar notes_text_renderer para layout limpo.

        Args:
            notes: Lista de dicionários com dados das notas
            force: Se True, ignora cache de hash e força re-renderização
            author_tags: Dicionário de tags de cores por autor (email → tag_name)
            author_names_cache: Cache de nomes de autores (email → (nome, timestamp))
            hub_screen: Referência ao HubScreen (para get_author_display_name)
            debug_logger: Logger de debug opcional (para _dlog)

        Notas:
            - Normaliza entrada (tuplas/listas → dicts)
            - Skip se lista vazia ou hash igual (otimização)
            - Usa novo renderer para layout clean (blocos separados)
            - Scrollar para o fim após renderização
        """
        # Normalizar entrada: converter tuplas/listas para dicts
        notes = [_normalize_note(x) for x in (notes or [])]

        # NÃO apaga se vier vazio/None (evita 'branco' e piscas)
        if should_skip_render_empty_notes(notes):
            if debug_logger:
                debug_logger("render_skip_empty")
            return

        # Hash de conteúdo pra evitar re-render desnecessário
        render_hash = calculate_notes_content_hash(notes)

        # Se não forçado, verificar se hash é igual (skip re-render)
        if not force:
            if render_hash == self._last_render_hash:
                if debug_logger:
                    debug_logger("render_skip_samehash")
                return

        self._last_render_hash = render_hash

        try:
            # 1) Verificar se o atributo existe e não é None
            if not hasattr(self, "notes_history") or self.notes_history is None:
                logger.warning("Hub: notes_history ausente ao renderizar; pulando atualização de notas.")
                return

            # 2) Verificar se o widget Tk ainda existe
            if not self.notes_history.winfo_exists():
                logger.warning("Hub: notes_history destruído (frame/aba fechada?); pulando atualização de notas.")
                return

            # Callback para resolver nomes de autores usando hub_screen
            def resolve_name(email: str) -> str:
                if hub_screen and email:
                    return get_author_display_name(hub_screen, email, start_async_fetch=True)
                return email.split("@")[0].title() if email else "Usuário"

            # Usar o novo renderer para layout clean (estilo chat/WhatsApp)
            render_notes_text(
                self.notes_history,
                notes,
                resolve_display_name=resolve_name,
                author_tags_dict=author_tags,
                ensure_author_tag_fn=_ensure_author_tag,
            )

        except TclError:
            logger.exception("Hub: erro crítico ao renderizar lista de notas.")
        except Exception:
            logger.exception("Hub: erro crítico ao renderizar lista de notas.")
            try:
                self.notes_history.configure(state="disabled")
            except Exception as exc:  # noqa: BLE001
                logger.debug("[HUB] Falha ao restaurar estado disabled: %s", exc)
