# -*- coding: utf-8 -*-
"""
TEST-001: Testes de edge cases para security/crypto.py

Garante que a criptografia Fernet lida corretamente com:
- Strings vazias
- Valores None
- Tokens inválidos
- Unicode/emoji
"""

import pytest

from security.crypto import encrypt_text, decrypt_text, _reset_fernet_cache


@pytest.fixture(autouse=True)
def reset_crypto_cache():
    """Reset do cache Fernet entre testes."""
    _reset_fernet_cache()
    yield
    _reset_fernet_cache()


def test_encrypt_empty_string():
    """TEST-001: Deve retornar string vazia para input vazio."""
    result = encrypt_text("")
    assert result == ""


def test_encrypt_none():
    """TEST-001: Deve retornar string vazia para None."""
    result = encrypt_text(None)
    assert result == ""


def test_decrypt_empty_string():
    """TEST-001: Deve retornar string vazia para token vazio."""
    result = decrypt_text("")
    assert result == ""


def test_decrypt_none():
    """TEST-001: Deve retornar string vazia para None."""
    result = decrypt_text(None)
    assert result == ""


def test_decrypt_invalid_token():
    """TEST-001: Deve retornar string vazia para token inválido."""
    result = decrypt_text("invalid_base64_token")
    assert result == ""


def test_decrypt_malformed_token():
    """TEST-001: Deve retornar string vazia para token malformado."""
    result = decrypt_text("Z0FBQUFBQmtSWFdBdHI4TUxQYmRCYlhIX2d5MQ==")
    assert result == ""


def test_encrypt_unicode():
    """TEST-001: Deve criptografar e descriptografar unicode corretamente."""
    original = "Olá Mundo! 🔐 Testing Unicode: Ñoño"
    encrypted = encrypt_text(original)

    assert encrypted != ""
    assert encrypted != original

    decrypted = decrypt_text(encrypted)
    assert decrypted == original


def test_encrypt_special_chars():
    """TEST-001: Deve criptografar caracteres especiais."""
    original = "!@#$%^&*()_+-=[]{}|;':\",./<>?\n\t"
    encrypted = encrypt_text(original)

    assert encrypted != ""
    decrypted = decrypt_text(encrypted)
    assert decrypted == original


def test_encrypt_long_text():
    """TEST-001: Deve criptografar textos longos."""
    original = "A" * 10000
    encrypted = encrypt_text(original)

    assert encrypted != ""
    decrypted = decrypt_text(encrypted)
    assert decrypted == original


def test_encrypt_decrypt_cycle():
    """TEST-001: Deve manter integridade após múltiplos ciclos."""
    original = "senha_secreta_123"

    # Ciclo 1
    enc1 = encrypt_text(original)
    dec1 = decrypt_text(enc1)
    assert dec1 == original

    # Ciclo 2
    enc2 = encrypt_text(dec1)
    dec2 = decrypt_text(enc2)
    assert dec2 == original

    # Tokens devem ser diferentes (Fernet usa timestamp)
    assert enc1 != enc2


def test_encrypt_whitespace():
    """TEST-001: Deve preservar espaços em branco."""
    original = "   espaços   "
    encrypted = encrypt_text(original)
    decrypted = decrypt_text(encrypted)
    assert decrypted == original


def test_encrypt_newlines():
    """TEST-001: Deve preservar quebras de linha."""
    original = "linha1\nlinha2\r\nlinha3"
    encrypted = encrypt_text(original)
    decrypted = decrypt_text(encrypted)
    assert decrypted == original
