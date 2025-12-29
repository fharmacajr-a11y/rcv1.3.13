# -*- coding: utf-8 -*-
"""Testes para hub/utils.py - funções puras headless."""

from dataclasses import dataclass

from src.modules.hub.utils import _hash_dict, _hsl_to_hex, _normalize_note


def test_hsl_to_hex_red():
    """Testa conversão HSL para HEX (vermelho puro)."""
    result = _hsl_to_hex(0, 1.0, 0.5)
    assert result == "#ff0000"


def test_hsl_to_hex_blue():
    """Testa conversão HSL para HEX (azul puro)."""
    result = _hsl_to_hex(240, 1.0, 0.5)
    assert result == "#0000ff"


def test_hsl_to_hex_gray():
    """Testa conversão HSL para HEX (cinza)."""
    result = _hsl_to_hex(0, 0.0, 0.5)
    assert result == "#7f7f7f"  # colorsys arredonda para 127 (0x7F) em vez de 128 (0x80)


def test_hash_dict_stable():
    """Testa que hash é estável independente da ordem das chaves."""
    dict1 = {"a": 1, "b": 2, "c": 3}
    dict2 = {"c": 3, "a": 1, "b": 2}
    assert _hash_dict(dict1) == _hash_dict(dict2)


def test_hash_dict_different():
    """Testa que hashes diferentes para dicts diferentes."""
    dict1 = {"a": 1, "b": 2}
    dict2 = {"a": 1, "b": 3}
    assert _hash_dict(dict1) != _hash_dict(dict2)


def test_hash_dict_empty():
    """Testa hash de dict vazio."""
    result = _hash_dict({})
    assert isinstance(result, str)
    assert len(result) == 64  # SHA256 hex


def test_normalize_note_dict_complete():
    """Testa normalização de dict completo."""
    note = {
        "id": "123",
        "created_at": "2025-12-28",
        "author_email": "test@example.com",
        "author_name": "Test User",
        "body": "Nota de teste",
        "is_pinned": True,
        "is_done": False,
        "formatted_line": "linha formatada",
        "tag_name": "importante",
    }
    result = _normalize_note(note)
    assert result["id"] == "123"
    assert result["body"] == "Nota de teste"
    assert result["is_pinned"] is True
    assert result["is_done"] is False


def test_normalize_note_dict_minimal():
    """Testa normalização de dict com campos mínimos."""
    note = {"body": "Texto simples"}
    result = _normalize_note(note)
    assert result["body"] == "Texto simples"
    assert result["id"] == ""
    assert result["is_pinned"] is False


def test_normalize_note_tuple_4_elements():
    """Testa normalização de tuple com 4 elementos (id, ts, author, body)."""
    note = ("456", "2025-12-28", "author@test.com", "Conteúdo da nota")
    result = _normalize_note(note)
    assert result["id"] == "456"
    assert result["created_at"] == "2025-12-28"
    assert result["author_email"] == "author@test.com"
    assert result["body"] == "Conteúdo da nota"


def test_normalize_note_tuple_3_elements():
    """Testa normalização de tuple com 3 elementos (ts, author, body)."""
    note = ("2025-12-28", "author@test.com", "Texto")
    result = _normalize_note(note)
    assert result["created_at"] == "2025-12-28"
    assert result["author_email"] == "author@test.com"
    assert result["body"] == "Texto"
    assert result["id"] == ""


def test_normalize_note_tuple_2_elements():
    """Testa normalização de tuple com 2 elementos (author, body)."""
    note = ("author@test.com", "Mensagem")
    result = _normalize_note(note)
    assert result["author_email"] == "author@test.com"
    assert result["body"] == "Mensagem"


def test_normalize_note_tuple_1_element():
    """Testa normalização de tuple com 1 elemento (body)."""
    note = ("Apenas texto",)
    result = _normalize_note(note)
    assert result["body"] == "Apenas texto"


def test_normalize_note_dataclass():
    """Testa normalização de dataclass."""

    @dataclass
    class FakeNote:
        id: str
        body: str
        author_email: str
        created_at: str
        is_pinned: bool = False

    fake = FakeNote(
        id="789",
        body="Nota do dataclass",
        author_email="dc@example.com",
        created_at="2025-12-28",
        is_pinned=True,
    )
    result = _normalize_note(fake)
    assert result["id"] == "789"
    assert result["body"] == "Nota do dataclass"
    assert result["author_email"] == "dc@example.com"
    assert result["is_pinned"] is True


def test_normalize_note_object_with_attributes():
    """Testa normalização de objeto com atributos."""

    class FakeNoteObj:
        def __init__(self):
            self.id = "obj-1"
            self.body = "Corpo do objeto"
            self.author_email = "obj@test.com"
            self.created_at = "2025-12-28"

    fake = FakeNoteObj()
    result = _normalize_note(fake)
    assert result["id"] == "obj-1"
    assert result["body"] == "Corpo do objeto"
    assert result["author_email"] == "obj@test.com"


def test_normalize_note_fallback_invalid_input():
    """Testa fallback para input inválido (retorna dict com body=str(n))."""
    result = _normalize_note("string inválida")
    assert isinstance(result, dict)
    assert result["id"] == ""
    assert result["body"] == "string inválida"  # Fallback: str(n)
