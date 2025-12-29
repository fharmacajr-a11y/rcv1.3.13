"""Characterization tests para código legado: actions.py e authors.py.

CLEANAPP-HUB-LEGACY-01 + LEGACY-02 + MICRO-FASE 2

UPDATED: Shims removidos - testes agora usam services diretamente.

Objetivo:
- Capturar comportamento ATUAL das funções de serviço
- Garantir que migração para nova arquitetura não quebre funcionalidade
- Não testar "design ideal", apenas comportamento existente

Funções cobertas:
- lifecycle_service.handle_screen_shown (antigo actions.on_show)
- authors_service.get_author_display_name (antigo authors._author_display_name)
- authors_service.debug_resolve_author (antigo authors._debug_resolve_author)
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from src.modules.hub.services.lifecycle_service import handle_screen_shown
from src.modules.hub.services.authors_service import (
    get_author_display_name,
    debug_resolve_author,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_screen():
    """Cria um mock de HubScreen com atributos mínimos necessários."""
    screen = MagicMock()
    screen.state = MagicMock()
    screen.state.author_cache = {}
    screen.state.notes_last_data = None
    screen.state.notes_last_snapshot = None
    screen.state.email_prefix_map = {}
    screen.state.names_cache_loaded = False
    screen.state.pending_name_fetch = set()
    screen._last_org_for_names = None
    screen.notes_history = MagicMock()
    screen.notes_history.index.return_value = "1.0"  # vazio por padrão
    screen.new_note = MagicMock()
    screen.btn_add_note = MagicMock()
    screen.after = MagicMock()
    return screen


# ============================================================================
# CHARACTERIZATION TESTS: actions.on_show
# ============================================================================


class TestActionsOnShow:
    """Testes de caracterização para actions.on_show."""

    def test_on_show_calls_start_live_sync(self, mock_screen):
        """on_show deve chamar _start_live_sync do screen."""
        mock_screen._start_live_sync = MagicMock()

        handle_screen_shown(mock_screen)

        mock_screen._start_live_sync.assert_called_once()

    def test_on_show_checks_notes_history_empty(self, mock_screen):
        """on_show deve verificar se notes_history está vazio."""
        mock_screen._start_live_sync = MagicMock()

        handle_screen_shown(mock_screen)

        mock_screen.notes_history.index.assert_called_once_with("end-1c")

    def test_on_show_renders_notes_if_empty_and_cached_data_exists(self, mock_screen):
        """on_show deve renderizar notas se histórico vazio e houver cache."""
        mock_screen._start_live_sync = MagicMock()
        mock_screen.notes_history.index.return_value = "1.0"  # vazio
        mock_screen.state.notes_last_data = [{"id": "123", "content": "test"}]
        mock_screen.render_notes = MagicMock()

        handle_screen_shown(mock_screen)

        mock_screen.render_notes.assert_called_once_with(mock_screen.state.notes_last_data, force=True)

    def test_on_show_skips_render_if_notes_history_not_empty(self, mock_screen):
        """on_show não deve renderizar se notes_history já tem conteúdo."""
        mock_screen._start_live_sync = MagicMock()
        mock_screen.notes_history.index.return_value = "2.5"  # não vazio
        mock_screen.state.notes_last_data = [{"id": "123", "content": "test"}]
        mock_screen.render_notes = MagicMock()

        handle_screen_shown(mock_screen)

        mock_screen.render_notes.assert_not_called()

    def test_on_show_resets_author_cache_state(self, mock_screen):
        """on_show deve resetar estado do cache de autores."""
        mock_screen._start_live_sync = MagicMock()
        mock_screen._refresh_author_names_cache_async = MagicMock()
        # MF-19: Adicionar método clear_author_cache ao mock
        mock_screen.clear_author_cache = MagicMock()
        mock_screen.state.author_cache = {"old@email.com": ("Old Name", 99999999)}
        mock_screen.state.email_prefix_map = {"old": "old@email.com"}
        mock_screen.state.names_cache_loaded = True
        mock_screen._last_org_for_names = "old_org"

        handle_screen_shown(mock_screen)

        # MF-19: Verificar que clear_author_cache foi chamado
        mock_screen.clear_author_cache.assert_called_once()
        assert mock_screen._last_org_for_names is None

    def test_on_show_refreshes_author_names_cache_with_force(self, mock_screen):
        """on_show deve chamar refresh do cache de autores com force=True."""
        mock_screen._start_live_sync = MagicMock()
        mock_screen._refresh_author_names_cache_async = MagicMock()

        handle_screen_shown(mock_screen)

        mock_screen._refresh_author_names_cache_async.assert_called_once_with(force=True)

    def test_on_show_handles_start_live_sync_exception_gracefully(self, mock_screen):
        """on_show deve capturar exceções de _start_live_sync sem propagar."""
        mock_screen._start_live_sync = MagicMock(side_effect=RuntimeError("test error"))

        # Não deve propagar exceção
        handle_screen_shown(mock_screen)

        # Mas deve ter tentado chamar
        mock_screen._start_live_sync.assert_called_once()

    def test_on_show_handles_render_notes_exception_gracefully(self, mock_screen):
        """on_show deve capturar exceções de render_notes sem propagar."""
        mock_screen._start_live_sync = MagicMock()
        mock_screen.notes_history.index.return_value = "1.0"
        mock_screen.state.notes_last_data = [{"id": "123"}]
        mock_screen.render_notes = MagicMock(side_effect=RuntimeError("render error"))

        # Não deve propagar exceção
        handle_screen_shown(mock_screen)

        mock_screen.render_notes.assert_called_once()

    def test_on_show_handles_cache_refresh_exception_gracefully(self, mock_screen):
        """on_show deve capturar exceções do cache refresh sem propagar."""
        mock_screen._start_live_sync = MagicMock()
        mock_screen._refresh_author_names_cache_async = MagicMock(side_effect=RuntimeError("cache error"))

        # Não deve propagar exceção
        handle_screen_shown(mock_screen)

        mock_screen._refresh_author_names_cache_async.assert_called_once()


# ============================================================================
# CHARACTERIZATION TESTS: actions.on_add_note_clicked
# ============================================================================


# ============================================================================
# REMOVED IN LEGACY-02: on_add_note_clicked tests (função removida)
# ============================================================================


# ============================================================================
# CHARACTERIZATION TESTS: authors._author_display_name
# ============================================================================


class TestAuthorsDisplayName:
    """Testes de caracterização para authors._author_display_name."""

    def test_author_display_name_returns_question_mark_for_empty_email(self, mock_screen):
        """_author_display_name deve retornar '?' para email vazio."""
        assert get_author_display_name(mock_screen, "") == "?"
        assert get_author_display_name(mock_screen, "   ") == "?"

    def test_author_display_name_uses_author_names_map_if_present(self, mock_screen):
        """_author_display_name deve usar AUTHOR_NAMES se email estiver lá."""
        # AUTHOR_NAMES tem: "farmacajr@gmail.com": "Júnior"
        result = get_author_display_name(mock_screen, "farmacajr@gmail.com")
        assert result == "Júnior"

    def test_author_display_name_uses_author_names_map_case_insensitive(self, mock_screen):
        """_author_display_name deve usar AUTHOR_NAMES case-insensitive."""
        result = get_author_display_name(mock_screen, "FARMACAJR@GMAIL.COM")
        assert result == "Júnior"

    def test_author_display_name_returns_cache_if_valid(self, mock_screen):
        """_author_display_name deve retornar valor do cache se ainda válido."""
        future_expiry = time.time() + 3600  # 1 hora no futuro
        mock_screen._author_names_cache = {"test@email.com": ("Cached Name", future_expiry)}

        result = get_author_display_name(mock_screen, "test@email.com")
        assert result == "Cached Name"

    def test_author_display_name_ignores_expired_cache(self, mock_screen):
        """_author_display_name deve ignorar cache expirado."""
        past_expiry = time.time() - 3600  # 1 hora no passado
        mock_screen._author_names_cache = {"test@email.com": ("Expired Name", past_expiry)}

        result = get_author_display_name(mock_screen, "test@email.com")

        # Não deve retornar o nome expirado
        assert result != "Expired Name"
        # E deve ter removido do cache
        assert "test@email.com" not in mock_screen._author_names_cache

    def test_author_display_name_handles_legacy_string_cache(self, mock_screen):
        """_author_display_name deve converter cache str legado para tupla."""
        mock_screen._author_names_cache = {"test@email.com": "String Cache"}

        result = get_author_display_name(mock_screen, "test@email.com")

        # Deve retornar o valor
        assert result == "String Cache"
        # E converter para formato tupla
        cached = mock_screen._author_names_cache.get("test@email.com")
        assert isinstance(cached, tuple)
        assert cached[0] == "String Cache"

    def test_author_display_name_resolves_prefix_via_email_prefix_map(self, mock_screen):
        """_author_display_name deve resolver prefixos via state.email_prefix_map."""
        mock_screen.state.email_prefix_map = {"junior": "farmacajr@gmail.com"}

        result = get_author_display_name(mock_screen, "junior")  # sem @

        # Deve resolver para o email completo e buscar no AUTHOR_NAMES
        assert result == "Júnior"

    @patch("threading.Thread")
    def test_author_display_name_starts_fetch_thread_for_unknown_email(self, mock_thread, mock_screen):
        """_author_display_name deve iniciar fetch assíncrono para email desconhecido."""
        mock_screen.state.pending_name_fetch = set()
        # MF-19: Adicionar métodos de StateManager ao mock
        mock_screen.clear_pending_name_fetch = MagicMock()
        mock_screen.add_pending_name_fetch = MagicMock(
            side_effect=lambda email: mock_screen.state.pending_name_fetch.add(email)
        )

        result = get_author_display_name(mock_screen, "unknown@test.com")

        # Deve retornar placeholder enquanto isso
        assert result  # algum fallback

        # Deve ter iniciado thread de fetch
        mock_thread.assert_called_once()
        assert mock_thread.call_args[1]["daemon"] is True

        # E marcado como pendente (via método add_pending_name_fetch)
        mock_screen.add_pending_name_fetch.assert_called_once_with("unknown@test.com")
        assert "unknown@test.com" in mock_screen.state.pending_name_fetch

    def test_author_display_name_skips_duplicate_fetch_for_pending_email(self, mock_screen):
        """_author_display_name não deve iniciar fetch duplicado."""
        mock_screen.state.pending_name_fetch = {"pending@test.com"}

        with patch("threading.Thread") as mock_thread:
            get_author_display_name(mock_screen, "pending@test.com")

            # Não deve iniciar nova thread
            mock_thread.assert_not_called()

    def test_author_display_name_returns_formatted_fallback_for_unknown(self, mock_screen):
        """_author_display_name deve retornar prefixo formatado como fallback."""
        mock_screen.state.pending_name_fetch = set()

        with patch("threading.Thread"):
            result = get_author_display_name(mock_screen, "john.doe@example.com")

            # Deve formatar: "john.doe" → "John Doe"
            assert "John" in result or "john" in result.lower()


# ============================================================================
# CHARACTERIZATION TESTS: authors._debug_resolve_author
# ============================================================================


class TestAuthorsDebugResolveAuthor:
    """Testes de caracterização para authors._debug_resolve_author."""

    def test_debug_resolve_author_returns_dict_with_all_fields(self, mock_screen):
        """_debug_resolve_author deve retornar dict com todos os campos esperados."""
        result = debug_resolve_author(mock_screen, "test@email.com")

        assert isinstance(result, dict)
        assert "input" in result
        assert "normalized" in result
        assert "alias_applied" in result
        assert "resolved_email" in result
        assert "name" in result
        assert "source" in result
        assert "cache_hit" in result
        assert "prefix_map_hit" in result

    def test_debug_resolve_author_normalizes_email_to_lowercase(self, mock_screen):
        """_debug_resolve_author deve normalizar email para lowercase."""
        result = debug_resolve_author(mock_screen, "TEST@EMAIL.COM")

        assert result["input"] == "TEST@EMAIL.COM"
        assert result["normalized"] == "test@email.com"

    def test_debug_resolve_author_detects_cache_hit(self, mock_screen):
        """_debug_resolve_author deve detectar cache hit."""
        future_expiry = time.time() + 3600
        mock_screen._author_names_cache = {"cached@test.com": ("Cached Name", future_expiry)}

        result = debug_resolve_author(mock_screen, "cached@test.com")

        assert result["cache_hit"] is True
        assert result["name"] == "Cached Name"
        assert result["source"] == "names_cache"

    def test_debug_resolve_author_uses_author_names_map(self, mock_screen):
        """_debug_resolve_author deve usar AUTHOR_NAMES se disponível."""
        result = debug_resolve_author(mock_screen, "farmacajr@gmail.com")

        assert result["name"] == "Júnior"
        assert result["source"] == "AUTHOR_NAMES"

    @patch("src.core.services.profiles_service.get_display_name_by_email")
    def test_debug_resolve_author_fetches_from_service(self, mock_get_display, mock_screen):
        """_debug_resolve_author deve buscar do serviço se não estiver em cache."""
        mock_get_display.return_value = "Fetched Name"

        result = debug_resolve_author(mock_screen, "new@test.com")

        assert result["name"] == "Fetched Name"
        assert result["source"] == "fetch_by_email"
        mock_get_display.assert_called_once_with("new@test.com")

    def test_debug_resolve_author_applies_prefix_aliases(self, mock_screen):
        """_debug_resolve_author deve aplicar aliases de prefixo."""
        mock_screen.state.email_prefix_map = {"jr": "farmacajr@gmail.com"}

        with patch.dict("src.core.services.profiles_service.EMAIL_PREFIX_ALIASES", {"junior": "jr"}):
            result = debug_resolve_author(mock_screen, "junior")  # sem @

            # Deve ter aplicado alias: junior → jr → farmacajr@gmail.com
            assert result["alias_applied"] is True
            assert result["resolved_email"] == "farmacajr@gmail.com"

    def test_debug_resolve_author_returns_formatted_fallback(self, mock_screen):
        """_debug_resolve_author deve retornar fallback formatado se não achar nada."""
        result = debug_resolve_author(mock_screen, "unknown.person@nowhere.com")

        # Deve ter um nome (fallback formatado)
        assert result["name"]
        # Deve incluir "Unknown" ou "Person" formatado
        assert "Unknown" in result["name"] or "Person" in result["name"]

    def test_debug_resolve_author_detects_prefix_map_hit(self, mock_screen):
        """_debug_resolve_author deve detectar se usou state.email_prefix_map."""
        mock_screen.state.email_prefix_map = {"short": "full@email.com"}

        result = debug_resolve_author(mock_screen, "short")

        assert result["prefix_map_hit"] is True
        assert result["resolved_email"] == "full@email.com"

    def test_debug_resolve_author_handles_empty_input(self, mock_screen):
        """_debug_resolve_author deve lidar com input vazio."""
        result = debug_resolve_author(mock_screen, "")

        assert result["input"] == ""
        assert result["normalized"] == ""
        # Para input vazio, pode retornar string vazia como nome
        assert "name" in result  # deve ter o campo

    @patch("src.core.services.profiles_service.get_display_name_by_email")
    def test_debug_resolve_author_handles_fetch_exception(self, mock_get_display, mock_screen):
        """_debug_resolve_author deve lidar com exceções do fetch."""
        mock_get_display.side_effect = RuntimeError("Network error")

        # Não deve propagar exceção
        result = debug_resolve_author(mock_screen, "error@test.com")

        # Deve ter um nome de fallback
        assert result["name"]
        assert result["source"] == "placeholder"
        assert result["source"] == "placeholder"
