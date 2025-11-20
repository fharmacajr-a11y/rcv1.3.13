# -*- coding: utf-8 -*-
"""
Testes para funções de autenticação e validação.

Foco em funções puras e lógica de validação/rate limiting.
Cobre: src/core/auth/auth.py (validate_credentials, check_rate_limit, pbkdf2_hash)
"""

import binascii
import time
from unittest.mock import patch

import pytest

from src.core.auth.auth import (
    EMAIL_RE,
    check_rate_limit,
    pbkdf2_hash,
    validate_credentials,
)


# ====================================================================
# Validação de credenciais
# ====================================================================


def test_validate_credentials_valid():
    """validate_credentials deve retornar None para email e senha válidos."""
    result = validate_credentials("user@example.com", "senha123")
    assert result is None


def test_validate_credentials_invalid_email_empty():
    """validate_credentials deve rejeitar email vazio."""
    result = validate_credentials("", "senha123")
    assert result == "Informe um e-mail válido."


def test_validate_credentials_invalid_email_no_at():
    """validate_credentials deve rejeitar email sem @."""
    result = validate_credentials("invalidemail.com", "senha123")
    assert result == "Informe um e-mail válido."


def test_validate_credentials_invalid_email_no_domain():
    """validate_credentials deve rejeitar email sem domínio."""
    result = validate_credentials("user@", "senha123")
    assert result == "Informe um e-mail válido."


def test_validate_credentials_invalid_email_with_spaces():
    """validate_credentials deve rejeitar email com espaços."""
    result = validate_credentials("user @example.com", "senha123")
    assert result == "Informe um e-mail válido."


def test_validate_credentials_password_too_short():
    """validate_credentials deve rejeitar senha com menos de 6 caracteres."""
    result = validate_credentials("user@example.com", "12345")
    assert result == "A senha deve ter ao menos 6 caracteres."


def test_validate_credentials_password_empty():
    """validate_credentials deve rejeitar senha vazia."""
    result = validate_credentials("user@example.com", "")
    assert result == "A senha deve ter ao menos 6 caracteres."


def test_validate_credentials_password_none():
    """validate_credentials deve rejeitar senha None."""
    result = validate_credentials("user@example.com", None)  # type: ignore
    assert result == "A senha deve ter ao menos 6 caracteres."


def test_validate_credentials_password_exactly_6_chars():
    """validate_credentials deve aceitar senha com exatamente 6 caracteres."""
    result = validate_credentials("user@example.com", "123456")
    assert result is None


def test_validate_credentials_email_none():
    """validate_credentials deve rejeitar email None."""
    result = validate_credentials(None, "senha123")  # type: ignore
    assert result == "Informe um e-mail válido."


# ====================================================================
# Regex de email
# ====================================================================


def test_email_regex_valid():
    """EMAIL_RE deve validar emails corretos."""
    assert EMAIL_RE.match("user@example.com")
    assert EMAIL_RE.match("test.user@domain.co.uk")
    assert EMAIL_RE.match("name+tag@company.org")


def test_email_regex_invalid():
    """EMAIL_RE deve rejeitar emails inválidos."""
    assert not EMAIL_RE.match("")
    assert not EMAIL_RE.match("invalid")
    assert not EMAIL_RE.match("@example.com")
    assert not EMAIL_RE.match("user@")
    assert not EMAIL_RE.match("user @example.com")
    assert not EMAIL_RE.match("user@domain")  # Sem TLD


# ====================================================================
# Rate limiting
# ====================================================================


def test_check_rate_limit_first_attempt(monkeypatch):
    """check_rate_limit deve permitir primeira tentativa."""
    # Limpar histórico
    monkeypatch.setattr("src.core.auth.auth.login_attempts", {})

    allowed, remaining = check_rate_limit("user@test.com")

    assert allowed is True
    assert remaining == 0.0


def test_check_rate_limit_under_threshold(monkeypatch):
    """check_rate_limit deve permitir até 4 tentativas."""
    attempts = {}
    monkeypatch.setattr("src.core.auth.auth.login_attempts", attempts)

    now = time.time()
    # Simular 4 tentativas
    attempts["user@test.com"] = (4, now)

    allowed, remaining = check_rate_limit("user@test.com")

    assert allowed is True
    assert remaining == 0.0


def test_check_rate_limit_exceed_threshold(monkeypatch):
    """check_rate_limit deve bloquear após 5 tentativas."""
    attempts = {}
    monkeypatch.setattr("src.core.auth.auth.login_attempts", attempts)

    now = time.time()
    # Simular 5 tentativas
    attempts["user@test.com"] = (5, now)

    allowed, remaining = check_rate_limit("user@test.com")

    assert allowed is False
    assert remaining > 0  # Deve ter tempo restante (até 60s)
    assert remaining <= 60


def test_check_rate_limit_reset_after_60_seconds(monkeypatch):
    """check_rate_limit deve resetar após 60 segundos."""
    attempts = {}
    monkeypatch.setattr("src.core.auth.auth.login_attempts", attempts)

    # Simular tentativas antigas (> 60s atrás)
    old_time = time.time() - 61
    attempts["user@test.com"] = (5, old_time)

    allowed, remaining = check_rate_limit("user@test.com")

    assert allowed is True
    assert remaining == 0.0
    # Deve ter limpado do histórico
    assert "user@test.com" not in attempts


def test_check_rate_limit_case_insensitive(monkeypatch):
    """check_rate_limit deve ser case-insensitive."""
    attempts = {}
    monkeypatch.setattr("src.core.auth.auth.login_attempts", attempts)

    now = time.time()
    attempts["user@test.com"] = (5, now)

    # Testar com maiúsculas
    allowed, remaining = check_rate_limit("USER@TEST.COM")

    assert allowed is False  # Deve reconhecer mesmo email


def test_check_rate_limit_strips_whitespace(monkeypatch):
    """check_rate_limit deve ignorar espaços em branco."""
    attempts = {}
    monkeypatch.setattr("src.core.auth.auth.login_attempts", attempts)

    now = time.time()
    attempts["user@test.com"] = (5, now)

    # Testar com espaços
    allowed, remaining = check_rate_limit("  user@test.com  ")

    assert allowed is False  # Deve reconhecer mesmo email


# ====================================================================
# pbkdf2_hash
# ====================================================================


def test_pbkdf2_hash_basic():
    """pbkdf2_hash deve gerar hash no formato correto."""
    password = "senha_teste"
    result = pbkdf2_hash(password)

    # Formato: pbkdf2_sha256$<iter>$<hex_salt>$<hex_hash>
    parts = result.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert parts[1].isdigit()  # iterations
    assert len(parts[2]) > 0  # salt hex
    assert len(parts[3]) > 0  # hash hex


def test_pbkdf2_hash_default_iterations():
    """pbkdf2_hash deve usar 1_000_000 iterações por padrão."""
    result = pbkdf2_hash("password")
    parts = result.split("$")
    assert parts[1] == "1000000"


def test_pbkdf2_hash_custom_iterations():
    """pbkdf2_hash deve aceitar iterações customizadas."""
    result = pbkdf2_hash("password", iterations=50000)
    parts = result.split("$")
    assert parts[1] == "50000"


def test_pbkdf2_hash_deterministic_with_same_salt():
    """pbkdf2_hash deve ser determinístico com mesmo salt."""
    password = "senha_teste"
    salt = b"fixed_salt_16byt"  # 16 bytes

    hash1 = pbkdf2_hash(password, salt=salt)
    hash2 = pbkdf2_hash(password, salt=salt)

    assert hash1 == hash2


def test_pbkdf2_hash_different_with_different_salt():
    """pbkdf2_hash deve gerar hashes diferentes com salts diferentes."""
    password = "senha_teste"

    # Gerar dois hashes sem salt fixo (random salt)
    hash1 = pbkdf2_hash(password)
    hash2 = pbkdf2_hash(password)

    # Devem ser diferentes devido a salts diferentes
    assert hash1 != hash2


def test_pbkdf2_hash_salt_hex_valid():
    """pbkdf2_hash deve gerar salt em hexadecimal válido."""
    result = pbkdf2_hash("password")
    parts = result.split("$")
    salt_hex = parts[2]

    # Deve ser hexadecimal válido
    try:
        binascii.unhexlify(salt_hex)
    except Exception:
        pytest.fail("Salt não é hexadecimal válido")


def test_pbkdf2_hash_hash_hex_valid():
    """pbkdf2_hash deve gerar hash em hexadecimal válido."""
    result = pbkdf2_hash("password")
    parts = result.split("$")
    hash_hex = parts[3]

    # Deve ser hexadecimal válido
    try:
        binascii.unhexlify(hash_hex)
    except Exception:
        pytest.fail("Hash não é hexadecimal válido")


def test_pbkdf2_hash_custom_dklen():
    """pbkdf2_hash deve aceitar tamanho customizado de hash."""
    result = pbkdf2_hash("password", dklen=64)
    parts = result.split("$")
    hash_hex = parts[3]

    # Hash deve ter 64 bytes = 128 caracteres hex
    assert len(hash_hex) == 128


def test_pbkdf2_hash_empty_password_raises():
    """pbkdf2_hash deve lançar ValueError para senha vazia."""
    with pytest.raises(ValueError, match="password vazio"):
        pbkdf2_hash("")


def test_pbkdf2_hash_different_passwords_different_hashes():
    """pbkdf2_hash deve gerar hashes diferentes para senhas diferentes."""
    salt = b"same_salt_16byte"
    hash1 = pbkdf2_hash("password1", salt=salt)
    hash2 = pbkdf2_hash("password2", salt=salt)

    assert hash1 != hash2


@patch("src.core.auth.auth._get_auth_pepper")
def test_pbkdf2_hash_uses_pepper(mock_pepper):
    """pbkdf2_hash deve incluir pepper no hash."""
    mock_pepper.return_value = "test_pepper"
    salt = b"fixed_salt_16byt"

    hash_with_pepper = pbkdf2_hash("password", salt=salt)

    # Alterar pepper deve gerar hash diferente
    mock_pepper.return_value = "different_pepper"
    hash_different_pepper = pbkdf2_hash("password", salt=salt)

    assert hash_with_pepper != hash_different_pepper
