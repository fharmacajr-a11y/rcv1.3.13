# -*- coding: utf-8 -*-
"""
MF-54: Testes para hub_helpers_notes.py

Testa helpers de notas do Hub:
- calculate_notes_ui_state
- calculate_notes_content_hash
- normalize_note_dict
- format_timestamp
- format_note_line
- should_show_notes_section
- format_notes_count
- is_notes_list_empty
- should_skip_render_empty_notes

Meta: 100% de cobertura (branches + statements).
"""

from __future__ import annotations

import importlib
from datetime import timezone
from unittest.mock import patch

from src.modules.hub.views import hub_helpers_notes
from src.modules.hub.views.hub_helpers_notes import (
    calculate_notes_content_hash,
    calculate_notes_ui_state,
    format_note_line,
    format_notes_count,
    format_timestamp,
    is_notes_list_empty,
    normalize_note_dict,
    should_show_notes_section,
    should_skip_render_empty_notes,
)


# ==============================================================================
# calculate_notes_ui_state
# ==============================================================================
class TestCalculateNotesUiState:
    """Testa cálculo do estado da UI de notas."""

    def test_has_org_id_true_enables_ui(self) -> None:
        """Quando has_org_id=True, UI está habilitada e sem placeholder."""
        result = calculate_notes_ui_state(True)
        assert result["button_enabled"] is True
        assert result["text_field_enabled"] is True
        assert result["placeholder_message"] == ""

    def test_has_org_id_false_disables_ui(self) -> None:
        """Quando has_org_id=False, UI está desabilitada com mensagem."""
        result = calculate_notes_ui_state(False)
        assert result["button_enabled"] is False
        assert result["text_field_enabled"] is False
        assert result["placeholder_message"] == "Sessão sem organização. Faça login novamente."


# ==============================================================================
# calculate_notes_content_hash
# ==============================================================================
class TestCalculateNotesContentHash:
    """Testa cálculo de hash de conteúdo de notas."""

    def test_empty_list_returns_expected_hash(self) -> None:
        """Lista vazia retorna hash MD5 esperado."""
        result = calculate_notes_content_hash([])
        # MD5 de "[]" serializado como JSON
        assert result == "d751713988987e9331980363e24189ce"

    def test_same_notes_produce_same_hash(self) -> None:
        """Mesma lista de notas produz hash idêntico (determinístico)."""
        notes = [
            {
                "author_email": "user@example.com",
                "created_at": "2025-01-01T10:00:00Z",
                "body": "Test note",
                "author_name": "User",
            }
        ]
        hash1 = calculate_notes_content_hash(notes)
        hash2 = calculate_notes_content_hash(notes)
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hexdigest tem 32 caracteres

    def test_different_body_produces_different_hash(self) -> None:
        """Mudança no body (len muda) altera o hash."""
        notes1 = [
            {
                "author_email": "user@example.com",
                "created_at": "2025-01-01T10:00:00Z",
                "body": "Short",
                "author_name": "User",
            }
        ]
        notes2 = [
            {
                "author_email": "user@example.com",
                "created_at": "2025-01-01T10:00:00Z",
                "body": "Much longer text",
                "author_name": "User",
            }
        ]
        hash1 = calculate_notes_content_hash(notes1)
        hash2 = calculate_notes_content_hash(notes2)
        assert hash1 != hash2

    def test_different_order_produces_different_hash(self) -> None:
        """Ordem diferente das notas produz hash diferente."""
        notes1 = [
            {"author_email": "a@test.com", "created_at": "2025-01-01T10:00:00Z", "body": "A", "author_name": "A"},
            {"author_email": "b@test.com", "created_at": "2025-01-02T10:00:00Z", "body": "B", "author_name": "B"},
        ]
        notes2 = [
            {"author_email": "b@test.com", "created_at": "2025-01-02T10:00:00Z", "body": "B", "author_name": "B"},
            {"author_email": "a@test.com", "created_at": "2025-01-01T10:00:00Z", "body": "A", "author_name": "A"},
        ]
        hash1 = calculate_notes_content_hash(notes1)
        hash2 = calculate_notes_content_hash(notes2)
        assert hash1 != hash2

    def test_normalizes_email_strip_and_lower(self) -> None:
        """Email é normalizado (strip + lower) no hash."""
        notes1 = [
            {
                "author_email": "  USER@EXAMPLE.COM  ",
                "created_at": "2025-01-01T10:00:00Z",
                "body": "Test",
                "author_name": "User",
            }
        ]
        notes2 = [
            {
                "author_email": "user@example.com",
                "created_at": "2025-01-01T10:00:00Z",
                "body": "Test",
                "author_name": "User",
            }
        ]
        hash1 = calculate_notes_content_hash(notes1)
        hash2 = calculate_notes_content_hash(notes2)
        assert hash1 == hash2

    def test_handles_missing_fields(self) -> None:
        """Campos ausentes são tratados como strings vazias."""
        notes = [{"body": "Test"}]
        result = calculate_notes_content_hash(notes)
        # Deve funcionar sem erro e retornar hash válido
        assert len(result) == 32

    def test_handles_none_values(self) -> None:
        """Valores None são tratados como strings vazias."""
        notes = [
            {
                "author_email": None,
                "created_at": None,
                "body": None,
                "author_name": None,
            }
        ]
        result = calculate_notes_content_hash(notes)
        # Hash de nota com todos os campos vazios
        assert len(result) == 32


# ==============================================================================
# normalize_note_dict
# ==============================================================================
class TestNormalizeNoteDict:
    """Testa normalização de nota para dict padrão."""

    def test_dict_with_standard_keys(self) -> None:
        """Dict com chaves padrão é retornado normalizado."""
        note = {
            "author_email": "user@test.com",
            "created_at": "2025-01-01T10:00:00Z",
            "body": "Test note",
            "author_name": "User",
        }
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == "2025-01-01T10:00:00Z"
        assert result["body"] == "Test note"
        assert result["author_name"] == "User"

    def test_dict_with_alternative_keys(self) -> None:
        """Dict com chaves alternativas é mapeado corretamente."""
        # author_email também aceita "author" e "email"
        note1 = {"author": "user@test.com", "body": "Test"}
        result1 = normalize_note_dict(note1)
        assert result1["author_email"] == "user@test.com"

        note2 = {"email": "user@test.com", "body": "Test"}
        result2 = normalize_note_dict(note2)
        assert result2["author_email"] == "user@test.com"

        # created_at também aceita "timestamp"
        note3 = {"timestamp": "2025-01-01T10:00:00Z", "body": "Test"}
        result3 = normalize_note_dict(note3)
        assert result3["created_at"] == "2025-01-01T10:00:00Z"

        # body também aceita "text" e "content"
        note4 = {"text": "Test note"}
        result4 = normalize_note_dict(note4)
        assert result4["body"] == "Test note"

        note5 = {"content": "Test note"}
        result5 = normalize_note_dict(note5)
        assert result5["body"] == "Test note"

        # author_name também aceita "display_name"
        note6 = {"display_name": "User Name", "body": "Test"}
        result6 = normalize_note_dict(note6)
        assert result6["author_name"] == "User Name"

    def test_empty_dict(self) -> None:
        """Dict vazio retorna todos os campos como strings vazias."""
        result = normalize_note_dict({})
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == ""
        assert result["author_name"] == ""

    def test_tuple_with_three_elements(self) -> None:
        """Tuple com 3 elementos: (created_at, author, body)."""
        note = ("2025-01-01T10:00:00Z", "user@test.com", "Test note")
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == "2025-01-01T10:00:00Z"
        assert result["body"] == "Test note"
        assert result["author_name"] == ""

    def test_list_with_three_elements(self) -> None:
        """List com 3 elementos: (created_at, author, body)."""
        note = ["2025-01-01T10:00:00Z", "user@test.com", "Test note"]
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == "2025-01-01T10:00:00Z"
        assert result["body"] == "Test note"
        assert result["author_name"] == ""

    def test_tuple_with_two_elements(self) -> None:
        """Tuple com 2 elementos: (author, body)."""
        note = ("user@test.com", "Test note")
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == ""
        assert result["body"] == "Test note"
        assert result["author_name"] == ""

    def test_list_with_two_elements(self) -> None:
        """List com 2 elementos: (author, body)."""
        note = ["user@test.com", "Test note"]
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == ""
        assert result["body"] == "Test note"
        assert result["author_name"] == ""

    def test_tuple_with_one_element(self) -> None:
        """Tuple com 1 elemento: (body,)."""
        note = ("Test note",)
        result = normalize_note_dict(note)
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == "Test note"
        assert result["author_name"] == ""

    def test_list_with_one_element(self) -> None:
        """List com 1 elemento: (body,)."""
        note = ["Test note"]
        result = normalize_note_dict(note)
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == "Test note"
        assert result["author_name"] == ""

    def test_empty_tuple(self) -> None:
        """Tuple vazia cai no fallback."""
        result = normalize_note_dict(())
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == ""
        assert result["author_name"] == ""

    def test_empty_list(self) -> None:
        """List vazia cai no fallback."""
        result = normalize_note_dict([])
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == ""
        assert result["author_name"] == ""

    def test_fallback_with_string(self) -> None:
        """Objeto qualquer vira str(note) no body."""
        result = normalize_note_dict("Just a string")
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == "Just a string"
        assert result["author_name"] == ""

    def test_fallback_with_none(self) -> None:
        """None vira string vazia no body."""
        result = normalize_note_dict(None)
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == ""
        assert result["author_name"] == ""

    def test_fallback_with_object(self) -> None:
        """Objeto qualquer é convertido para string."""

        class CustomObj:
            def __str__(self) -> str:
                return "Custom object"

        result = normalize_note_dict(CustomObj())
        assert result["body"] == "Custom object"


# ==============================================================================
# format_timestamp
# ==============================================================================
class TestFormatTimestamp:
    """Testa formatação de timestamp ISO para local."""

    def test_none_returns_question_mark(self) -> None:
        """None retorna '?'."""
        assert format_timestamp(None) == "?"

    def test_empty_string_returns_question_mark(self) -> None:
        """String vazia retorna '?'."""
        assert format_timestamp("") == "?"

    def test_iso_with_z_formats_correctly(self) -> None:
        """ISO com Z é formatado corretamente (determinístico com UTC)."""
        # Patch _LOCAL_TZ para garantir determinismo
        with patch.object(hub_helpers_notes, "_LOCAL_TZ", timezone.utc):
            result = format_timestamp("2025-01-15T14:30:00Z")
            assert result == "15/01/2025 - 14:30"

    def test_iso_without_timezone_assumes_utc(self) -> None:
        """ISO sem timezone assume UTC."""
        with patch.object(hub_helpers_notes, "_LOCAL_TZ", timezone.utc):
            result = format_timestamp("2025-01-15T14:30:00")
            # dt.tzinfo is None, então assume UTC
            assert result == "15/01/2025 - 14:30"

    def test_invalid_string_returns_original(self) -> None:
        """String inválida retorna o valor original."""
        assert format_timestamp("invalid") == "invalid"
        assert format_timestamp("not-a-date") == "not-a-date"

    def test_iso_with_offset_formats_correctly(self) -> None:
        """ISO com offset é formatado corretamente."""
        with patch.object(hub_helpers_notes, "_LOCAL_TZ", timezone.utc):
            # "2025-01-15T14:30:00+02:00" → UTC seria 12:30
            result = format_timestamp("2025-01-15T14:30:00+02:00")
            assert result == "15/01/2025 - 12:30"


# ==============================================================================
# Cobertura de fallback de timezone local no import
# ==============================================================================
class TestLocalTimezoneImportFallback:
    """Testa o fallback de timezone local quando datetime.now() falha."""

    def test_timezone_fallback_on_import_error(self) -> None:
        """Quando datetime.now() falha no import, _LOCAL_TZ vira timezone.utc."""
        # Patch datetime.datetime.now para levantar exceção
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.side_effect = Exception("Mock error")
            # Reload do módulo para executar o bloco try/except no import
            importlib.reload(hub_helpers_notes)
            # Verificar que _LOCAL_TZ foi setado como timezone.utc
            assert hub_helpers_notes._LOCAL_TZ == timezone.utc

        # Restaurar estado original do módulo
        importlib.reload(hub_helpers_notes)


# ==============================================================================
# format_note_line
# ==============================================================================
class TestFormatNoteLine:
    """Testa formatação de linha de nota."""

    def test_formats_note_line_correctly(self) -> None:
        """Linha de nota é formatada: [timestamp] autor: texto."""
        # Patch format_timestamp para retorno fixo
        with patch.object(hub_helpers_notes, "format_timestamp", return_value="TS"):
            result = format_note_line("2025-01-15T14:30:00Z", "João Silva", "Reunião às 15h")
            assert result == "[TS] João Silva: Reunião às 15h"

    def test_empty_timestamp_shows_question_mark(self) -> None:
        """Timestamp vazio mostra '?' via format_timestamp."""
        # format_timestamp("") retorna "?"
        result = format_note_line("", "Usuário", "Nota sem timestamp")
        assert result == "[?] Usuário: Nota sem timestamp"

    def test_none_timestamp_shows_question_mark(self) -> None:
        """Timestamp None mostra '?' via format_timestamp."""
        result = format_note_line(None, "Anônimo", "Teste")
        assert result == "[?] Anônimo: Teste"


# ==============================================================================
# should_show_notes_section
# ==============================================================================
class TestShouldShowNotesSection:
    """Testa decisão de mostrar seção de notas."""

    def test_always_returns_true(self) -> None:
        """Seção de notas sempre é mostrada (independente da contagem)."""
        assert should_show_notes_section(0) is True
        assert should_show_notes_section(1) is True
        assert should_show_notes_section(999) is True


# ==============================================================================
# format_notes_count
# ==============================================================================
class TestFormatNotesCount:
    """Testa formatação de contagem de notas com pluralização."""

    def test_count_one_returns_singular(self) -> None:
        """Contagem 1 retorna '1 nota' (singular)."""
        assert format_notes_count(1) == "1 nota"

    def test_count_zero_returns_plural(self) -> None:
        """Contagem 0 retorna '0 notas' (plural)."""
        assert format_notes_count(0) == "0 notas"

    def test_count_two_returns_plural(self) -> None:
        """Contagem 2 retorna '2 notas' (plural)."""
        assert format_notes_count(2) == "2 notas"

    def test_count_many_returns_plural(self) -> None:
        """Contagem alta retorna '{n} notas' (plural)."""
        assert format_notes_count(100) == "100 notas"
        assert format_notes_count(999) == "999 notas"


# ==============================================================================
# is_notes_list_empty
# ==============================================================================
class TestIsNotesListEmpty:
    """Testa verificação de lista de notas vazia."""

    def test_none_returns_true(self) -> None:
        """None é considerado vazio."""
        assert is_notes_list_empty(None) is True

    def test_empty_list_returns_true(self) -> None:
        """Lista vazia retorna True."""
        assert is_notes_list_empty([]) is True

    def test_list_with_one_note_returns_false(self) -> None:
        """Lista com 1 nota retorna False."""
        assert is_notes_list_empty([{"body": "test"}]) is False

    def test_list_with_multiple_notes_returns_false(self) -> None:
        """Lista com múltiplas notas retorna False."""
        assert is_notes_list_empty([{"body": "test1"}, {"body": "test2"}]) is False


# ==============================================================================
# should_skip_render_empty_notes
# ==============================================================================
class TestShouldSkipRenderEmptyNotes:
    """Testa decisão de pular render quando notas vazias."""

    def test_none_returns_true(self) -> None:
        """None → deve pular render."""
        assert should_skip_render_empty_notes(None) is True

    def test_empty_list_returns_true(self) -> None:
        """Lista vazia → deve pular render."""
        assert should_skip_render_empty_notes([]) is True

    def test_list_with_notes_returns_false(self) -> None:
        """Lista com notas → deve permitir render."""
        assert should_skip_render_empty_notes([{"body": "test"}]) is False
