# -*- coding: utf-8 -*-
"""Testes para format_cnpj em src/utils/formatters.py."""

import unittest

from src.utils.formatters import format_cnpj


class TestFormatCnpj(unittest.TestCase):
    """Verifica comportamento consistente e sem retorno de 'lixo cru'."""

    # --- entradas inválidas / vazias ---

    def test_none_retorna_vazio(self):
        self.assertEqual(format_cnpj(None), "")

    def test_string_vazia_retorna_vazio(self):
        self.assertEqual(format_cnpj(""), "")

    def test_zero_inteiro_retorna_vazio(self):
        self.assertEqual(format_cnpj(0), "")

    # --- 14 dígitos: aplica máscara ---

    def test_14_digitos_sem_formatacao(self):
        self.assertEqual(format_cnpj("12345678000190"), "12.345.678/0001-90")

    def test_14_digitos_como_int(self):
        self.assertEqual(format_cnpj(12345678000190), "12.345.678/0001-90")

    def test_cnpj_ja_formatado(self):
        self.assertEqual(format_cnpj("12.345.678/0001-90"), "12.345.678/0001-90")

    # --- menos de 14 dígitos: retorna só os dígitos, sem máscara, sem "lixo" ---

    def test_menos_de_14_digitos_retorna_digitos(self):
        result = format_cnpj("123")
        # deve retornar apenas os dígitos, nunca "str(raw)" com caracteres extras
        self.assertEqual(result, "123")

    def test_string_com_pontuacao_menos_14_retorna_digitos(self):
        result = format_cnpj("1234-")
        # str(raw) seria "1234-", mas esperamos só dígitos
        self.assertEqual(result, "1234")

    def test_mais_de_14_digitos_retorna_digitos(self):
        # 15 dígitos -> retorna os dígitos sem máscara
        result = format_cnpj("123456789001234")
        self.assertEqual(result, "123456789001234")

    def test_sem_digitos_retorna_vazio(self):
        # string só com letras/pontuação -> sem dígitos -> ""
        self.assertEqual(format_cnpj("ABC--"), "")


if __name__ == "__main__":
    unittest.main()
