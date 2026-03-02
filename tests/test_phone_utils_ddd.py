# -*- coding: utf-8 -*-
"""Testes para validação de DDD em normalize_br_whatsapp (phone_utils.py)."""

import unittest

from src.utils.phone_utils import normalize_br_whatsapp


class TestNormalizeBrWhatsappDdd(unittest.TestCase):
    """Verifica que DDDs inválidos (começando com 0) são rejeitados."""

    def test_ddd_00_invalido(self):
        """DDD '00' deve resultar em retorno vazio (inválido)."""
        result = normalize_br_whatsapp("0098765432109")
        self.assertEqual(result["e164"], "")
        self.assertEqual(result["ddd"], "")

    def test_ddd_01_invalido(self):
        """DDD iniciando com 0 deve ser rejeitado."""
        result = normalize_br_whatsapp("0187654321")
        self.assertEqual(result["e164"], "")

    def test_ddd_valido_11(self):
        """DDD 11 é válido e deve gerar e164 correto."""
        result = normalize_br_whatsapp("11987654321")
        self.assertEqual(result["ddd"], "11")
        self.assertTrue(result["e164"].startswith("55"))
        self.assertIn("11", result["e164"])

    def test_ddd_valido_21(self):
        """DDD 21 é válido."""
        result = normalize_br_whatsapp("21987654321")
        self.assertEqual(result["ddd"], "21")
        self.assertNotEqual(result["e164"], "")

    def test_ddd_valido_com_prefixo_55(self):
        """DDD válido vindo com prefixo +55."""
        result = normalize_br_whatsapp("+5511987654321")
        self.assertEqual(result["ddd"], "11")
        self.assertNotEqual(result["e164"], "")

    def test_entrada_vazia_retorna_vazio(self):
        """Entrada vazia não deve lançar exceção."""
        result = normalize_br_whatsapp(None)
        self.assertEqual(result["e164"], "")
        self.assertEqual(result["ddd"], "")

    def test_ddd_99_valido(self):
        """DDD 99 (Maranhão) é válido (não começa com 0)."""
        result = normalize_br_whatsapp("99987654321")
        self.assertEqual(result["ddd"], "99")
        self.assertNotEqual(result["e164"], "")


if __name__ == "__main__":
    unittest.main()
