# -*- coding: utf-8 -*-
"""Testes para src/utils/formatters.py (format_cnpj)"""

import pytest


class TestFormatCnpj:
    """Testes para format_cnpj()"""

    def test_empty(self):
        from src.utils.formatters import format_cnpj
        assert format_cnpj("") == ""
        assert format_cnpj(None) == ""

    def test_valid_digits_only(self):
        from src.utils.formatters import format_cnpj
        assert format_cnpj("12345678000190") == "12.345.678/0001-90"

    def test_valid_already_formatted(self):
        from src.utils.formatters import format_cnpj
        # Deve retornar formatado mesmo se já estiver
        assert format_cnpj("12.345.678/0001-90") == "12.345.678/0001-90"

    def test_valid_partial_formatting(self):
        from src.utils.formatters import format_cnpj
        # Com alguns separadores (re.sub remove tudo que não é dígito)
        assert format_cnpj("12345678/000190") == "12.345.678/0001-90"

    def test_invalid_short(self):
        from src.utils.formatters import format_cnpj
        # Retorna original se não tiver 14 dígitos
        assert format_cnpj("123456") == "123456"

    def test_invalid_long(self):
        from src.utils.formatters import format_cnpj
        # 15 dígitos - retorna original
        assert format_cnpj("123456789012345") == "123456789012345"

    def test_int_input(self):
        from src.utils.formatters import format_cnpj
        # Aceita int
        assert format_cnpj(12345678000190) == "12.345.678/0001-90"

    def test_with_letters_mixed(self):
        from src.utils.formatters import format_cnpj
        # Letras são ignoradas, só dígitos são extraídos
        # "12345678000190ABC" tem 14 dígitos + letras = 14 dígitos após limpeza
        assert format_cnpj("12345678000190ABC") == "12.345.678/0001-90"

    def test_real_cnpjs(self):
        from src.utils.formatters import format_cnpj
        # CNPJs reais (fictícios para teste)
        assert format_cnpj("00000000000191") == "00.000.000/0001-91"
        assert format_cnpj("11222333000181") == "11.222.333/0001-81"
