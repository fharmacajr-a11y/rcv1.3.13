# -*- coding: utf-8 -*-
"""Testes para safe_int em src/utils/validators.py."""

import unittest

from src.utils.validators import safe_int


class TestSafeInt(unittest.TestCase):
    """Verifica que safe_int converte valores válidos e retorna default para inválidos."""

    def test_string_numerica_valida(self):
        self.assertEqual(safe_int("123"), 123)

    def test_string_com_espacos(self):
        self.assertEqual(safe_int(" 123 "), 123)

    def test_string_nao_numerica_retorna_default(self):
        self.assertEqual(safe_int("ABC"), 0)

    def test_none_retorna_default(self):
        self.assertEqual(safe_int(None), 0)

    def test_string_vazia_retorna_default(self):
        self.assertEqual(safe_int(""), 0)

    def test_int_direto(self):
        self.assertEqual(safe_int(42), 42)

    def test_float_retorna_default(self):
        # float como "3.9" não é int válido → retorna default
        self.assertEqual(safe_int(3.9), 0)

    def test_default_customizado(self):
        self.assertEqual(safe_int("XYZ", default=-1), -1)

    def test_zero_como_string(self):
        self.assertEqual(safe_int("0"), 0)

    def test_negativo(self):
        self.assertEqual(safe_int("-5"), -5)


if __name__ == "__main__":
    unittest.main()
