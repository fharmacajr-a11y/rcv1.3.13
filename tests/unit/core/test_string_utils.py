# -*- coding: utf-8 -*-
"""Tests for src.core.string_utils module."""

from __future__ import annotations


from src.core.string_utils import only_digits


class TestOnlyDigits:
    """Test suite for the canonical only_digits function."""

    def test_removes_all_non_digits(self):
        """Deve remover todos os caracteres não numéricos."""
        assert only_digits("abc123def456") == "123456"
        assert only_digits("12.345.678/0001-90") == "12345678000190"
        assert only_digits("(11) 98765-4321") == "11987654321"

    def test_handles_none_input(self):
        """Deve retornar string vazia quando input é None."""
        assert only_digits(None) == ""

    def test_handles_empty_string(self):
        """Deve retornar string vazia quando input é vazio."""
        assert only_digits("") == ""

    def test_handles_only_non_digits(self):
        """Deve retornar string vazia quando não há dígitos."""
        assert only_digits("!@#$%^&*()") == ""
        assert only_digits("---///\\\\") == ""
        assert only_digits("abcdefg") == ""

    def test_handles_only_digits(self):
        """Deve retornar inalterado quando já contém apenas dígitos."""
        assert only_digits("123456") == "123456"
        assert only_digits("0") == "0"
        assert only_digits("9876543210") == "9876543210"

    def test_real_world_examples(self):
        """Testa com exemplos reais de CNPJ e telefone."""
        # CNPJ formatado
        assert only_digits("12.345.678/0001-90") == "12345678000190"

        # Telefone formatado
        assert only_digits("(11) 99999-9999") == "11999999999"
        assert only_digits("+55 11 98765-4321") == "5511987654321"

        # Misto
        assert only_digits("ID: 12345") == "12345"
        assert only_digits("REF#999-A") == "999"

    def test_preserves_only_ascii_digits(self):
        """Deve manter apenas dígitos ASCII 0-9."""
        assert only_digits("①②③123") == "123"  # Unicode digits são removidos
        assert only_digits("0123456789") == "0123456789"

    def test_type_coercion_compatibility(self):
        """Verifica compatibilidade com conversão str(value)."""
        # Quando usado com str(int) ou str(float)
        result = only_digits(str(12345))
        assert result == "12345"
