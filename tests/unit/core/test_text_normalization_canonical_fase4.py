# -*- coding: utf-8 -*-
"""
tests/unit/core/test_text_normalization_canonical_fase4.py

Suite completa de testes para o módulo canônico de normalização de texto (FASE 4).
Testa remoção de diacríticos (acentos) e normalização ASCII.
"""

from __future__ import annotations

import pytest

from src.core.text_normalization import normalize_ascii, strip_diacritics


class TestStripDiacritics:
    """Testes para a função strip_diacritics - remoção de acentos."""

    def test_strip_diacritics_none(self) -> None:
        """None deve retornar string vazia."""
        assert strip_diacritics(None) == ""

    def test_strip_diacritics_empty(self) -> None:
        """String vazia deve retornar vazia."""
        assert strip_diacritics("") == ""

    def test_strip_diacritics_no_accents(self) -> None:
        """String sem acentos deve permanecer inalterada."""
        assert strip_diacritics("ABC123") == "ABC123"

    def test_strip_diacritics_common_accents(self) -> None:
        """Deve remover acentos comuns do português."""
        assert strip_diacritics("áéíóúâêôãõç") == "aeiouaeoaoc"
        assert strip_diacritics("ÀÈÌÒÙÄËÏÖÜ") == "AEIOUAEIOU"

    def test_strip_diacritics_with_spaces(self) -> None:
        """Deve preservar espaços ao remover acentos."""
        assert strip_diacritics("José da Silva") == "Jose da Silva"
        assert strip_diacritics("São Paulo") == "Sao Paulo"

    def test_strip_diacritics_with_numbers(self) -> None:
        """Deve preservar números ao remover acentos."""
        assert strip_diacritics("123 São José 456") == "123 Sao Jose 456"

    def test_strip_diacritics_mixed_content(self) -> None:
        """Deve remover acentos mantendo pontuação e números."""
        # º (ordinal indicator) é um caractere próprio, não um acento combinante
        assert strip_diacritics("Rua José, nº 123") == "Rua Jose, nº 123"

    def test_strip_diacritics_cedilla(self) -> None:
        """Deve remover cedilha (ç → c)."""
        assert strip_diacritics("Açúcar") == "Acucar"
        assert strip_diacritics("Coração") == "Coracao"

    def test_strip_diacritics_unicode_edge_cases(self) -> None:
        """Deve lidar com casos complexos de Unicode."""
        # Emoji não deve quebrar
        result = strip_diacritics("Café ☕")
        assert "Cafe" in result  # Emoji pode ser preservado ou removido, depende da implementação

    def test_strip_diacritics_preserves_length(self) -> None:
        """Remoção de acentos não deve alterar drasticamente o tamanho (exceto por composições)."""
        original = "José"
        stripped = strip_diacritics(original)
        assert stripped == "Jose"
        assert len(stripped) == len(original)  # 4 caracteres

    def test_strip_diacritics_idempotent(self) -> None:
        """Aplicar strip_diacritics duas vezes deve ter mesmo resultado."""
        text = "São José"
        once = strip_diacritics(text)
        twice = strip_diacritics(once)
        assert once == twice

    def test_strip_diacritics_european_chars(self) -> None:
        """Deve remover acentos de caracteres europeus."""
        assert strip_diacritics("Zürich") == "Zurich"
        assert strip_diacritics("François") == "Francois"

    def test_strip_diacritics_uppercase_lowercase(self) -> None:
        """Deve funcionar para maiúsculas e minúsculas."""
        assert strip_diacritics("ÁÉÍ") == "AEI"
        assert strip_diacritics("áéí") == "aei"


class TestNormalizeAscii:
    """Testes para a função normalize_ascii - conversão para ASCII puro."""

    def test_normalize_ascii_none(self) -> None:
        """None deve retornar string vazia."""
        assert normalize_ascii(None) == ""

    def test_normalize_ascii_empty(self) -> None:
        """String vazia deve retornar vazia."""
        assert normalize_ascii("") == ""

    def test_normalize_ascii_plain_text(self) -> None:
        """Texto ASCII simples deve permanecer inalterado."""
        assert normalize_ascii("HelloWorld") == "HelloWorld"

    def test_normalize_ascii_removes_accents(self) -> None:
        """Deve remover acentos antes de converter para ASCII."""
        assert normalize_ascii("José") == "Jose"
        assert normalize_ascii("São Paulo") == "Sao Paulo"

    def test_normalize_ascii_only_ascii_chars(self) -> None:
        """Resultado deve conter apenas caracteres ASCII."""
        result = normalize_ascii("Café ☕ 中文")
        # Deve conter apenas ASCII (código < 128)
        assert all(ord(ch) < 128 for ch in result)

    def test_normalize_ascii_emoji_removed(self) -> None:
        """Emoji e símbolos não-ASCII devem ser removidos."""
        result = normalize_ascii("Text 😀 🎉")
        # Emoji devem ser removidos na conversão ASCII
        assert "😀" not in result
        assert "🎉" not in result
        assert result.strip() == "Text"

    def test_normalize_ascii_cedilla(self) -> None:
        """Cedilha deve ser convertida para c."""
        assert normalize_ascii("Açúcar") == "Acucar"

    def test_normalize_ascii_preserves_spaces(self) -> None:
        """Espaços devem ser preservados."""
        assert normalize_ascii("Hello World") == "Hello World"

    def test_normalize_ascii_preserves_numbers(self) -> None:
        """Números devem ser preservados."""
        assert normalize_ascii("Rua 123") == "Rua 123"

    def test_normalize_ascii_preserves_punctuation(self) -> None:
        """Pontuação ASCII deve ser preservada."""
        result = normalize_ascii("Hello, World!")
        assert result == "Hello, World!"

    def test_normalize_ascii_idempotent(self) -> None:
        """Aplicar normalize_ascii duas vezes deve ter mesmo resultado."""
        text = "São José ☕"
        once = normalize_ascii(text)
        twice = normalize_ascii(once)
        assert once == twice

    def test_normalize_ascii_complex_input(self) -> None:
        """Deve lidar com input complexo misturando Unicode, ASCII, emoji."""
        result = normalize_ascii("Café ☕ 123 - São Paulo (SP)")
        assert "Cafe" in result
        assert "123" in result
        assert "Sao Paulo" in result
        assert all(ord(ch) < 128 for ch in result)


class TestWrapperDelegation:
    """Testes para garantir que wrappers delegam corretamente para implementação canônica."""

    def test_text_utils_normalize_ascii_wrapper(self) -> None:
        """Wrapper em text_utils deve delegar para core."""
        from src.utils.text_utils import normalize_ascii as text_utils_normalize

        assert text_utils_normalize("José") == "Jose"
        assert text_utils_normalize(None) == ""

    def test_textnorm_strip_diacritics_wrapper(self) -> None:
        """Wrapper em textnorm deve delegar para core."""
        from src.core.textnorm import _strip_diacritics as textnorm_strip

        assert textnorm_strip("São Paulo") == "Sao Paulo"

    def test_cnpj_norm_strip_diacritics_wrapper(self) -> None:
        """Wrapper em cnpj_norm deve delegar para core."""
        from src.core.cnpj_norm import _strip_diacritics as cnpj_strip

        assert cnpj_strip("Açúcar") == "Acucar"

    def test_storage_key_strip_diacritics_wrapper(self) -> None:
        """Wrapper em storage_key deve delegar para core."""
        from src.core.storage_key import _strip_diacritics as storage_strip

        assert storage_strip("José") == "Jose"

    def test_subfolders_strip_diacritics_wrapper(self) -> None:
        """Wrapper em subfolders deve delegar para core."""
        from src.shared.subfolders import _strip_diacritics as subfolder_strip

        assert subfolder_strip("São José") == "Sao Jose"

    def test_supabase_storage_normalize_key(self) -> None:
        """normalize_key_for_storage deve usar normalize_ascii do core."""
        from src.adapters.storage.supabase_storage import normalize_key_for_storage

        # Testa normalização apenas no último segmento (nome do arquivo)
        result = normalize_key_for_storage("pasta/subpasta/Relatório José.pdf")
        assert result == "pasta/subpasta/Relatorio Jose.pdf"


class TestEdgeCases:
    """Testes para casos extremos e comportamentos especiais."""

    def test_strip_diacritics_whitespace_only(self) -> None:
        """String com apenas espaços deve retornar espaços."""
        assert strip_diacritics("   ") == "   "

    def test_normalize_ascii_whitespace_only(self) -> None:
        """String com apenas espaços deve retornar espaços."""
        assert normalize_ascii("   ") == "   "

    def test_strip_diacritics_special_chars(self) -> None:
        """Caracteres especiais ASCII devem ser preservados."""
        assert strip_diacritics("@#$%&*") == "@#$%&*"

    def test_normalize_ascii_special_chars(self) -> None:
        """Caracteres especiais ASCII devem ser preservados."""
        assert normalize_ascii("@#$%&*") == "@#$%&*"

    def test_strip_diacritics_newlines(self) -> None:
        """Quebras de linha devem ser preservadas."""
        result = strip_diacritics("José\nSão")
        assert result == "Jose\nSao"

    def test_normalize_ascii_newlines(self) -> None:
        """Quebras de linha devem ser preservadas."""
        result = normalize_ascii("José\nSão")
        assert result == "Jose\nSao"

    def test_strip_diacritics_tabs(self) -> None:
        """Tabs devem ser preservados."""
        result = strip_diacritics("José\tSão")
        assert result == "Jose\tSao"

    def test_normalize_ascii_tabs(self) -> None:
        """Tabs devem ser preservados."""
        result = normalize_ascii("José\tSão")
        assert result == "Jose\tSao"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
