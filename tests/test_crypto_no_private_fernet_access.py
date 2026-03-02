# -*- coding: utf-8 -*-
"""Testes de crypto.py — ausência de atributos privados do Fernet e comportamento estável.

Garante:
a) O código-fonte do módulo não referencia _signing_key nem _encryption_key.
b) encrypt/decrypt continuam funcionando corretamente.
c) _reset_fernet_cache é idempotente e não quebra.
d) _secure_delete é honesta (sem gc.collect e sem acesso a internals).
"""

import inspect
import os
import unittest


# ---------------------------------------------------------------------------
# Fixture: garante chave válida e cache limpo para cada teste
# ---------------------------------------------------------------------------

_fake_key: str = ""  # preenchido em setUpModule


def setUpModule():  # noqa: N802
    global _fake_key
    from cryptography.fernet import Fernet

    _fake_key = Fernet.generate_key().decode("utf-8")


class _CryptoBase(unittest.TestCase):
    def setUp(self):
        os.environ["RC_CLIENT_SECRET_KEY"] = _fake_key
        import src.security.crypto as mod

        mod._reset_fernet_cache()

    def tearDown(self):
        import src.security.crypto as mod

        mod._reset_fernet_cache()
        os.environ.pop("RC_CLIENT_SECRET_KEY", None)


# ---------------------------------------------------------------------------
# A) Ausência de atributos privados do Fernet no código-fonte
# ---------------------------------------------------------------------------


class TestSemAtributosPrivados(unittest.TestCase):
    def _source(self) -> str:
        import src.security.crypto as mod

        return inspect.getsource(mod)

    def test_sem_signing_key(self):
        self.assertNotIn(
            "_signing_key",
            self._source(),
            "Referência a _signing_key (atributo privado do Fernet) encontrada — deve ser removida.",
        )

    def test_sem_encryption_key(self):
        self.assertNotIn(
            "_encryption_key",
            self._source(),
            "Referência a _encryption_key (atributo privado do Fernet) encontrada — deve ser removida.",
        )

    def test_sem_gc_collect(self):
        self.assertNotIn(
            "gc.collect",
            self._source(),
            "gc.collect() não garante wipe de memória — deve ser removido.",
        )

    def test_sem_import_gc(self):
        """import gc não deve aparecer; foi usado apenas por gc.collect()."""
        source = self._source()
        # Aceita comentários com "gc" mas não import direto
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            self.assertNotRegex(
                stripped,
                r"^import\s+gc\b",
                "import gc não deve estar presente no módulo.",
            )


# ---------------------------------------------------------------------------
# B) Encrypt/Decrypt continuam funcionando
# ---------------------------------------------------------------------------


class TestEncryptDecrypt(_CryptoBase):
    def test_encrypt_retorna_string_nao_vazia(self):
        from src.security.crypto import encrypt_text

        result = encrypt_text("senha_secreta")
        self.assertIsInstance(result, str)
        self.assertTrue(result)

    def test_decrypt_recupera_original(self):
        from src.security.crypto import encrypt_text, decrypt_text

        original = "minha senha 123!@#"
        token = encrypt_text(original)
        self.assertEqual(decrypt_text(token), original)

    def test_encrypt_none_retorna_vazio(self):
        from src.security.crypto import encrypt_text

        self.assertEqual(encrypt_text(None), "")

    def test_encrypt_vazio_retorna_vazio(self):
        from src.security.crypto import encrypt_text

        self.assertEqual(encrypt_text(""), "")

    def test_decrypt_token_invalido_retorna_vazio(self):
        from src.security.crypto import decrypt_text

        self.assertEqual(decrypt_text("token-invalido-xpto"), "")

    def test_decrypt_none_retorna_vazio(self):
        from src.security.crypto import decrypt_text

        self.assertEqual(decrypt_text(None), "")

    def test_decrypt_vazio_retorna_vazio(self):
        from src.security.crypto import decrypt_text

        self.assertEqual(decrypt_text(""), "")

    def test_tokens_diferentes_para_mesmo_plaintext(self):
        """Fernet usa IV aleatório; dois tokens para o mesmo plain são distintos."""
        from src.security.crypto import encrypt_text

        t1 = encrypt_text("abc")
        t2 = encrypt_text("abc")
        self.assertNotEqual(t1, t2)

    def test_encrypt_preserva_unicode(self):
        from src.security.crypto import encrypt_text, decrypt_text

        original = "café ñoño 日本語"
        self.assertEqual(decrypt_text(encrypt_text(original)), original)


# ---------------------------------------------------------------------------
# C) _reset_fernet_cache idempotente
# ---------------------------------------------------------------------------


class TestResetFernetCache(_CryptoBase):
    def test_reset_quando_cache_none_nao_quebra(self):
        import src.security.crypto as mod

        mod._fernet_instance = None
        mod._reset_fernet_cache()  # Não deve lançar
        self.assertIsNone(mod._fernet_instance)

    def test_reset_quando_cache_preenchido(self):
        import src.security.crypto as mod

        mod._get_fernet()  # popula o cache
        self.assertIsNotNone(mod._fernet_instance)
        mod._reset_fernet_cache()
        self.assertIsNone(mod._fernet_instance)

    def test_reset_multiplas_vezes_idempotente(self):
        import src.security.crypto as mod

        for _ in range(5):
            mod._reset_fernet_cache()
        self.assertIsNone(mod._fernet_instance)

    def test_encrypt_funciona_apos_reset(self):
        import src.security.crypto as mod
        from src.security.crypto import encrypt_text, decrypt_text

        mod._reset_fernet_cache()
        # Deve recriar cache automaticamente
        self.assertEqual(decrypt_text(encrypt_text("pós-reset")), "pós-reset")


# ---------------------------------------------------------------------------
# D) _secure_delete honesta — sem acessos a internals
# ---------------------------------------------------------------------------


class TestSecureDelete(unittest.TestCase):
    def test_nao_levanta_com_bytes_normais(self):
        from src.security.crypto import _secure_delete

        _secure_delete(b"dados sensiveis")  # Não deve lançar

    def test_nao_levanta_com_bytes_vazios(self):
        from src.security.crypto import _secure_delete

        _secure_delete(b"")  # Não deve lançar

    def test_funcao_existe_e_callable(self):
        from src.security.crypto import _secure_delete

        self.assertTrue(callable(_secure_delete))

    def test_secure_delete_nao_usa_privados_fernet(self):
        """_secure_delete não deve acessar _signing_key nem _encryption_key."""
        from src.security.crypto import _secure_delete

        source = inspect.getsource(_secure_delete)
        self.assertNotIn("_signing_key", source)
        self.assertNotIn("_encryption_key", source)
        self.assertNotIn("gc.collect", source)


if __name__ == "__main__":
    unittest.main()
