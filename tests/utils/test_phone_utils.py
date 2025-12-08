# -*- coding: utf-8 -*-
"""Testes unitários para src/utils/phone_utils.py."""

from src.utils import phone_utils


class TestOnlyDigits:
    """Testes para a função only_digits()."""

    def test_removes_non_digits(self):
        """Remove caracteres não numéricos."""
        assert phone_utils.only_digits("(11) 98765-4321") == "11987654321"

    def test_handles_plus_sign(self):
        """Remove o sinal de + do número."""
        assert phone_utils.only_digits("+55 11 98765-4321") == "5511987654321"

    def test_handles_empty_string(self):
        """Retorna string vazia para entrada vazia."""
        assert phone_utils.only_digits("") == ""

    def test_handles_none(self):
        """Retorna string vazia para None."""
        assert phone_utils.only_digits(None) == ""

    def test_only_digits_passthrough(self):
        """Mantém string que já é só dígitos."""
        assert phone_utils.only_digits("11987654321") == "11987654321"

    def test_handles_letters(self):
        """Remove letras misturadas com números."""
        assert phone_utils.only_digits("1a2b3c") == "123"


class TestNormalizeBrWhatsapp:
    """Testes para a função normalize_br_whatsapp()."""

    def test_celular_com_codigo_pais(self):
        """Normaliza celular com +55."""
        result = phone_utils.normalize_br_whatsapp("+55 11 98765-4321")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "987654321"

    def test_celular_sem_codigo_pais(self):
        """Normaliza celular sem código do país."""
        result = phone_utils.normalize_br_whatsapp("(11) 98765-4321")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "987654321"

    def test_celular_apenas_digitos(self):
        """Normaliza celular com apenas dígitos."""
        result = phone_utils.normalize_br_whatsapp("11987654321")
        assert result["e164"] == "5511987654321"
        assert result["display"] == "(11) 98765-4321"
        assert result["ddd"] == "11"
        assert result["local"] == "987654321"

    def test_telefone_fixo(self):
        """Normaliza telefone fixo (8 dígitos)."""
        result = phone_utils.normalize_br_whatsapp("(11) 3456-7890")
        assert result["e164"] == "551134567890"
        assert result["display"] == "(11) 3456-7890"
        assert result["ddd"] == "11"
        assert result["local"] == "34567890"

    def test_telefone_fixo_com_codigo_pais(self):
        """Normaliza fixo com código do país."""
        result = phone_utils.normalize_br_whatsapp("+55 11 3456-7890")
        assert result["e164"] == "551134567890"
        assert result["display"] == "(11) 3456-7890"
        assert result["ddd"] == "11"
        assert result["local"] == "34567890"

    def test_numero_curto_sem_ddd(self):
        """Trata número curto sem DDD."""
        result = phone_utils.normalize_br_whatsapp("98765432")
        assert result["ddd"] == ""
        assert result["local"] == "98765432"
        assert result["e164"] == ""  # Sem DDD não gera e164
        assert result["display"] == "98765432"

    def test_entrada_vazia(self):
        """Trata entrada vazia."""
        result = phone_utils.normalize_br_whatsapp("")
        assert result["e164"] == ""
        assert result["display"] == ""
        assert result["ddd"] == ""
        assert result["local"] == ""

    def test_entrada_com_espacos_extras(self):
        """Remove espaços extras corretamente."""
        result = phone_utils.normalize_br_whatsapp("  +55  11   98765   4321  ")
        assert result["e164"] == "5511987654321"
        assert result["ddd"] == "11"

    def test_diferentes_ddds(self):
        """Testa com diferentes DDDs brasileiros."""
        # São Paulo
        result_sp = phone_utils.normalize_br_whatsapp("11987654321")
        assert result_sp["ddd"] == "11"

        # Rio de Janeiro
        result_rj = phone_utils.normalize_br_whatsapp("21987654321")
        assert result_rj["ddd"] == "21"

        # Minas Gerais
        result_mg = phone_utils.normalize_br_whatsapp("31987654321")
        assert result_mg["ddd"] == "31"

    def test_celular_com_digitos_extras(self):
        """Trunca dígitos extras além de 9 no número local."""
        # Número com mais de 9 dígitos no local - deve truncar
        result = phone_utils.normalize_br_whatsapp("119876543210")  # 10 dígitos local
        assert len(result["local"]) == 9
        assert result["local"] == "987654321"

    def test_formato_display_celular_vs_fixo(self):
        """Verifica formato de display diferente para celular e fixo."""
        # Celular: (DD) 9XXXX-XXXX
        celular = phone_utils.normalize_br_whatsapp("11987654321")
        assert celular["display"] == "(11) 98765-4321"

        # Fixo: (DD) XXXX-XXXX
        fixo = phone_utils.normalize_br_whatsapp("1134567890")
        assert fixo["display"] == "(11) 3456-7890"


class TestEdgeCases:
    """Testes de casos de borda e situações especiais."""

    def test_numero_apenas_zeros(self):
        """Testa número composto apenas de zeros."""
        result = phone_utils.normalize_br_whatsapp("00000000000")
        assert result["ddd"] == "00"
        assert result["local"] == "000000000"

    def test_numero_com_caracteres_especiais(self):
        """Remove caracteres especiais variados."""
        result = phone_utils.normalize_br_whatsapp("(11) 9.8765-4321 [cel]")
        assert result["e164"] == "5511987654321"

    def test_numero_internacional_falso(self):
        """Trata número que começa com 55 mas não é código do país."""
        # Se vier 5511..., assume que 55 é código do país
        result = phone_utils.normalize_br_whatsapp("5511987654321")
        assert result["ddd"] == "11"
        assert result["e164"] == "5511987654321"
