# -*- coding: utf-8 -*-
"""Testes de validação de bucket name em _normalize_bucket.

Cobre as regras S3/DNS:
- 3..63 caracteres
- apenas [a-z0-9.-]
- começa e termina com [a-z0-9]
- não contém ".."
- não é formato IP (ex: 192.168.0.1)
- string vazia/espaços => inválido
- None => usa DEFAULT_BUCKET
"""

import unittest

from src.adapters.storage.supabase_storage import (
    DEFAULT_BUCKET,
    InvalidBucketNameError,
    _normalize_bucket,
)

_DEFAULT = DEFAULT_BUCKET


# ---------------------------------------------------------------------------
# Casos válidos
# ---------------------------------------------------------------------------


class TestBucketValido(unittest.TestCase):
    def test_none_retorna_default(self):
        self.assertEqual(_normalize_bucket(None), _DEFAULT)

    def test_uppercase_normaliza_para_lower(self):
        self.assertEqual(_normalize_bucket("MeuBucket"), "meubucket")

    def test_nome_valido_simples(self):
        self.assertEqual(_normalize_bucket("meubucket"), "meubucket")

    def test_nome_com_hifen(self):
        self.assertEqual(_normalize_bucket("meu-bucket"), "meu-bucket")

    def test_nome_com_ponto_e_numero(self):
        self.assertEqual(_normalize_bucket("meu-bucket.1"), "meu-bucket.1")

    def test_tamanho_minimo_3(self):
        self.assertEqual(_normalize_bucket("abc"), "abc")

    def test_tamanho_maximo_63(self):
        name = "a" * 63
        self.assertEqual(_normalize_bucket(name), name)

    def test_espacos_ao_redor_sao_removidos(self):
        self.assertEqual(_normalize_bucket("  docs  "), "docs")

    def test_numeros_no_nome(self):
        self.assertEqual(_normalize_bucket("bucket123"), "bucket123")

    def test_nome_com_ponto_interno(self):
        self.assertEqual(_normalize_bucket("my.bucket"), "my.bucket")

    def test_misto_letras_numeros_hifen_ponto(self):
        self.assertEqual(_normalize_bucket("Rc-Docs.2"), "rc-docs.2")


# ---------------------------------------------------------------------------
# Casos inválidos — tipo de exceção
# ---------------------------------------------------------------------------


class TestBucketInvalido(unittest.TestCase):
    def _assert_invalido(self, value):
        with self.assertRaises(InvalidBucketNameError, msg=f"Esperava erro para {value!r}"):
            _normalize_bucket(value)

    # Vazio / espaços
    def test_string_vazia(self):
        self._assert_invalido("")

    def test_so_espacos(self):
        self._assert_invalido("   ")

    # Tamanho
    def test_tamanho_2_curto(self):
        self._assert_invalido("ab")

    def test_tamanho_64_longo(self):
        self._assert_invalido("a" * 64)

    def test_tamanho_1(self):
        self._assert_invalido("a")

    # Caracteres inválidos
    def test_underscore(self):
        self._assert_invalido("meu_bucket")

    def test_arroba(self):
        self._assert_invalido("meu@bucket")

    def test_espaco_interno(self):
        self._assert_invalido("meu bucket")

    def test_barra(self):
        self._assert_invalido("meu/bucket")

    # Começa/termina errado
    def test_hifen_no_inicio(self):
        self._assert_invalido("-abc")

    def test_hifen_no_fim(self):
        self._assert_invalido("abc-")

    def test_ponto_no_inicio(self):
        self._assert_invalido(".abc")

    def test_ponto_no_fim(self):
        self._assert_invalido("abc.")

    # Duplo ponto
    def test_dois_pontos_consecutivos(self):
        self._assert_invalido("a..b")

    def test_multiplos_pontos(self):
        self._assert_invalido("a...b")

    # Formato IP
    def test_ip_simples(self):
        self._assert_invalido("192.168.0.1")

    def test_ip_zeros(self):
        self._assert_invalido("0.0.0.0")

    def test_ip_255(self):
        self._assert_invalido("255.255.255.255")


# ---------------------------------------------------------------------------
# InvalidBucketNameError é subclasse de ValueError
# ---------------------------------------------------------------------------


class TestInvalidBucketNameError(unittest.TestCase):
    def test_eh_subclasse_de_value_error(self):
        self.assertTrue(issubclass(InvalidBucketNameError, ValueError))

    def test_pode_ser_capturado_como_value_error(self):
        with self.assertRaises(ValueError):
            _normalize_bucket("")

    def test_mensagem_contem_nome(self):
        try:
            _normalize_bucket("-ruim")
        except InvalidBucketNameError as exc:
            self.assertIn("-ruim", str(exc))
        else:
            self.fail("Esperava InvalidBucketNameError")

    def test_mensagem_vazio(self):
        try:
            _normalize_bucket("")
        except InvalidBucketNameError as exc:
            self.assertIn("vazi", str(exc).lower())  # "vazia" ou "vazio"
        else:
            self.fail("Esperava InvalidBucketNameError")


# ---------------------------------------------------------------------------
# Integração: SupabaseStorageAdapter.__init__ propaga InvalidBucketNameError
# ---------------------------------------------------------------------------


class TestAdapterInit(unittest.TestCase):
    def test_adapter_invalido_levanta_ao_instanciar(self):
        from src.adapters.storage.supabase_storage import SupabaseStorageAdapter

        with self.assertRaises(InvalidBucketNameError):
            SupabaseStorageAdapter(bucket="invalid_name!")

    def test_adapter_valido_nao_levanta(self):
        from src.adapters.storage.supabase_storage import SupabaseStorageAdapter

        adapter = SupabaseStorageAdapter(bucket="valid-bucket")
        self.assertEqual(adapter._bucket, "valid-bucket")

    def test_adapter_none_usa_default(self):
        from src.adapters.storage.supabase_storage import SupabaseStorageAdapter

        adapter = SupabaseStorageAdapter(bucket=None)
        self.assertEqual(adapter._bucket, _DEFAULT)

    def test_adapter_uppercase_normaliza(self):
        from src.adapters.storage.supabase_storage import SupabaseStorageAdapter

        adapter = SupabaseStorageAdapter(bucket="MyBucket")
        self.assertEqual(adapter._bucket, "mybucket")


# ---------------------------------------------------------------------------
# Exportação em __all__
# ---------------------------------------------------------------------------


class TestExportacao(unittest.TestCase):
    def test_invalido_bucket_name_error_em_all(self):
        import src.adapters.storage.supabase_storage as mod

        self.assertIn("InvalidBucketNameError", mod.__all__)


if __name__ == "__main__":
    unittest.main()
