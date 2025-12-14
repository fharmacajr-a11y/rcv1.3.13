# -*- coding: utf-8 -*-
"""Testes para notes_rendering.py - helper de rendering de notas.

Valida:
- Cores de autores (hash-based, consistência)
- Formatação de header (timestamp + autor)
- Formatação de corpo (truncate, "...")
- Tooltips (data completa, autor, texto)
"""

from __future__ import annotations

import pytest

from src.modules.hub.notes_rendering import (
    AUTHOR_COLOR_PALETTE,
    build_note_tooltip_text,
    format_full_timestamp,
    format_note_body,
    format_note_full_line,
    format_note_header,
    format_timestamp,
    get_author_color,
)
from src.modules.hub.viewmodels.notes_vm import NoteItemView


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def sample_note() -> NoteItemView:
    """Nota de amostra com todos os campos preenchidos."""
    return NoteItemView(
        id="note-123",
        body="Texto completo da nota de exemplo",
        created_at="2024-12-08T14:30:00Z",
        author_email="test@example.com",
        author_name="João Silva",
        is_pinned=False,
        is_done=False,
        formatted_line="",  # Será preenchido pelo helper
        tag_name="author_test@example.com",
    )


@pytest.fixture
def note_no_author() -> NoteItemView:
    """Nota sem autor definido."""
    return NoteItemView(
        id="note-456",
        body="Nota sem autor",
        created_at="2024-12-08T10:15:00Z",
        author_email="",
        author_name="",
        is_pinned=False,
        is_done=False,
        formatted_line="",
        tag_name="author_unknown",
    )


@pytest.fixture
def note_long_body() -> NoteItemView:
    """Nota com corpo muito longo (para teste de truncate)."""
    long_text = "A" * 300  # 300 caracteres
    return NoteItemView(
        id="note-789",
        body=long_text,
        created_at="2024-12-08T16:45:00Z",
        author_email="long@example.com",
        author_name="Maria Santos",
        is_pinned=False,
        is_done=False,
        formatted_line="",
        tag_name="author_long@example.com",
    )


# =========================================================================
# TESTES: CORES DE AUTORES
# =========================================================================


def test_get_author_color_returns_valid_hex():
    """get_author_color deve retornar cor hex válida da paleta."""
    color = get_author_color("test@example.com")
    assert color in AUTHOR_COLOR_PALETTE


def test_get_author_color_is_consistent():
    """get_author_color deve retornar a mesma cor para o mesmo autor."""
    author = "consistent@example.com"
    color1 = get_author_color(author)
    color2 = get_author_color(author)
    assert color1 == color2


def test_get_author_color_different_authors():
    """Autores diferentes podem ter cores diferentes (baseado em hash)."""
    color1 = get_author_color("author1@example.com")
    color2 = get_author_color("author2@example.com")
    # Não garantimos que sejam diferentes (pode colidir), mas testamos que ambos são válidos
    assert color1 in AUTHOR_COLOR_PALETTE
    assert color2 in AUTHOR_COLOR_PALETTE


def test_get_author_color_empty_string():
    """get_author_color deve lidar com string vazia."""
    color = get_author_color("")
    assert color in AUTHOR_COLOR_PALETTE


def test_get_author_color_special_chars():
    """get_author_color deve lidar com caracteres especiais."""
    color = get_author_color("user+test@example.com")
    assert color in AUTHOR_COLOR_PALETTE


# =========================================================================
# TESTES: FORMATAÇÃO DE TIMESTAMP
# =========================================================================


def test_format_timestamp_valid_iso():
    """format_timestamp deve formatar ISO timestamp para HH:MM."""
    result = format_timestamp("2024-12-08T14:30:00Z")
    assert result == "14:30"


def test_format_timestamp_invalid():
    """format_timestamp deve retornar '??:??' para timestamp inválido."""
    result = format_timestamp("invalid-timestamp")
    assert result == "??:??"


def test_format_timestamp_empty():
    """format_timestamp deve retornar '??:??' para string vazia."""
    result = format_timestamp("")
    assert result == "??:??"


def test_format_full_timestamp_valid_iso():
    """format_full_timestamp deve formatar ISO para DD/MM/YYYY HH:MM:SS."""
    result = format_full_timestamp("2024-12-08T14:30:45Z")
    assert result == "08/12/2024 14:30:45"


def test_format_full_timestamp_invalid():
    """format_full_timestamp deve retornar 'Data inválida' para timestamp inválido."""
    result = format_full_timestamp("invalid-timestamp")
    assert result == "Data inválida"


# =========================================================================
# TESTES: FORMATAÇÃO DE HEADER
# =========================================================================


def test_format_note_header_with_author(sample_note: NoteItemView):
    """format_note_header deve montar header com timestamp e autor."""
    result = format_note_header(sample_note)
    assert result == "[14:30] João Silva: "


def test_format_note_header_no_author(note_no_author: NoteItemView):
    """format_note_header deve usar 'Desconhecido' quando não há autor."""
    result = format_note_header(note_no_author)
    assert result == "[10:15] Desconhecido: "


def test_format_note_header_only_email():
    """format_note_header deve usar email quando não há author_name."""
    note = NoteItemView(
        id="test",
        body="Texto",
        created_at="2024-12-08T12:00:00Z",
        author_email="email@example.com",
        author_name="",
        formatted_line="",
        tag_name="author_email@example.com",
    )
    result = format_note_header(note)
    assert result == "[12:00] email@example.com: "


# =========================================================================
# TESTES: FORMATAÇÃO DE CORPO
# =========================================================================


def test_format_note_body_short_text(sample_note: NoteItemView):
    """format_note_body não deve truncar texto menor que max_len."""
    result = format_note_body(sample_note, max_len=200)
    assert result == "Texto completo da nota de exemplo"
    assert "..." not in result


def test_format_note_body_long_text_truncate(note_long_body: NoteItemView):
    """format_note_body deve truncar texto maior que max_len com '...'."""
    result = format_note_body(note_long_body, max_len=50)
    assert len(result) == 53  # 50 chars + "..."
    assert result.endswith("...")
    assert result.startswith("A" * 50)


def test_format_note_body_exact_max_len():
    """format_note_body não deve truncar se texto == max_len."""
    note = NoteItemView(
        id="test",
        body="A" * 100,
        created_at="2024-12-08T12:00:00Z",
        author_email="test@example.com",
        author_name="Test",
        formatted_line="",
        tag_name="author_test@example.com",
    )
    result = format_note_body(note, max_len=100)
    assert result == "A" * 100
    assert "..." not in result


def test_format_note_body_empty():
    """format_note_body deve lidar com corpo vazio."""
    note = NoteItemView(
        id="test",
        body="",
        created_at="2024-12-08T12:00:00Z",
        author_email="test@example.com",
        author_name="Test",
        formatted_line="",
        tag_name="author_test@example.com",
    )
    result = format_note_body(note, max_len=200)
    assert result == ""


# =========================================================================
# TESTES: FORMATAÇÃO DE LINHA COMPLETA
# =========================================================================


def test_format_note_full_line(sample_note: NoteItemView):
    """format_note_full_line deve montar header + body completo."""
    result = format_note_full_line(sample_note)
    assert result == "[14:30] João Silva: Texto completo da nota de exemplo"


def test_format_note_full_line_no_author(note_no_author: NoteItemView):
    """format_note_full_line deve funcionar sem autor."""
    result = format_note_full_line(note_no_author)
    assert result == "[10:15] Desconhecido: Nota sem autor"


def test_format_note_full_line_long_text(note_long_body: NoteItemView):
    """format_note_full_line não trunca (isso é papel de format_note_body)."""
    result = format_note_full_line(note_long_body)
    assert result.startswith("[16:45] Maria Santos: ")
    assert "A" * 300 in result  # Texto completo preservado


# =========================================================================
# TESTES: TOOLTIPS
# =========================================================================


def test_build_note_tooltip_text(sample_note: NoteItemView):
    """build_note_tooltip_text deve incluir data completa + autor + texto."""
    result = build_note_tooltip_text(sample_note)

    # Verificar componentes
    assert "08/12/2024 14:30:00" in result  # Data completa
    assert "João Silva" in result  # Autor
    assert "Texto completo da nota de exemplo" in result  # Corpo


def test_build_note_tooltip_text_no_author(note_no_author: NoteItemView):
    """build_note_tooltip_text deve usar 'Desconhecido' sem autor."""
    result = build_note_tooltip_text(note_no_author)

    assert "08/12/2024 10:15:00" in result  # Data completa
    assert "Desconhecido" in result  # Fallback
    assert "Nota sem autor" in result  # Corpo


def test_build_note_tooltip_text_long_body(note_long_body: NoteItemView):
    """build_note_tooltip_text deve incluir texto completo (sem truncar)."""
    result = build_note_tooltip_text(note_long_body)

    assert "08/12/2024 16:45:00" in result  # Data completa
    assert "Maria Santos" in result  # Autor
    assert "A" * 300 in result  # Texto completo (não truncado)


def test_build_note_tooltip_text_invalid_date():
    """build_note_tooltip_text deve lidar com data inválida."""
    note = NoteItemView(
        id="test",
        body="Texto",
        created_at="invalid-date",
        author_email="test@example.com",
        author_name="Test",
        formatted_line="",
        tag_name="author_test@example.com",
    )
    result = build_note_tooltip_text(note)

    assert "Data inválida" in result  # Fallback de data
    assert "Test" in result  # Autor
    assert "Texto" in result  # Corpo


# =========================================================================
# TESTES DE INTEGRAÇÃO
# =========================================================================


def test_rendering_pipeline_complete(sample_note: NoteItemView):
    """Testa pipeline completo de rendering (header + body + tooltip)."""
    # Header
    header = format_note_header(sample_note)
    assert header == "[14:30] João Silva: "

    # Body (sem truncar)
    body = format_note_body(sample_note, max_len=200)
    assert body == "Texto completo da nota de exemplo"

    # Full line
    full_line = format_note_full_line(sample_note)
    assert full_line == "[14:30] João Silva: Texto completo da nota de exemplo"

    # Tooltip
    tooltip = build_note_tooltip_text(sample_note)
    assert "08/12/2024 14:30:00" in tooltip
    assert "João Silva" in tooltip
    assert "Texto completo da nota de exemplo" in tooltip

    # Cor
    color = get_author_color(sample_note.tag_name)
    assert color in AUTHOR_COLOR_PALETTE
