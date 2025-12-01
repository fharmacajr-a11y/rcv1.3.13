# -*- coding: utf-8 -*-
"""
Testes de cobertura para src/utils/phone_utils.py
Objetivo: atingir ≥85% de cobertura com testes sólidos de edge cases.
"""

import pytest
from src.utils.phone_utils import only_digits, normalize_br_whatsapp


# ==================== only_digits ====================


class TestOnlyDigits:
    """Testa extração de apenas dígitos de strings."""

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("123-456-789", "123456789"),
            ("(11) 98765-4321", "11987654321"),
            ("ABC123DEF456", "123456"),
            ("", ""),
            ("NoDigitsHere!", ""),
            ("  123  ", "123"),
            ("+55 11 98765-4321", "5511987654321"),
            ("R$ 1.234,56", "123456"),
        ],
    )
    def test_only_digits_various_inputs(self, input_str, expected):
        """Testa only_digits com vários formatos de entrada."""
        assert only_digits(input_str) == expected

    def test_only_digits_none_input(self):
        """Testa only_digits com None."""
        assert only_digits(None) == ""


# ==================== normalize_br_whatsapp ====================


class TestNormalizeBrWhatsapp:
    """Testa normalização completa de números WhatsApp brasileiros."""

    def test_normalize_celular_com_ddd_9_digitos(self):
        """Testa celular com DDD e 9 dígitos (padrão atual)."""
        result = normalize_br_whatsapp("11987654321")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "987654321"

    def test_normalize_celular_formatado(self):
        """Testa celular já formatado com parênteses e traços."""
        result = normalize_br_whatsapp("(11) 98765-4321")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "987654321"

    def test_normalize_celular_com_55_prefixado(self):
        """Testa celular que já vem com 55 no início."""
        result = normalize_br_whatsapp("5511987654321")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "987654321"

    def test_normalize_celular_com_plus_55(self):
        """Testa celular com +55 internacional."""
        result = normalize_br_whatsapp("+55 11 98765-4321")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "987654321"

    def test_normalize_fixo_8_digitos(self):
        """Testa telefone fixo com 8 dígitos."""
        result = normalize_br_whatsapp("1133334444")
        assert result["e164"] == "551133334444"
        assert result["display"] == "(11) 3333-4444"
        assert result["ddd"] == "11"
        assert result["local"] == "33334444"

    def test_normalize_fixo_formatado(self):
        """Testa telefone fixo formatado."""
        result = normalize_br_whatsapp("(21) 3333-4444")
        assert result["e164"] == "552133334444"
        assert result["display"] == "(21) 3333-4444"
        assert result["ddd"] == "21"
        assert result["local"] == "33334444"

    def test_normalize_fixo_com_55(self):
        """Testa fixo que já vem com 55."""
        result = normalize_br_whatsapp("551133334444")
        assert result["e164"] == "551133334444"
        assert result["display"] == "(11) 3333-4444"
        assert result["ddd"] == "11"
        assert result["local"] == "33334444"

    def test_normalize_numero_curto_sem_ddd(self):
        """Testa número muito curto (sem DDD completo)."""
        result = normalize_br_whatsapp("12345")
        # Sem DDD suficiente, trata tudo como local
        assert result["e164"] == ""  # sem e164 válido
        assert result["ddd"] == ""
        assert result["local"] == "12345"

    def test_normalize_numero_vazio(self):
        """Testa string vazia."""
        result = normalize_br_whatsapp("")
        assert result["e164"] == ""
        assert result["display"] == ""
        assert result["ddd"] == ""
        assert result["local"] == ""

    def test_normalize_numero_com_letras(self):
        """Testa número misturado com letras."""
        result = normalize_br_whatsapp("ABC11987654321DEF")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"

    def test_normalize_numero_10_digitos_celular_antigo(self):
        """Testa celular antigo com 10 dígitos (antes do 9º dígito)."""
        result = normalize_br_whatsapp("1187654321")
        # 10 dígitos: DDD=11, local=87654321 (8 dígitos)
        assert result["e164"] == "551187654321"
        assert result["display"] == "(11) 8765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "87654321"

    def test_normalize_numero_muito_longo_trunca(self):
        """Testa número com mais de 11 dígitos (deve truncar local)."""
        result = normalize_br_whatsapp("11987654321999")
        # Deve pegar DDD=11, local até 9 dígitos
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "987654321"

    def test_normalize_diferentes_ddds(self):
        """Testa vários DDDs diferentes."""
        # DDD 21 (Rio)
        result = normalize_br_whatsapp("21987654321")
        assert result["e164"] == "5521987654321"
        assert result["ddd"] == "21"

        # DDD 85 (Fortaleza)
        result = normalize_br_whatsapp("85987654321")
        assert result["e164"] == "5585987654321"
        assert result["ddd"] == "85"

    def test_normalize_apenas_ddd_sem_local(self):
        """Testa entrada com apenas 2 dígitos (só DDD)."""
        result = normalize_br_whatsapp("11")
        # Com menos de 10 dígitos, não extrai DDD - trata tudo como local
        assert result["e164"] == ""  # sem local suficiente, não monta e164
        assert result["ddd"] == ""
        assert result["local"] == "11"
        assert result["display"] == "11"

    def test_normalize_9_digitos_local_mantido(self):
        """Testa que local com 9 dígitos é mantido completo."""
        result = normalize_br_whatsapp("11987654321")
        assert len(result["local"]) == 9
        assert result["local"] == "987654321"

    def test_normalize_8_digitos_local_mantido(self):
        """Testa que local com 8 dígitos é mantido completo."""
        result = normalize_br_whatsapp("1133334444")
        assert len(result["local"]) == 8
        assert result["local"] == "33334444"

    def test_normalize_display_sem_ddd(self):
        """Testa display quando não há DDD completo."""
        result = normalize_br_whatsapp("12345")
        assert result["display"] == "12345"  # só local, sem formatação

    def test_normalize_display_com_ddd_sem_local_completo(self):
        """Testa display quando há DDD mas local incompleto."""
        result = normalize_br_whatsapp("11123")
        # Com menos de 10 dígitos, não extrai DDD - trata tudo como local
        assert result["display"] == "11123"
        assert result["ddd"] == ""
        assert result["local"] == "11123"

    def test_normalize_numero_com_espacos_extras(self):
        """Testa número com muitos espaços."""
        result = normalize_br_whatsapp("  11  9  8765  4321  ")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"

    def test_normalize_numero_com_caracteres_especiais(self):
        """Testa número com vários caracteres especiais."""
        result = normalize_br_whatsapp("(+55) 11-98765.4321")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"

    def test_normalize_edge_case_exatamente_10_digitos(self):
        """Testa edge case com exatamente 10 dígitos."""
        result = normalize_br_whatsapp("1133334444")
        assert len(result["e164"]) == 12  # 55 + 10
        assert result["display"] == "(11) 3333-4444"

    def test_normalize_edge_case_exatamente_11_digitos(self):
        """Testa edge case com exatamente 11 dígitos."""
        result = normalize_br_whatsapp("11987654321")
        assert len(result["e164"]) == 13  # 55 + 11
        assert result["display"] == "(11) 98765-4321"

    def test_normalize_celular_comeca_com_9(self):
        """Testa que celulares com 9 dígitos começam com 9."""
        result = normalize_br_whatsapp("11987654321")
        assert result["local"].startswith("9")
        assert len(result["local"]) == 9

    def test_normalize_fixo_nao_comeca_com_9(self):
        """Testa que fixos com 8 dígitos não começam com 9."""
        result = normalize_br_whatsapp("1133334444")
        assert not result["local"].startswith("9")
        assert len(result["local"]) == 8
