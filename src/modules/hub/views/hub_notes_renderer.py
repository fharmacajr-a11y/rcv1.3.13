# -*- coding: utf-8 -*-
"""MF-20: Notes Renderer - Responsável pela renderização de notas.

Este módulo encapsula toda a lógica de renderização de notas,
reduzindo a complexidade do HubScreen e melhorando a separação de responsabilidades.

Extraído de hub_screen.py na MF-20 (Dezembro 2025).

Responsabilidades:
- Renderizar lista de notas no histórico
- Aplicar formatação de timestamps, autores, cores
- Gerenciar tooltips e tags de autores
- Coordenar com HubNotesView para atualização da UI
- NÃO contém lógica de negócio (sem chamadas a services/repos/timers)

Design:
- Usa Protocol para desacoplar do HubScreen concreto
- Recebe callbacks via interface mínima
- Delega renderização visual para HubNotesView
- Usa helpers de src/modules/hub/views/hub_helpers_notes.py para formatação
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Protocol

if TYPE_CHECKING:
    from src.modules.hub.views.hub_notes_view import HubNotesView
    from src.modules.hub.state import HubState

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)


logger = get_logger(__name__)


class NotesRenderCallbacks(Protocol):
    """Interface mínima que o renderer precisa da view principal.

    MF-20: Evita acoplamento direto com HubScreen.
    Permite testar o renderer com mocks.
    """

    def get_notes_view(self) -> "HubNotesView":
        """Retorna a instância do HubNotesView."""
        ...

    def get_state(self) -> "HubState":
        """Retorna o estado atual do Hub."""
        ...

    def get_debug_logger(self) -> Optional[Callable[[str], None]]:
        """Retorna função de debug logging (opcional)."""
        ...


class HubNotesRenderer:
    """Responsável por renderizar o painel de notas na UI.

    MF-20: Extraído de hub_screen.py para reduzir complexidade.

    Este renderer:
    - Recebe lista de notas e força re-renderização se necessário
    - Atualiza a UI via HubNotesView
    - Não contém lógica de negócio
    - Foca apenas em renderização visual

    Benefícios:
    - Reduz tamanho do hub_screen.py
    - Melhora testabilidade (pode mockar callbacks)
    - Clarifica responsabilidades
    - Facilita manutenção futura
    """

    def __init__(self, callbacks: NotesRenderCallbacks) -> None:
        """Inicializa o renderer.

        Args:
            callbacks: Interface com métodos necessários para renderização
        """
        self._callbacks = callbacks
        self._logger = logger

    def render_notes(
        self,
        notes: List[Dict[str, Any]],
        force: bool = False,
        hub_screen: Any = None,
    ) -> None:
        """Renderiza lista de notas no histórico com cores, timestamps e tooltips.

        MF-20: Método principal de renderização de notas.
        Delega para HubNotesView mas coordena preparação de dados.

        Args:
            notes: Lista de dicionários com dados das notas
            force: Se True, ignora cache de hash e força re-renderização
            hub_screen: Referência ao HubScreen (para compatibilidade com código existente)
        """
        # Obter estado e view via callbacks
        try:
            state = self._callbacks.get_state()
            notes_view = self._callbacks.get_notes_view()
            debug_logger = self._callbacks.get_debug_logger()
        except Exception as e:
            self._logger.warning(f"Erro ao obter callbacks para renderização de notas: {e}")
            return

        # Garantir que author_tags existe no estado
        if state.author_tags is None:
            state.author_tags = {}

        # Verificar se notes_view existe
        if notes_view is None:
            self._logger.warning("HubNotesRenderer: notes_view ausente ao renderizar notas; ignorando chamada.")
            return

        # Preparar dados para renderização
        author_tags = state.author_tags
        author_names_cache = state.author_cache or {}

        # Delegar para HubNotesView (MF-34)
        try:
            notes_view.render_notes(
                notes or [],
                force=force,
                author_tags=author_tags,
                author_names_cache=author_names_cache,
                hub_screen=hub_screen,
                debug_logger=debug_logger,
            )
            self._logger.debug(f"HubNotesRenderer: renderizadas {len(notes or [])} notas")
        except Exception as e:
            self._logger.exception(f"Erro ao renderizar notas via HubNotesView: {e}")

    def render_loading(self) -> None:
        """Renderiza estado de loading no painel de notas.

        MF-20: Placeholder para futuro estado de loading.
        Por enquanto, apenas loga (a lógica atual não tem loading separado).
        """
        self._logger.debug("HubNotesRenderer: render_loading (placeholder)")
        # Futura implementação pode chamar notes_view.show_loading()

    def render_error(self, error_message: str) -> None:
        """Renderiza estado de erro no painel de notas.

        MF-20: Placeholder para futuro estado de erro.

        Args:
            error_message: Mensagem de erro a exibir
        """
        self._logger.warning(f"HubNotesRenderer: render_error: {error_message}")
        # Futura implementação pode chamar notes_view.show_error(error_message)

    def render_empty(self) -> None:
        """Renderiza estado vazio no painel de notas.

        MF-20: Placeholder para futuro estado vazio.
        Por enquanto, a view já lida com lista vazia.
        """
        self._logger.debug("HubNotesRenderer: render_empty (lista vazia)")
        # A implementação atual já trata lista vazia na render_notes

    def update_notes_ui_state(
        self,
        has_org_id: bool,
        btn_add_note: Any = None,
        new_note_field: Any = None,
    ) -> None:
        """Atualiza estado do botão e placeholder baseado em org_id.

        MF-20: Extraído de HubScreen._update_notes_ui_state.
        Usa helper calculate_notes_ui_state para determinar estado.

        Args:
            has_org_id: Se há organização selecionada
            btn_add_note: Referência ao botão de adicionar nota
            new_note_field: Referência ao campo de texto
        """
        from src.modules.hub.views.hub_screen_helpers import calculate_notes_ui_state

        state = calculate_notes_ui_state(has_org_id=has_org_id)

        # Aplicar estado ao botão
        if btn_add_note is not None:
            btn_state = "normal" if state["button_enabled"] else "disabled"
            try:
                btn_add_note.configure(state=btn_state)
            except Exception as e:
                self._logger.debug(f"Erro ao configurar botão: {e}")

        # Aplicar estado ao campo de texto
        if new_note_field is not None:
            text_state = "normal" if state["text_field_enabled"] else "disabled"
            try:
                new_note_field.configure(state="normal")  # Temporário para editar
                new_note_field.delete("1.0", "end")

                if state["placeholder_message"]:
                    new_note_field.insert("1.0", state["placeholder_message"])

                new_note_field.configure(state=text_state)
            except Exception as e:
                self._logger.debug(f"Erro ao configurar campo de texto: {e}")

    def __repr__(self) -> str:
        """Representação do renderer para debug."""
        return "<HubNotesRenderer>"
