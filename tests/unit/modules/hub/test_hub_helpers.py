# -*- coding: utf-8 -*-
"""
Testes para funções auxiliares do módulo Hub.

Foco em funções puras de formatação, colorização, estado e normalização.
Cobre: state.py, format.py, utils.py, colors.py
"""

import tkinter as tk
from unittest.mock import MagicMock

import pytest

from src.modules.hub.colors import _author_color, _ensure_author_tag
from src.modules.hub.format import _format_note_line, _format_timestamp
from src.modules.hub.state import HubState, ensure_hub_state, ensure_state
from src.modules.hub.utils import _hash_dict, _hsl_to_hex, _normalize_note
from src.modules.hub.viewmodels.notes_vm import NoteItemView


# ====================================================================
# state.py - HubState e funções de estado
# ====================================================================


def test_hub_state_default_values():
    """HubState deve ser criado com valores padrão corretos."""
    state = HubState()
    assert state.author_tags == {}
    assert state.poll_job is None
    assert state.is_refreshing is False
    assert state.last_refresh_ts is None
    assert state.pending_notes == []
    assert state.auth_retry_ms == 2000


def test_ensure_hub_state_creates_new_state():
    """ensure_hub_state deve criar um novo HubState se não existir."""
    obj = MagicMock()
    del obj._hub_state  # Garantir que não existe

    state = ensure_hub_state(obj)

    assert isinstance(state, HubState)
    assert state.author_tags == {}
    assert obj._hub_state is state


def test_ensure_hub_state_reuses_existing_state():
    """ensure_hub_state deve reusar HubState existente."""
    obj = MagicMock()
    existing_state = HubState(author_tags={"test": "value"}, is_refreshing=True)
    obj._hub_state = existing_state

    state = ensure_hub_state(obj)

    assert state is existing_state
    assert state.author_tags == {"test": "value"}
    assert state.is_refreshing is True


def test_ensure_state_is_alias_for_ensure_hub_state():
    """ensure_state deve ser um alias para ensure_hub_state."""
    obj = MagicMock()
    del obj._hub_state

    state1 = ensure_hub_state(obj)
    obj2 = MagicMock()
    del obj2._hub_state
    state2 = ensure_state(obj2)

    # Ambos devem criar novos estados do mesmo tipo
    assert isinstance(state1, HubState)
    assert isinstance(state2, HubState)


# ====================================================================
# format.py - Formatação de timestamps e linhas de nota
# ====================================================================


def test_format_timestamp_valid_iso():
    """_format_timestamp deve converter ISO para formato local dd/mm/YYYY - HH:MM."""
    # Timestamp fixo: 2025-01-15T14:30:00Z
    ts_iso = "2025-01-15T14:30:00Z"
    result = _format_timestamp(ts_iso)

    # Deve retornar formato dd/mm/YYYY - HH:MM (hora local pode variar)
    assert "/" in result
    assert "-" in result
    assert ":" in result
    # Verifica estrutura básica sem depender de timezone local
    parts = result.split(" - ")
    assert len(parts) == 2
    date_part, time_part = parts
    assert len(date_part.split("/")) == 3  # dd/mm/YYYY
    assert len(time_part.split(":")) == 2  # HH:MM


def test_format_timestamp_empty_string():
    """_format_timestamp deve retornar '?' para string vazia."""
    assert _format_timestamp("") == "?"


def test_format_timestamp_none():
    """_format_timestamp deve retornar '?' para None."""
    result = _format_timestamp(None)  # type: ignore
    assert result == "?"


def test_format_timestamp_invalid_format():
    """_format_timestamp deve retornar '?' para formato inválido."""
    invalid = "not-a-timestamp"
    result = _format_timestamp(invalid)
    # BUG-006: Função retorna "?" para formatos inválidos
    assert result == "?"


def test_format_note_line_basic():
    """_format_note_line deve compor linha padrão com timestamp, autor e texto."""
    created_at = "2025-01-15T10:00:00Z"
    author = "João Silva"
    text = "Teste de nota"

    result = _format_note_line(created_at, author, text)

    assert "João Silva" in result
    assert "Teste de nota" in result
    assert "[" in result and "]" in result  # Timestamp entre colchetes
    assert ":" in result  # Separador autor:texto


def test_format_note_line_empty_text():
    """_format_note_line deve funcionar com texto vazio."""
    result = _format_note_line("2025-01-15T10:00:00Z", "Autor", "")

    assert "Autor" in result
    assert ": " in result  # Separador presente mesmo sem texto


# ====================================================================
# utils.py - Funções utilitárias puras
# ====================================================================


def test_hsl_to_hex_basic():
    """_hsl_to_hex deve converter HSL para formato hexadecimal #RRGGBB."""
    # Vermelho puro: h=0, s=1, l=0.5
    result = _hsl_to_hex(0, 1.0, 0.5)
    assert result.startswith("#")
    assert len(result) == 7
    # Deve ser vermelho: #ff0000 ou próximo
    assert result.lower() == "#ff0000"


def test_hsl_to_hex_blue():
    """_hsl_to_hex deve converter azul corretamente."""
    # Azul puro: h=240, s=1, l=0.5
    result = _hsl_to_hex(240, 1.0, 0.5)
    assert result.startswith("#")
    assert result.lower() == "#0000ff"


def test_hsl_to_hex_gray():
    """_hsl_to_hex com saturação 0 deve retornar cinza."""
    # Cinza: s=0, lightness define tom de cinza
    result = _hsl_to_hex(180, 0.0, 0.5)
    assert result.startswith("#")
    # Componentes RGB devem ser iguais (cinza)
    r, g, b = result[1:3], result[3:5], result[5:7]
    assert r == g == b


def test_hash_dict_consistent():
    """_hash_dict deve produzir hash consistente para mesmo dicionário."""
    d = {"a": 1, "b": 2, "c": 3}
    hash1 = _hash_dict(d)
    hash2 = _hash_dict(d)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produz 64 caracteres hex


def test_hash_dict_order_independent():
    """_hash_dict deve produzir mesmo hash independente da ordem das chaves."""
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 2, "a": 1}
    assert _hash_dict(d1) == _hash_dict(d2)


def test_hash_dict_different_values():
    """_hash_dict deve produzir hashes diferentes para valores diferentes."""
    d1 = {"key": "value1"}
    d2 = {"key": "value2"}
    assert _hash_dict(d1) != _hash_dict(d2)


def test_hash_dict_empty():
    """_hash_dict deve funcionar com dicionário vazio."""
    result = _hash_dict({})
    assert len(result) == 64
    assert isinstance(result, str)


def test_hash_dict_none():
    """_hash_dict deve tratar None como dicionário vazio."""
    result = _hash_dict(None)  # type: ignore
    assert len(result) == 64


def test_normalize_note_dict_complete():
    """_normalize_note deve extrair campos corretos de dict completo."""
    note = {
        "id": "123",
        "created_at": "2025-01-15T10:00:00Z",
        "author_email": "test@example.com",
        "body": "Texto da nota",
    }
    result = _normalize_note(note)

    assert result["id"] == "123"
    assert result["created_at"] == "2025-01-15T10:00:00Z"
    assert result["author_email"] == "test@example.com"
    assert result["body"] == "Texto da nota"


def test_normalize_note_dict_with_aliases():
    """_normalize_note deve usar aliases (ts, author, text) se campos principais ausentes."""
    note = {"ts": "2025-01-15T10:00:00Z", "author": "user@test.com", "text": "Mensagem"}
    result = _normalize_note(note)

    assert result["created_at"] == "2025-01-15T10:00:00Z"
    assert result["author_email"] == "user@test.com"
    assert result["body"] == "Mensagem"


def test_normalize_note_dict_missing_fields():
    """_normalize_note deve retornar strings vazias para campos ausentes."""
    note = {"body": "Apenas texto"}
    result = _normalize_note(note)

    assert result["id"] == ""
    assert result["created_at"] == ""
    assert result["author_email"] == ""
    assert result["body"] == "Apenas texto"


def test_normalize_note_tuple_4_elements():
    """_normalize_note deve converter tupla de 4 elementos (id, ts, author, body)."""
    note = ("456", "2025-01-15T11:00:00Z", "user@example.com", "Texto")
    result = _normalize_note(note)

    assert result["id"] == "456"
    assert result["created_at"] == "2025-01-15T11:00:00Z"
    assert result["author_email"] == "user@example.com"
    assert result["body"] == "Texto"


def test_normalize_note_tuple_3_elements():
    """_normalize_note deve converter tupla de 3 elementos (ts, author, body)."""
    note = ("2025-01-15T12:00:00Z", "user2@test.com", "Mensagem")
    result = _normalize_note(note)

    assert result["id"] == ""  # Sem ID
    assert result["created_at"] == "2025-01-15T12:00:00Z"
    assert result["author_email"] == "user2@test.com"
    assert result["body"] == "Mensagem"


def test_normalize_note_tuple_2_elements():
    """_normalize_note deve converter tupla de 2 elementos (author, body)."""
    note = ("author@test.com", "Texto da nota")
    result = _normalize_note(note)

    assert result["id"] == ""
    assert result["created_at"] == ""
    assert result["author_email"] == "author@test.com"
    assert result["body"] == "Texto da nota"


def test_normalize_note_tuple_1_element():
    """_normalize_note deve converter tupla de 1 elemento (body apenas)."""
    note = ("Apenas o texto",)
    result = _normalize_note(note)

    assert result["id"] == ""
    assert result["created_at"] == ""
    assert result["author_email"] == ""
    assert result["body"] == "Apenas o texto"


def test_normalize_note_list():
    """_normalize_note deve funcionar com list da mesma forma que tuple."""
    note = ["789", "2025-01-15T13:00:00Z", "list@test.com", "Texto lista"]
    result = _normalize_note(note)

    assert result["id"] == "789"
    assert result["created_at"] == "2025-01-15T13:00:00Z"
    assert result["author_email"] == "list@test.com"
    assert result["body"] == "Texto lista"


def test_normalize_note_string():
    """_normalize_note deve converter string diretamente em body."""
    note = "String simples"
    result = _normalize_note(note)

    assert result["id"] == ""
    assert result["created_at"] == ""
    assert result["author_email"] == ""
    assert result["body"] == "String simples"


def test_normalize_note_dataclass_noteitemview():
    """_normalize_note deve extrair campos de NoteItemView (dataclass) sem usar repr."""
    note = NoteItemView(
        id="abc123",
        body="Texto da nota",
        created_at="2025-01-15T10:00:00+00:00",
        author_email="user@test.com",
        author_name="User Test",
        is_pinned=False,
        is_done=False,
        formatted_line="[10:00] User Test: Texto da nota",
        tag_name="author_user@test.com",
    )
    result = _normalize_note(note)

    # Verifica que extrai corretamente os atributos
    assert result["id"] == "abc123"
    assert result["created_at"] == "2025-01-15T10:00:00+00:00"
    assert result["author_email"] == "user@test.com"
    assert result["author_name"] == "User Test"
    assert result["body"] == "Texto da nota"
    assert result["is_pinned"] is False
    assert result["is_done"] is False
    assert result["formatted_line"] == "[10:00] User Test: Texto da nota"
    assert result["tag_name"] == "author_user@test.com"

    # Verifica que NÃO retorna repr do dataclass
    assert "NoteItemView" not in result["body"]
    assert "NoteItemView" not in str(result)


def test_normalize_note_integer():
    """_normalize_note deve converter inteiro em string no body."""
    note = 12345
    result = _normalize_note(note)

    assert result["body"] == "12345"


# ====================================================================
# colors.py - Colorização por autor
# ====================================================================


def test_author_color_consistent_for_same_email():
    """_author_color deve retornar mesma cor para mesmo email."""
    email = "test@example.com"
    color1 = _author_color(email)
    color2 = _author_color(email)
    assert color1 == color2


def test_author_color_different_for_different_emails():
    """_author_color deve retornar cores diferentes para emails diferentes."""
    color1 = _author_color("user1@test.com")
    color2 = _author_color("user2@test.com")
    assert color1 != color2


def test_author_color_hex_format():
    """_author_color deve retornar cor em formato hexadecimal #RRGGBB."""
    color = _author_color("user@test.com")
    assert color.startswith("#")
    assert len(color) == 7
    # Verificar que é hexadecimal válido
    int(color[1:], 16)  # Deve não lançar exceção


def test_author_color_empty_email():
    """_author_color deve retornar cor padrão cinza escuro para email vazio."""
    color = _author_color("")
    assert color == "#3a3a3a"


def test_author_color_none():
    """_author_color deve tratar None como email vazio."""
    color = _author_color(None)  # type: ignore
    assert color == "#3a3a3a"


def test_author_color_case_insensitive():
    """_author_color deve ignorar maiúsculas/minúsculas."""
    color1 = _author_color("User@Test.COM")
    color2 = _author_color("user@test.com")
    assert color1 == color2


def test_author_color_strips_whitespace():
    """_author_color deve ignorar espaços em branco."""
    color1 = _author_color("  user@test.com  ")
    color2 = _author_color("user@test.com")
    assert color1 == color2


@pytest.fixture
def mock_text_widget():
    """Fixture que cria um widget Text mockado para testes."""
    widget = MagicMock(spec=tk.Text)
    widget.tag_names.return_value = ()
    widget.tag_configure = MagicMock()
    widget._author_tags = {}
    return widget


def test_ensure_author_tag_creates_new_tag(mock_text_widget):
    """_ensure_author_tag deve criar nova tag e retornar nome correto."""
    email = "test@example.com"
    tag_name = _ensure_author_tag(mock_text_widget, email)

    assert tag_name == f"author:{email}"
    mock_text_widget.tag_configure.assert_called_once()


def test_ensure_author_tag_reuses_cached_tag(mock_text_widget):
    """_ensure_author_tag deve reutilizar tag do cache se já existe."""
    email = "cached@test.com"
    cache = {email: "author:cached@test.com"}

    tag_name1 = _ensure_author_tag(mock_text_widget, email, tag_cache=cache)
    tag_name2 = _ensure_author_tag(mock_text_widget, email, tag_cache=cache)

    assert tag_name1 == tag_name2 == "author:cached@test.com"
    # tag_configure não deve ser chamado (tag já existe no cache)
    assert mock_text_widget.tag_configure.call_count == 0


def test_ensure_author_tag_uses_widget_cache(mock_text_widget):
    """_ensure_author_tag deve usar cache armazenado no widget se não fornecido."""
    email = "widget@test.com"
    mock_text_widget._author_tags = {}

    tag_name1 = _ensure_author_tag(mock_text_widget, email)
    # Deve adicionar ao cache do widget
    assert email in mock_text_widget._author_tags

    # Segunda chamada deve usar cache do widget
    tag_name2 = _ensure_author_tag(mock_text_widget, email)
    assert tag_name1 == tag_name2


def test_ensure_author_tag_handles_empty_email(mock_text_widget):
    """_ensure_author_tag deve funcionar com email vazio."""
    tag_name = _ensure_author_tag(mock_text_widget, "")
    assert tag_name == "author:unknown"


def test_ensure_author_tag_handles_widget_error(mock_text_widget):
    """_ensure_author_tag deve retornar fallback se widget lançar exceção."""
    mock_text_widget.tag_configure.side_effect = Exception("Widget error")

    tag_name = _ensure_author_tag(mock_text_widget, "error@test.com")

    # Deve retornar fallback sem quebrar
    assert tag_name == "author:default"
