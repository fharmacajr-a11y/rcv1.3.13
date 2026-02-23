# -*- coding: utf-8 -*-
"""Testes para src/utils/phone_utils.py"""

import pytest


class TestOnlyPhoneDigits:
    """Testes para only_phone_digits()"""

    def test_empty(self):
        from src.utils.phone_utils import only_phone_digits
        assert only_phone_digits("") == ""
        assert only_phone_digits(None) == ""

    def test_only_digits(self):
        from src.utils.phone_utils import only_phone_digits
        assert only_phone_digits("11987654321") == "11987654321"

    def test_with_formatting(self):
        from src.utils.phone_utils import only_phone_digits
        assert only_phone_digits("(11) 98765-4321") == "11987654321"
        assert only_phone_digits("+55 11 98765-4321") == "5511987654321"

    def test_with_spaces_and_special(self):
        from src.utils.phone_utils import only_phone_digits
        assert only_phone_digits("  11 . 98765 - 4321  ") == "11987654321"


class TestFormatPhoneBr:
    """Testes para format_phone_br()"""

    def test_empty(self):
        from src.utils.phone_utils import format_phone_br
        assert format_phone_br("") == ""
        assert format_phone_br(None) == ""

    def test_celular_9_digits(self):
        from src.utils.phone_utils import format_phone_br
        assert format_phone_br("11987654321") == "+55 11 98765-4321"
        assert format_phone_br("5511987654321") == "+55 11 98765-4321"
        assert format_phone_br("(11) 98765-4321") == "+55 11 98765-4321"

    def test_fixo_8_digits(self):
        from src.utils.phone_utils import format_phone_br
        assert format_phone_br("1134567890") == "+55 11 3456-7890"

    def test_invalid_short(self):
        from src.utils.phone_utils import format_phone_br
        assert format_phone_br("1198765") == ""  # Muito curto

    def test_already_formatted(self):
        from src.utils.phone_utils import format_phone_br
        # Deve retornar formatado mesmo se já estiver formatado (após normalização)
        result = format_phone_br("+55 11 98765-4321")
        assert result == "+55 11 98765-4321"

    def test_with_country_code(self):
        from src.utils.phone_utils import format_phone_br
        assert format_phone_br("5521999887766") == "+55 21 99988-7766"

    def test_various_formats(self):
        from src.utils.phone_utils import format_phone_br
        # Diferentes formatos de entrada devem resultar no mesmo output
        expected = "+55 11 98765-4321"
        assert format_phone_br("11987654321") == expected
        assert format_phone_br("(11)987654321") == expected
        assert format_phone_br("11 98765-4321") == expected
        assert format_phone_br("+5511987654321") == expected


class TestIsValidBrPhone:
    """Testes para is_valid_br_phone()"""

    def test_valid_celular(self):
        from src.utils.phone_utils import is_valid_br_phone
        assert is_valid_br_phone("11987654321") is True
        assert is_valid_br_phone("5511987654321") is True

    def test_valid_fixo(self):
        from src.utils.phone_utils import is_valid_br_phone
        assert is_valid_br_phone("1134567890") is True

    def test_invalid(self):
        from src.utils.phone_utils import is_valid_br_phone
        assert is_valid_br_phone("") is False
        assert is_valid_br_phone(None) is False
        assert is_valid_br_phone("1198765") is False  # Muito curto


class TestNormalizeBrWhatsapp:
    """Testes para normalize_br_whatsapp()"""

    def test_empty(self):
        from src.utils.phone_utils import normalize_br_whatsapp
        result = normalize_br_whatsapp("")
        assert result["e164"] == ""

    def test_with_55_prefix(self):
        from src.utils.phone_utils import normalize_br_whatsapp
        result = normalize_br_whatsapp("+55 11 98765-4321")
        assert result["e164"] == "5511987654321"
        assert result["ddd"] == "11"

    def test_without_55_prefix(self):
        from src.utils.phone_utils import normalize_br_whatsapp
        result = normalize_br_whatsapp("11987654321")
        assert result["e164"] == "5511987654321"
        assert result["ddd"] == "11"
