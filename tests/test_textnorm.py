# -*- coding: utf-8 -*-
"""Tests for src/core/textnorm.py - text normalization utilities."""

from __future__ import annotations


from src.core.textnorm import _strip_diacritics, join_and_normalize, normalize_search


class TestStripDiacritics:
    """Tests for _strip_diacritics helper."""

    def test_strip_diacritics_basic_accents(self):
        """Should remove common Portuguese accents."""
        assert _strip_diacritics("São Paulo") == "Sao Paulo"
        assert _strip_diacritics("José") == "Jose"
        assert _strip_diacritics("Açúcar") == "Acucar"

    def test_strip_diacritics_multiple_accents(self):
        """Should remove multiple types of accents."""
        assert _strip_diacritics("café") == "cafe"
        assert _strip_diacritics("Münich") == "Munich"
        assert _strip_diacritics("naïve") == "naive"

    def test_strip_diacritics_none(self):
        """Should return empty string for None."""
        assert _strip_diacritics(None) == ""

    def test_strip_diacritics_empty_string(self):
        """Should return empty string for empty input."""
        assert _strip_diacritics("") == ""

    def test_strip_diacritics_no_accents(self):
        """Should preserve text without accents."""
        assert _strip_diacritics("ABC 123") == "ABC 123"

    def test_strip_diacritics_preserves_case(self):
        """Should preserve original case."""
        assert _strip_diacritics("JOSÉ") == "JOSE"
        assert _strip_diacritics("josé") == "jose"


class TestNormalizeSearch:
    """Tests for normalize_search function."""

    def test_normalize_search_removes_accents(self):
        """Should remove accents from text."""
        assert normalize_search("São Paulo") == "saopaulo"

    def test_normalize_search_lowercase(self):
        """Should convert to lowercase."""
        assert normalize_search("TEXTO") == "texto"
        assert normalize_search("TeXtO") == "texto"

    def test_normalize_search_removes_punctuation(self):
        """Should remove punctuation marks."""
        assert normalize_search("hello, world!") == "helloworld"
        assert normalize_search("test-case.example") == "testcaseexample"

    def test_normalize_search_removes_spaces(self):
        """Should remove spaces and separators."""
        assert normalize_search("a b c") == "abc"
        assert normalize_search("  multiple   spaces  ") == "multiplespaces"

    def test_normalize_search_complex_text(self):
        """Should handle complex text with accents, punctuation, and case."""
        assert normalize_search("José da Silva - CPF: 123.456.789-00") == "josedasilvacpf12345678900"

    def test_normalize_search_none(self):
        """Should handle None value."""
        assert normalize_search(None) == ""

    def test_normalize_search_empty_string(self):
        """Should handle empty string."""
        assert normalize_search("") == ""

    def test_normalize_search_numbers(self):
        """Should preserve numbers."""
        assert normalize_search("123") == "123"
        assert normalize_search("ABC-123") == "abc123"

    def test_normalize_search_special_chars(self):
        """Should remove special characters."""
        assert normalize_search("user@example.com") == "userexamplecom"
        assert normalize_search("R$ 1.000,00") == "r100000"

    def test_normalize_search_cnpj(self):
        """Should normalize CNPJ (common use case)."""
        assert normalize_search("12.345.678/0001-90") == "12345678000190"

    def test_normalize_search_casefold_strength(self):
        """Should use casefold for stronger lowercase (German ß -> ss)."""
        result = normalize_search("Straße")
        # casefold converts ß to ss, then removes diacritics if any
        assert "ss" in result or "strasse" in result


class TestJoinAndNormalize:
    """Tests for join_and_normalize function."""

    def test_join_and_normalize_basic(self):
        """Should join and normalize multiple strings."""
        result = join_and_normalize("José", "da", "Silva")
        assert result == "josedasilva"

    def test_join_and_normalize_with_none(self):
        """Should handle None values in parts."""
        result = join_and_normalize("José", None, "Silva")
        assert result == "josesilva"

    def test_join_and_normalize_all_none(self):
        """Should handle all None values."""
        result = join_and_normalize(None, None, None)
        assert result == ""

    def test_join_and_normalize_empty_strings(self):
        """Should handle empty strings."""
        result = join_and_normalize("", "test", "")
        assert result == "test"

    def test_join_and_normalize_mixed_types(self):
        """Should convert non-string types to strings."""
        result = join_and_normalize("ID:", 12345, "Nome:", "José")
        assert "12345" in result
        assert "jose" in result

    def test_join_and_normalize_single_part(self):
        """Should work with single part."""
        result = join_and_normalize("José da Silva")
        assert result == "josedasilva"

    def test_join_and_normalize_no_parts(self):
        """Should handle no parts."""
        result = join_and_normalize()
        assert result == ""

    def test_join_and_normalize_cliente_search_blob(self):
        """Should work like cliente search blob (real use case)."""
        # Simulating cliente fields
        result = join_and_normalize(
            123,  # id
            "José Ltda",  # nome
            "José da Silva ME",  # razao_social
            "12.345.678/0001-90",  # cnpj
            "CLI-001",  # numero
            "Observação: Cliente VIP",  # obs
        )
        assert "123" in result
        assert "jose" in result
        assert "12345678000190" in result
        assert "cli001" in result
        assert "vip" in result
