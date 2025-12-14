# -*- coding: utf-8 -*-
"""ViewModel para a Central de Anotações do HUB.

Implementa o padrão MVVM, encapsulando toda a lógica de apresentação das notas
de forma headless (sem depender de Tkinter). A View (HubScreen/panels) apenas
consome o state e renderiza.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Optional

from src.modules.hub.notes_rendering import format_note_full_line

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
        self._all_notes: list[NoteItemView] = []  # MF-6: Lista completa sem filtro
        self._all_notes: list[NoteItemView] = []  # MF-6: Lista completa sem filtro

    @property
    def state(self) -> NotesViewState:
        """Estado atual das notas (imutável)."""
        return self._state

    def start_loading(self) -> NotesViewState:
        """Cria estado de loading inicial.

        Returns:
            Estado com is_loading=True e campos limpos.
        """
        self._state = NotesViewState(is_loading=True)
        return self._state

    def from_error(self, message: str) -> NotesViewState:
        """Cria estado de erro.

        Args:
            message: Mensagem de erro a ser exibida.

        Returns:
            Estado com error_message preenchido e is_loading=False.
        """
        self._state = NotesViewState(
            is_loading=False,
            error_message=message,
            notes=[],
            total_count=0,
        )
        return self._state

    def load(
        self,
        org_id: str,
        author_names_cache: dict[str, str] | dict[str, tuple[str, float]] | None = None,
    ) -> NotesViewState:
        """Carrega notas e monta estado de visualização.

        Este método é headless (sem Tkinter) e pode rodar em thread separada.

        Args:
            org_id: ID da organização.
            author_names_cache: Cache de nomes de autores.
                Pode ser dict[str, str] (nome direto) ou dict[str, tuple[str, float]] (nome + timestamp).
                MF-29: Aceita ambos os formatos para compatibilidade com ScreenProtocol.

        Returns:
            Novo estado das notas (com lista ou erro).
        """
        # Atualizar cache de nomes (normalizar formato se for tupla)
        # MF-29: Suporta dict[str, str] ou dict[str, tuple[str, float]]
        if author_names_cache:
            normalized_cache: dict[str, str] = {}
            for email, value in author_names_cache.items():
                if isinstance(value, tuple):
                    # Formato: (nome, timestamp) -> extrair apenas nome
                    normalized_cache[email] = value[0]
                else:
                    # Formato: nome direto
                    normalized_cache[email] = str(value)
            self._author_names_cache = normalized_cache

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
            # V2: Corrigido para chamar método list_notes() do adapter
            raw_notes = (
                self._service.list_notes(org_id) if hasattr(self._service, "list_notes") else self._service(org_id)
            )

            # Normalizar e formatar notas
            note_items = [self._make_note_item(note) for note in raw_notes]

            # Ordenar: fixadas primeiro, depois por data (mais recentes primeiro)
            note_items_sorted = self._sort_notes(note_items)

            # MF-6: Armazenar lista completa e aplicar filtro atual
            self._all_notes = note_items_sorted

            # Se há filtro ativo, reaplicar
            filtered_notes = note_items_sorted
            if self._state.filter_text:
                filtered_notes = self._apply_filter_to_notes(note_items_sorted, self._state.filter_text)

            # Atualizar estado com sucesso
            self._state = NotesViewState(
                is_loading=False,
                error_message=None,
                notes=filtered_notes,
                filter_text=self._state.filter_text,  # Manter filtro atual
                total_count=len(note_items_sorted),  # Total sem filtro
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

            # MF-6: Adicionar à lista completa
            self._all_notes = [new_item, *self._all_notes]

            # Reordenar lista completa
            self._all_notes = self._sort_notes(self._all_notes)

            # Aplicar filtro atual
            filtered_notes = self._all_notes
            if self._state.filter_text:
                filtered_notes = self._apply_filter_to_notes(self._all_notes, self._state.filter_text)

            # Atualizar estado
            self._state = replace(
                self._state,
                notes=filtered_notes,
                total_count=len(self._all_notes),
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

            # MF-6: Atualizar nota na lista completa
            updated_notes = []
            for note in self._all_notes:
                if note.id == note_id:
                    updated_notes.append(self._make_note_item(updated_note))
                else:
                    updated_notes.append(note)

            # Reordenar lista completa
            self._all_notes = self._sort_notes(updated_notes)

            # Aplicar filtro atual
            filtered_notes = self._all_notes
            if self._state.filter_text:
                filtered_notes = self._apply_filter_to_notes(self._all_notes, self._state.filter_text)

            # Atualizar estado
            self._state = replace(
                self._state,
                notes=filtered_notes,
                total_count=len(self._all_notes),
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
            # MF-6: Filtrar nota removida da lista completa
            self._all_notes = [note for note in self._all_notes if note.id != note_id]

            # Aplicar filtro atual
            filtered_notes = self._all_notes
            if self._state.filter_text:
                filtered_notes = self._apply_filter_to_notes(self._all_notes, self._state.filter_text)

            # Atualizar estado
            self._state = replace(
                self._state,
                notes=filtered_notes,
                total_count=len(self._all_notes),
            )

            return self._state

        except Exception:
            self._logger.exception("Erro ao remover nota do estado")
            return self._state

    def apply_filter(self, filter_text: str) -> NotesViewState:
        """Aplica filtro de texto nas notas.

        MF-6: Filtra notas por texto no body (case-insensitive).

        Args:
            filter_text: Texto para filtrar (vazio = sem filtro).

        Returns:
            Novo estado com filtro aplicado.
        """
        try:
            # Normalizar filtro
            filter_text = (filter_text or "").strip()

            # Se filtro vazio, mostrar todas as notas
            if not filter_text:
                self._state = replace(
                    self._state,
                    notes=self._all_notes,
                    filter_text="",
                )
                return self._state

            # Aplicar filtro
            filtered_notes = self._apply_filter_to_notes(self._all_notes, filter_text)

            # Atualizar estado
            self._state = replace(
                self._state,
                notes=filtered_notes,
                filter_text=filter_text,
            )
            return self._state

        except Exception:
            self._logger.exception("Erro ao aplicar filtro")
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

        # Montar linha formatada usando helper de rendering
        note_item = NoteItemView(
            id=note_id,
            body=body,
            created_at=created_at,
            author_email=author_email,
            author_name=display_name,
            is_pinned=note_data.get("is_pinned", False),
            is_done=note_data.get("is_done", False),
            formatted_line="",  # Será preenchido abaixo
            tag_name=f"author_{author_email}" if author_email else "author_unknown",
        )

        # Usar helper para formatar linha completa
        formatted_line = format_note_full_line(note_item)

        # Retornar com formatted_line preenchido
        return NoteItemView(
            id=note_id,
            body=body,
            created_at=created_at,
            author_email=author_email,
            author_name=display_name,
            is_pinned=note_data.get("is_pinned", False),
            is_done=note_data.get("is_done", False),
            formatted_line=formatted_line,
            tag_name=f"author_{author_email}" if author_email else "author_unknown",
        )

    def _sort_notes(self, notes: list[NoteItemView]) -> list[NoteItemView]:
        """Ordena notas: fixadas primeiro, depois não-fixadas em ordem cronológica (antigas → novas).

        Regras:
        - Notas fixadas (is_pinned=True) aparecem no topo (mantém ordem por data desc).
        - Notas não-fixadas aparecem em ordem cronológica: antigas primeiro, novas embaixo (ASC).

        Args:
            notes: Lista de notas para ordenar.

        Returns:
            Lista ordenada de notas.
        """
        try:
            # Separar fixadas e não-fixadas
            pinned = [n for n in notes if n.is_pinned]
            unpinned = [n for n in notes if not n.is_pinned]

            # Fixadas: mais recentes primeiro (desc)
            pinned_sorted = sorted(pinned, key=lambda n: n.created_at, reverse=True)

            # Não-fixadas: ordem cronológica - antigas primeiro, novas embaixo (asc)
            unpinned_sorted = sorted(unpinned, key=lambda n: n.created_at, reverse=False)

            return pinned_sorted + unpinned_sorted
        except Exception:
            self._logger.exception("Erro ao ordenar notas")
            return notes

    def _apply_filter_to_notes(self, notes: list[NoteItemView], filter_text: str) -> list[NoteItemView]:
        """Filtra lista de notas por texto no body (case-insensitive).

        MF-6: Helper para aplicar filtro de texto.

        Args:
            notes: Lista de notas para filtrar.
            filter_text: Texto de busca (já normalizado).

        Returns:
            Lista filtrada de notas.
        """
        if not filter_text:
            return notes

        try:
            filter_lower = filter_text.lower()
            return [note for note in notes if filter_lower in note.body.lower()]
        except Exception:
            self._logger.exception("Erro ao filtrar notas")
            return notes

    def update_author_names_cache(self, cache: dict[str, str]) -> None:
        """Atualiza cache de nomes de autores.

        Args:
            cache: Novo cache de nomes (email -> display_name).
        """
        self._author_names_cache = cache.copy()

    def fetch_missing_authors(self, emails: list[str]) -> dict[str, str]:
        """Busca nomes de autores ausentes no cache de forma síncrona.

        MF-4: Método para buscar nomes de autores que não estão no cache.
        Usado por hub_async_tasks_service.refresh_author_names_cache_async.

        Args:
            emails: Lista de e-mails de autores cujos nomes não estão em cache.

        Returns:
            Dicionário {email: display_name} com os nomes encontrados.
        """
        authors_map: dict[str, str] = {}

        # Normalizar emails para lowercase
        normalized_emails = [email.strip().lower() for email in emails if email]

        # Importar serviço de profiles
        try:
            from src.core.services.profiles_service import get_display_name_by_email
        except ImportError:
            self._logger.warning("profiles_service não disponível para buscar autores")
            return authors_map

        # Buscar cada email individualmente
        for email in normalized_emails:
            # Pular se já está no cache
            if email in self._author_names_cache:
                continue

            try:
                display_name = get_display_name_by_email(email)
                if display_name:
                    authors_map[email] = display_name
                    # Atualizar cache interno
                    self._author_names_cache[email] = display_name
                    self._logger.debug(f"Author fetched: {email} -> {display_name}")
            except Exception as exc:
                self._logger.debug(f"Erro ao buscar autor {email}: {exc}")
                continue

        self._logger.debug(f"Fetched {len(authors_map)} missing authors")
        return authors_map
