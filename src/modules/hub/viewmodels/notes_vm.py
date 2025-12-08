# -*- coding: utf-8 -*-
"""ViewModel para a Central de Anotações do HUB.

Implementa o padrão MVVM, encapsulando toda a lógica de apresentação das notas
de forma headless (sem depender de Tkinter). A View (HubScreen/panels) apenas
consome o state e renderiza.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Callable, Optional

try:
    from src.core.logger import get_logger
except Exception:

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


@dataclass(frozen=True)
class NoteItemView:
    """Representa uma anotação individual formatada para exibição.

    Attributes:
        id: ID único da anotação.
        body: Texto da anotação.
        created_at: Timestamp de criação (ISO string).
        author_email: Email do autor.
        author_name: Nome de exibição do autor.
        is_pinned: Se a nota está fixada no topo (futuro).
        is_done: Se a nota está marcada como concluída (futuro).
        formatted_line: Linha formatada para exibição (timestamp + autor + texto).
        tag_name: Nome da tag para coloração no Text widget (baseado no autor).
    """

    id: Any
    body: str
    created_at: str
    author_email: str
    author_name: str = ""
    is_pinned: bool = False
    is_done: bool = False
    formatted_line: str = ""
    tag_name: str = ""


@dataclass(frozen=True)
class NotesViewState:
    """Estado imutável da Central de Anotações.

    Attributes:
        is_loading: Se está carregando notas.
        error_message: Mensagem de erro (se houver).
        notes: Lista de notas formatadas para exibição.
        filter_text: Texto de filtro ativo (futuro).
        show_only_pinned: Se deve mostrar apenas notas fixadas (futuro).
        total_count: Total de notas (sem filtro).
    """

    is_loading: bool = False
    error_message: Optional[str] = None
    notes: list[NoteItemView] = field(default_factory=list)
    filter_text: str = ""
    show_only_pinned: bool = False
    total_count: int = 0


class NotesViewModel:
    """ViewModel headless para a Central de Anotações do HUB.

    Encapsula a lógica de:
    - Carregar lista de notas via service
    - Formatar notas para exibição (linhas de texto, tags de cor)
    - Ordenar notas (pinadas primeiro, depois por data)
    - Aplicar filtros (texto, status)
    - Gerenciar estado de loading/erro

    A View (HubScreen/panels) apenas observa o state e renderiza.
    """

    def __init__(
        self,
        service: Callable[[str], list[dict[str, Any]]] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Inicializa o ViewModel.

        Args:
            service: Função de service para carregar notas (injetável para testes).
                Assinatura esperada: (org_id: str) -> list[dict]
            logger: Logger opcional (usa logger do módulo se não fornecido).
        """
        self._service = service
        self._logger = logger or globals()["logger"]
        self._state = NotesViewState()
        self._author_names_cache: dict[str, str] = {}  # email -> display_name

    @property
    def state(self) -> NotesViewState:
        """Estado atual das notas (imutável)."""
        return self._state

    def load(
        self,
        org_id: str,
        author_names_cache: dict[str, str] | None = None,
    ) -> NotesViewState:
        """Carrega notas e monta estado de visualização.

        Este método é headless (sem Tkinter) e pode rodar em thread separada.

        Args:
            org_id: ID da organização.
            author_names_cache: Cache de nomes de autores (email -> display_name).

        Returns:
            Novo estado das notas (com lista ou erro).
        """
        # Atualizar cache de nomes
        if author_names_cache:
            self._author_names_cache = author_names_cache.copy()

        # Marca como loading
        self._state = replace(
            self._state,
            is_loading=True,
            error_message=None,
        )

        try:
            if self._service is None:
                # Sem service injetado, retorna estado vazio
                self._state = NotesViewState(
                    is_loading=False,
                    notes=[],
                    total_count=0,
                )
                return self._state

            # Buscar notas via service
            raw_notes = self._service(org_id)

            # Normalizar e formatar notas
            note_items = [self._make_note_item(note) for note in raw_notes]

            # Ordenar: fixadas primeiro, depois por data (mais recentes primeiro)
            note_items_sorted = self._sort_notes(note_items)

            # Atualizar estado com sucesso
            self._state = NotesViewState(
                is_loading=False,
                error_message=None,
                notes=note_items_sorted,
                total_count=len(note_items_sorted),
            )

            return self._state

        except Exception as e:
            self._logger.exception("Erro ao carregar notas")
            self._state = NotesViewState(
                is_loading=False,
                error_message=f"Erro ao carregar notas: {e}",
                notes=[],
                total_count=0,
            )
            return self._state

    def after_note_created(self, new_note: dict[str, Any]) -> NotesViewState:
        """Atualiza estado após criação de nova nota.

        Args:
            new_note: Dados da nova nota (dict do service).

        Returns:
            Novo estado com a nota adicionada e ordenada.
        """
        try:
            # Criar NoteItemView da nova nota
            new_item = self._make_note_item(new_note)

            # Adicionar à lista existente
            current_notes = list(self._state.notes)
            current_notes.append(new_item)

            # Reordenar
            sorted_notes = self._sort_notes(current_notes)

            # Atualizar estado
            self._state = replace(
                self._state,
                notes=sorted_notes,
                total_count=len(sorted_notes),
            )

            return self._state

        except Exception:
            self._logger.exception("Erro ao adicionar nota ao estado")
            return self._state

    def after_note_updated(self, updated_note: dict[str, Any]) -> NotesViewState:
        """Atualiza estado após edição de nota existente.

        Args:
            updated_note: Dados atualizados da nota.

        Returns:
            Novo estado com a nota atualizada.
        """
        try:
            note_id = updated_note.get("id")
            if note_id is None:
                return self._state

            # Atualizar nota na lista
            updated_notes = []
            for note in self._state.notes:
                if note.id == note_id:
                    updated_notes.append(self._make_note_item(updated_note))
                else:
                    updated_notes.append(note)

            # Reordenar
            sorted_notes = self._sort_notes(updated_notes)

            # Atualizar estado
            self._state = replace(
                self._state,
                notes=sorted_notes,
            )

            return self._state

        except Exception:
            self._logger.exception("Erro ao atualizar nota no estado")
            return self._state

    def after_note_deleted(self, note_id: Any) -> NotesViewState:
        """Atualiza estado após remoção de nota.

        Args:
            note_id: ID da nota removida.

        Returns:
            Novo estado sem a nota removida.
        """
        try:
            # Filtrar nota removida
            remaining_notes = [note for note in self._state.notes if note.id != note_id]

            # Atualizar estado
            self._state = replace(
                self._state,
                notes=remaining_notes,
                total_count=len(remaining_notes),
            )

            return self._state

        except Exception:
            self._logger.exception("Erro ao remover nota do estado")
            return self._state

    def apply_filter(self, filter_text: str) -> NotesViewState:
        """Aplica filtro de texto nas notas (futuro).

        Args:
            filter_text: Texto para filtrar.

        Returns:
            Novo estado com filtro aplicado.
        """
        # TODO: implementar filtro quando necessário
        self._state = replace(
            self._state,
            filter_text=filter_text,
        )
        return self._state

    # =========================================================================
    # MÉTODOS PRIVADOS (Lógica de apresentação)
    # =========================================================================

    def _make_note_item(self, note_data: dict[str, Any]) -> NoteItemView:
        """Cria NoteItemView a partir de dados brutos.

        Args:
            note_data: Dados brutos da nota do service.

        Returns:
            NoteItemView formatado para exibição.
        """
        # Normalizar dados
        note_id = note_data.get("id")
        body = (note_data.get("body") or "").strip()
        created_at = note_data.get("created_at") or ""
        author_email = (note_data.get("author_email") or "").strip().lower()
        author_name = note_data.get("author_name") or ""

        # Usar cache de nomes se disponível
        if not author_name and author_email in self._author_names_cache:
            author_name = self._author_names_cache[author_email]

        # Fallback para email se não tiver nome
        display_name = author_name or author_email or "Desconhecido"

        # Formatar timestamp
        formatted_time = self._format_timestamp(created_at)

        # Montar linha formatada: [HH:MM] Nome: texto
        formatted_line = f"[{formatted_time}] {display_name}: {body}"

        # Tag para coloração (baseado no email do autor)
        tag_name = f"author_{author_email}" if author_email else "author_unknown"

        return NoteItemView(
            id=note_id,
            body=body,
            created_at=created_at,
            author_email=author_email,
            author_name=display_name,
            is_pinned=note_data.get("is_pinned", False),
            is_done=note_data.get("is_done", False),
            formatted_line=formatted_line,
            tag_name=tag_name,
        )

    def _format_timestamp(self, iso_timestamp: str) -> str:
        """Formata timestamp ISO para exibição (HH:MM).

        Args:
            iso_timestamp: Timestamp em formato ISO string.

        Returns:
            String formatada "HH:MM" ou "??:??" se inválido.
        """
        try:
            # Tentar parsear ISO timestamp
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            return dt.strftime("%H:%M")
        except Exception:
            return "??:??"

    def _sort_notes(self, notes: list[NoteItemView]) -> list[NoteItemView]:
        """Ordena notas: fixadas primeiro, depois por data (mais recentes primeiro).

        Args:
            notes: Lista de notas para ordenar.

        Returns:
            Lista ordenada de notas.
        """

        def sort_key(note: NoteItemView) -> tuple:
            # Primeiro critério: fixadas vêm primeiro (inverte bool)
            # Segundo critério: mais recentes primeiro (inverte timestamp)
            return (not note.is_pinned, note.created_at)

        try:
            return sorted(notes, key=sort_key, reverse=True)
        except Exception:
            self._logger.exception("Erro ao ordenar notas")
            return notes

    def update_author_names_cache(self, cache: dict[str, str]) -> None:
        """Atualiza cache de nomes de autores.

        Args:
            cache: Novo cache de nomes (email -> display_name).
        """
        self._author_names_cache = cache.copy()
