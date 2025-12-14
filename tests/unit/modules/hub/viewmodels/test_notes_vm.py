# -*- coding: utf-8 -*-
"""Testes headless para NotesViewModel.

Testa toda a lógica de apresentação de notas sem dependências de Tkinter:
- Carregamento e formatação de notas
- Ordenação (pinned first, then by date)
- Operações CRUD (after_note_created, after_note_updated, after_note_deleted)
- Formatação de timestamps e nomes de autores
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.modules.hub.viewmodels.notes_vm import NoteItemView, NotesViewModel, NotesViewState


@pytest.fixture
def mock_notes_service():
    """Mock do NotesService como callable."""
    return MagicMock()


@pytest.fixture
def sample_notes_data():
    """Dados de exemplo de notas."""
    return [
        {
            "id": "note1",
            "body": "Primeira nota",
            "created_at": "2024-01-01T10:00:00Z",
            "author_email": "user1@example.com",
            "is_pinned": False,
            "is_done": False,
        },
        {
            "id": "note2",
            "body": "Segunda nota (fixada)",
            "created_at": "2024-01-02T11:00:00Z",
            "author_email": "user2@example.com",
            "is_pinned": True,
            "is_done": False,
        },
        {
            "id": "note3",
            "body": "Terceira nota (mais recente)",
            "created_at": "2024-01-03T12:00:00Z",
            "author_email": "user1@example.com",
            "is_pinned": False,
            "is_done": True,
        },
    ]


class TestNotesViewState:
    """Testes para NotesViewState (dataclass imutável)."""

    def test_default_state(self):
        """Estado padrão deve estar vazio."""
        state = NotesViewState()

        assert state.is_loading is False
        assert state.error_message is None
        assert state.notes == []
        assert state.filter_text == ""
        assert state.show_only_pinned is False
        assert state.total_count == 0

    def test_state_is_immutable(self):
        """NotesViewState deve ser imutável (frozen)."""
        state = NotesViewState(total_count=5)

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            state.total_count = 10  # type: ignore[misc]


class TestNoteItemView:
    """Testes para NoteItemView (dataclass imutável)."""

    def test_note_item_creation(self):
        """Deve criar NoteItemView corretamente."""
        note = NoteItemView(
            id="note1",
            body="Test note",
            created_at="2024-01-01T10:00:00Z",
            author_email="user@example.com",
            author_name="User Name",
            is_pinned=True,
            is_done=False,
            formatted_line="[10:00] User Name: Test note",
            tag_name="user@example.com",
        )

        assert note.id == "note1"
        assert note.body == "Test note"
        assert note.is_pinned is True
        assert note.formatted_line == "[10:00] User Name: Test note"


class TestNotesViewModel:
    """Testes headless para NotesViewModel."""

    def test_initial_state_is_empty(self, mock_notes_service):
        """Estado inicial deve estar vazio."""
        vm = NotesViewModel(service=mock_notes_service)

        assert vm.state.is_loading is False
        assert vm.state.notes == []
        assert vm.state.total_count == 0

    def test_load_notes_success(self, mock_notes_service, sample_notes_data):
        """Deve carregar notas e formatá-las corretamente."""
        mock_notes_service.list_notes.return_value = sample_notes_data
        vm = NotesViewModel(service=mock_notes_service)

        state = vm.load(org_id="org123", author_names_cache={"user1@example.com": "User One"})

        assert state.is_loading is False
        assert state.error_message is None
        assert len(state.notes) == 3
        assert state.total_count == 3

        # Verificar ordenação: pinned first, then unpinned cronológico (antigas→novas)
        assert state.notes[0].id == "note2"  # pinned
        assert state.notes[0].is_pinned is True
        assert state.notes[1].id == "note1"  # mais antiga (não fixada) - agora vem primeiro
        assert state.notes[2].id == "note3"  # mais recente (não fixada) - agora vem por último

    def test_load_notes_formats_timestamps(self, mock_notes_service, sample_notes_data):
        """Deve formatar timestamps corretamente."""
        mock_notes_service.list_notes.return_value = [sample_notes_data[0]]
        vm = NotesViewModel(service=mock_notes_service)

        state = vm.load(org_id="org123")

        note = state.notes[0]
        # formatted_line deve conter timestamp formatado
        assert "[" in note.formatted_line
        assert "]" in note.formatted_line
        # Deve conter o corpo da nota
        assert "Primeira nota" in note.formatted_line

    def test_load_notes_uses_author_names_cache(self, mock_notes_service, sample_notes_data):
        """Deve usar cache de nomes de autores."""
        mock_notes_service.list_notes.return_value = [sample_notes_data[0]]
        vm = NotesViewModel(service=mock_notes_service)

        cache = {
            "user1@example.com": "João Silva",
        }
        state = vm.load(org_id="org123", author_names_cache=cache)

        note = state.notes[0]
        assert note.author_name == "João Silva"
        assert "João Silva" in note.formatted_line

    def test_load_notes_handles_service_error(self, mock_notes_service):
        """Deve tratar erros do service."""
        mock_notes_service.list_notes.side_effect = Exception("Database error")
        vm = NotesViewModel(service=mock_notes_service)

        state = vm.load(org_id="org123")

        assert state.is_loading is False
        assert state.error_message is not None
        assert "Database error" in state.error_message
        assert state.notes == []

    def test_load_notes_without_service(self):
        """Deve funcionar sem service (retorna estado vazio)."""
        vm = NotesViewModel(service=None)

        state = vm.load(org_id="org123")

        assert state.notes == []
        assert state.total_count == 0

    def test_after_note_created_adds_note(self, mock_notes_service, sample_notes_data):
        """after_note_created deve adicionar nota e re-ordenar."""
        mock_notes_service.list_notes.return_value = [sample_notes_data[0]]  # Só 1 nota inicialmente
        vm = NotesViewModel(service=mock_notes_service)

        # Load inicial
        state = vm.load(org_id="org123")
        assert len(state.notes) == 1

        # Adicionar nova nota
        new_note = {
            "id": "note_new",
            "body": "Nova nota",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "author_email": "newuser@example.com",
            "is_pinned": False,
            "is_done": False,
        }
        state = vm.after_note_created(new_note)

        assert len(state.notes) == 2
        assert state.total_count == 2
        # Nova nota deve estar no FINAL (ordem cronológica: antigas→novas)
        assert state.notes[1].id == "note_new"  # mais recente fica embaixo
        assert state.notes[0].id == "note1"  # mais antiga fica em cima

    def test_after_note_created_pinned_stays_first(self, mock_notes_service, sample_notes_data):
        """Nota fixada deve permanecer no topo após criar nota nova."""
        mock_notes_service.list_notes.return_value = [sample_notes_data[1]]  # nota fixada
        vm = NotesViewModel(service=mock_notes_service)

        state = vm.load(org_id="org123")
        assert state.notes[0].is_pinned is True

        # Adicionar nota nova (não fixada)
        new_note = {
            "id": "note_new",
            "body": "Nova nota",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "author_email": "user@example.com",
            "is_pinned": False,
            "is_done": False,
        }
        state = vm.after_note_created(new_note)

        # Nota fixada deve continuar no topo
        assert len(state.notes) == 2
        assert state.notes[0].is_pinned is True
        assert state.notes[0].id == "note2"
        assert state.notes[1].id == "note_new"

    def test_after_note_updated_modifies_existing(self, mock_notes_service, sample_notes_data):
        """after_note_updated deve atualizar nota existente."""
        mock_notes_service.list_notes.return_value = sample_notes_data
        vm = NotesViewModel(service=mock_notes_service)

        state = vm.load(org_id="org123")
        original_note = next(n for n in state.notes if n.id == "note1")
        assert "Primeira nota" in original_note.body

        # Atualizar nota
        updated_note = {
            "id": "note1",
            "body": "Nota atualizada",
            "created_at": "2024-01-01T10:00:00Z",
            "author_email": "user1@example.com",
            "is_pinned": False,
            "is_done": False,
        }
        state = vm.after_note_updated(updated_note)

        # Verificar atualização
        updated = next(n for n in state.notes if n.id == "note1")
        assert "Nota atualizada" in updated.body
        assert len(state.notes) == 3  # Mesmo número de notas

    def test_after_note_deleted_removes_note(self, mock_notes_service, sample_notes_data):
        """after_note_deleted deve remover nota."""
        mock_notes_service.list_notes.return_value = sample_notes_data
        vm = NotesViewModel(service=mock_notes_service)

        state = vm.load(org_id="org123")
        assert len(state.notes) == 3

        # Deletar nota
        state = vm.after_note_deleted(note_id="note1")

        assert len(state.notes) == 2
        assert state.total_count == 2
        # Verificar que note1 foi removida
        assert all(n.id != "note1" for n in state.notes)

    def test_sorting_pinned_first_then_by_date(self, mock_notes_service):
        """Ordenação: fixadas primeiro, depois por data (mais recente primeiro)."""
        notes_data = [
            {
                "id": "old_pinned",
                "body": "Nota fixada antiga",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
                "is_pinned": True,
                "is_done": False,
            },
            {
                "id": "recent",
                "body": "Nota recente",
                "created_at": "2024-01-05T10:00:00Z",
                "author_email": "user@example.com",
                "is_pinned": False,
                "is_done": False,
            },
            {
                "id": "new_pinned",
                "body": "Nota fixada nova",
                "created_at": "2024-01-03T10:00:00Z",
                "author_email": "user@example.com",
                "is_pinned": True,
                "is_done": False,
            },
            {
                "id": "old",
                "body": "Nota antiga",
                "created_at": "2024-01-02T10:00:00Z",
                "author_email": "user@example.com",
                "is_pinned": False,
                "is_done": False,
            },
        ]
        mock_notes_service.list_notes.return_value = notes_data
        vm = NotesViewModel(service=mock_notes_service)

        state = vm.load(org_id="org123")

        # Ordem esperada:
        # 1. Fixadas (new_pinned, old_pinned) - por data desc
        # 2. Não fixadas (old, recent) - por data ASC (antigas→novas)
        assert len(state.notes) == 4
        assert state.notes[0].id == "new_pinned"  # fixada mais recente
        assert state.notes[1].id == "old_pinned"  # fixada mais antiga
        assert state.notes[2].id == "old"  # não fixada mais antiga (agora vem primeiro)
        assert state.notes[3].id == "recent"  # não fixada mais recente (agora vem por último)


class TestNotesViewModelStateFactories:
    """Testes para métodos factory de estados (start_loading, from_error)."""

    def test_start_loading_creates_loading_state(self):
        """start_loading deve criar estado de loading limpo."""
        vm = NotesViewModel(service=None)
        state = vm.start_loading()

        assert state.is_loading is True
        assert state.error_message is None
        assert state.notes == []
        assert state.total_count == 0

    def test_from_error_creates_error_state(self):
        """from_error deve criar estado de erro com mensagem."""
        vm = NotesViewModel(service=None)
        state = vm.from_error("Erro ao carregar notas")

        assert state.is_loading is False
        assert state.error_message == "Erro ao carregar notas"
        assert state.notes == []
        assert state.total_count == 0

    def test_start_loading_clears_previous_state(self):
        """start_loading deve limpar estado anterior."""
        mock_service = MagicMock()
        mock_service.list_notes = MagicMock(
            return_value=[
                {
                    "id": "note1",
                    "body": "Test",
                    "created_at": "2024-01-01T10:00:00Z",
                    "author_email": "user@example.com",
                }
            ]
        )
        vm = NotesViewModel(service=mock_service)

        # Carregar com sucesso
        state1 = vm.load(org_id="org123")
        assert len(state1.notes) > 0
        assert state1.total_count > 0

        # Iniciar loading deve limpar
        state2 = vm.start_loading()
        assert state2.is_loading is True
        assert state2.notes == []
        assert state2.total_count == 0

    def test_from_error_after_success(self):
        """from_error deve substituir estado de sucesso."""
        mock_service = MagicMock()
        mock_service.list_notes = MagicMock(
            return_value=[
                {
                    "id": "note1",
                    "body": "Test",
                    "created_at": "2024-01-01T10:00:00Z",
                    "author_email": "user@example.com",
                }
            ]
        )
        vm = NotesViewModel(service=mock_service)

        # Carregar com sucesso
        state1 = vm.load(org_id="org123")
        assert state1.error_message is None
        assert len(state1.notes) > 0

        # Criar estado de erro
        state2 = vm.from_error("Erro de conexão")
        assert state2.error_message == "Erro de conexão"
        assert state2.notes == []

    def test_state_factories_update_vm_state_property(self):
        """Métodos factory devem atualizar vm.state."""
        vm = NotesViewModel(service=None)

        # Após start_loading, state deve refletir loading
        vm.start_loading()
        assert vm.state.is_loading is True

        # Após from_error, state deve refletir erro
        vm.from_error("Teste")
        assert vm.state.error_message == "Teste"
        assert vm.state.is_loading is False

    def test_fetch_missing_authors_returns_empty_dict_when_no_emails(self):
        """fetch_missing_authors deve retornar dicionário vazio se lista de emails vazia."""
        vm = NotesViewModel(service=None)
        result = vm.fetch_missing_authors([])
        assert result == {}

    def test_fetch_missing_authors_skips_cached_authors(self):
        """fetch_missing_authors deve pular emails que já estão no cache."""
        vm = NotesViewModel(service=None)
        # Pré-popular cache
        vm._author_names_cache = {"user1@example.com": "User One"}

        # Mockar profiles_service
        from unittest.mock import patch

        with patch("src.core.services.profiles_service.get_display_name_by_email") as mock_get:
            mock_get.return_value = "User Two"

            # Buscar um email que já está em cache e um novo
            result = vm.fetch_missing_authors(["user1@example.com", "user2@example.com"])

            # Deve ter chamado get_display_name_by_email apenas para user2
            assert mock_get.call_count == 1
            mock_get.assert_called_with("user2@example.com")

            # Resultado deve conter apenas o novo autor
            assert result == {"user2@example.com": "User Two"}

    def test_fetch_missing_authors_updates_internal_cache(self):
        """fetch_missing_authors deve atualizar _author_names_cache internamente."""
        vm = NotesViewModel(service=None)

        # Mockar profiles_service
        from unittest.mock import patch

        with patch("src.core.services.profiles_service.get_display_name_by_email") as mock_get:
            mock_get.return_value = "John Doe"

            # Buscar autor
            result = vm.fetch_missing_authors(["john@example.com"])

            # Cache interno deve ter sido atualizado
            assert vm._author_names_cache["john@example.com"] == "John Doe"
            assert result == {"john@example.com": "John Doe"}

    def test_fetch_missing_authors_normalizes_emails_to_lowercase(self):
        """fetch_missing_authors deve normalizar emails para lowercase."""
        vm = NotesViewModel(service=None)

        # Mockar profiles_service
        from unittest.mock import patch

        with patch("src.core.services.profiles_service.get_display_name_by_email") as mock_get:
            mock_get.return_value = "User Name"

            # Buscar com email em maiúsculas
            result = vm.fetch_missing_authors(["USER@EXAMPLE.COM"])

            # Deve ter chamado com lowercase
            mock_get.assert_called_with("user@example.com")
            assert "user@example.com" in result

    def test_fetch_missing_authors_handles_service_errors_gracefully(self):
        """fetch_missing_authors deve lidar com erros do serviço de forma graciosa."""
        vm = NotesViewModel(service=None)

        # Mockar profiles_service com erro
        from unittest.mock import patch

        with patch("src.core.services.profiles_service.get_display_name_by_email") as mock_get:
            mock_get.side_effect = Exception("Database error")

            # Buscar autor - não deve lançar exceção
            result = vm.fetch_missing_authors(["error@example.com"])

            # Deve retornar vazio mas não falhar
            assert result == {}

    def test_fetch_missing_authors_handles_none_from_service(self):
        """fetch_missing_authors deve ignorar quando serviço retorna None."""
        vm = NotesViewModel(service=None)

        # Mockar profiles_service retornando None (autor não encontrado)
        from unittest.mock import patch

        with patch("src.core.services.profiles_service.get_display_name_by_email") as mock_get:
            mock_get.return_value = None

            # Buscar autor inexistente
            result = vm.fetch_missing_authors(["notfound@example.com"])

            # Não deve incluir no resultado
            assert result == {}
            # Não deve adicionar ao cache
            assert "notfound@example.com" not in vm._author_names_cache


class TestNotesViewModelFiltering:
    """Testes para funcionalidade de filtragem de notas (MF-6)."""

    def test_apply_filter_empty_shows_all_notes(self):
        """Filtro vazio deve mostrar todas as notas."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note2",
                "body": "Segunda nota",
                "created_at": "2024-01-02T11:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note3",
                "body": "Terceira nota",
                "created_at": "2024-01-03T12:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)

        # Carregar notas
        vm.load(org_id="test_org")
        assert len(vm.state.notes) == 3

        # Aplicar filtro vazio
        state = vm.apply_filter("")

        assert len(state.notes) == 3
        assert state.filter_text == ""

    def test_apply_filter_whitespace_shows_all_notes(self):
        """Filtro com apenas espaços deve mostrar todas as notas."""
        sample_notes = [
            {"id": "note1", "body": "Test", "created_at": "2024-01-01T10:00:00Z", "author_email": "user@example.com"},
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        state = vm.apply_filter("   ")

        assert len(state.notes) == 1
        assert state.filter_text == ""

    def test_apply_filter_case_insensitive(self):
        """Filtro deve ser case-insensitive."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Primeira Nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note2",
                "body": "Segunda nota",
                "created_at": "2024-01-02T11:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note3",
                "body": "Terceira NOTA",
                "created_at": "2024-01-03T12:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        # Filtrar por "nota" (minúsculo)
        state = vm.apply_filter("nota")

        assert len(state.notes) == 3
        assert state.filter_text == "nota"

    def test_apply_filter_partial_match(self):
        """Filtro deve fazer match parcial no body."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Reunião com cliente",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note2",
                "body": "Enviar relatório",
                "created_at": "2024-01-02T11:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note3",
                "body": "Ligar para cliente",
                "created_at": "2024-01-03T12:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        # Filtrar por "cliente"
        state = vm.apply_filter("cliente")

        assert len(state.notes) == 2
        assert state.notes[0].id in ["note1", "note3"]
        assert state.notes[1].id in ["note1", "note3"]

    def test_apply_filter_no_matches(self):
        """Filtro sem matches deve retornar lista vazia."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        state = vm.apply_filter("inexistente")

        assert len(state.notes) == 0
        assert state.filter_text == "inexistente"
        assert state.total_count == 1  # Total sem filtro

    def test_apply_filter_preserves_total_count(self):
        """Filtro deve manter total_count (sem filtro)."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note2",
                "body": "Segunda nota",
                "created_at": "2024-01-02T11:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note3",
                "body": "Terceira anotação",
                "created_at": "2024-01-03T12:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        state = vm.apply_filter("nota")

        # "nota" faz match em todas (substring em "anotação" também)
        assert len(state.notes) == 3
        assert state.total_count == 3  # Total original

    def test_filter_persists_after_load(self):
        """Filtro deve ser reaplicado após load."""
        sample_notes_1 = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
        ]
        sample_notes_2 = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note2",
                "body": "Segunda nota",
                "created_at": "2024-01-02T11:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note3",
                "body": "Terceiro comentário",
                "created_at": "2024-01-03T12:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes_1)
        vm = NotesViewModel(service=service)

        # Carregar e aplicar filtro
        vm.load(org_id="test_org")
        vm.apply_filter("nota")

        # Recarregar com mais notas
        service.list_notes.return_value = sample_notes_2
        state = vm.load(org_id="test_org")

        # Filtro deve ter sido reaplicado - apenas notas com "nota" no body
        assert len(state.notes) == 2  # "primeira" e "segunda"
        assert state.filter_text == "nota"
        assert state.total_count == 3

    def test_filter_persists_after_note_created(self):
        """Filtro deve ser reaplicado após criação de nota."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        # Aplicar filtro
        vm.apply_filter("nota")

        # Adicionar nova nota que não faz match
        new_note = {
            "id": "note2",
            "body": "Novo comentário",
            "created_at": "2024-01-02T11:00:00Z",
            "author_email": "user@example.com",
        }
        state = vm.after_note_created(new_note)

        # Filtro deve ter sido aplicado - apenas nota com "nota"
        assert len(state.notes) == 1  # Apenas "primeira"
        assert state.notes[0].id == "note1"
        assert state.total_count == 2

    def test_filter_persists_after_note_updated(self):
        """Filtro deve ser reaplicado após atualização de nota."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note2",
                "body": "Segunda nota",
                "created_at": "2024-01-02T11:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        # Aplicar filtro
        vm.apply_filter("segunda")
        assert len(vm.state.notes) == 1

        # Atualizar nota para não dar mais match
        updated_note = {
            "id": "note2",
            "body": "Anotação atualizada",
            "created_at": "2024-01-02T11:00:00Z",
            "author_email": "user@example.com",
        }
        state = vm.after_note_updated(updated_note)

        # Filtro deve ter sido aplicado
        assert len(state.notes) == 0

    def test_filter_persists_after_note_deleted(self):
        """Filtro deve ser mantido após deleção de nota."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note2",
                "body": "Segunda nota",
                "created_at": "2024-01-02T11:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        # Aplicar filtro
        vm.apply_filter("nota")
        assert len(vm.state.notes) == 2

        # Deletar uma nota
        state = vm.after_note_deleted("note1")

        # Filtro deve ter sido aplicado
        assert len(state.notes) == 1
        assert state.notes[0].id == "note2"
        assert state.filter_text == "nota"

    def test_clearing_filter_shows_all_notes(self):
        """Limpar filtro (passar vazio) deve mostrar todas as notas."""
        sample_notes = [
            {
                "id": "note1",
                "body": "Primeira nota",
                "created_at": "2024-01-01T10:00:00Z",
                "author_email": "user@example.com",
            },
            {
                "id": "note2",
                "body": "Segundo comentário",
                "created_at": "2024-01-02T11:00:00Z",
                "author_email": "user@example.com",
            },
        ]

        service = MagicMock()
        service.list_notes = MagicMock(return_value=sample_notes)
        vm = NotesViewModel(service=service)
        vm.load(org_id="test_org")

        # Aplicar filtro - deve mostrar apenas nota com "nota"
        vm.apply_filter("nota")
        assert len(vm.state.notes) == 1

        # Limpar filtro - deve mostrar todas
        state = vm.apply_filter("")

        assert len(state.notes) == 2
        assert state.filter_text == ""
