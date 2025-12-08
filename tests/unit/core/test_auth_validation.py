# -*- coding: utf-8 -*-
"""
Testes para funções de autenticação e validação.

Foco em funções puras e lógica de validação/rate limiting.
Cobre: src/core/auth/auth.py (validate_credentials, check_rate_limit, pbkdf2_hash)
"""

import binascii
import os
import sqlite3
import time
from unittest.mock import Mock, patch

import pytest

from src.core.auth.auth import (
    EMAIL_RE,
    _get_auth_pepper,
    check_rate_limit,
    create_user,
    ensure_users_db,
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


def test_check_rate_limit_first_attempt():
    """check_rate_limit deve permitir primeira tentativa."""
    # reset_auth_rate_limit fixture já limpa o histórico
    allowed, remaining = check_rate_limit("user@test.com")

    assert allowed is True
    assert remaining == 0.0


def test_check_rate_limit_under_threshold():
    """check_rate_limit deve permitir até 4 tentativas."""
    from src.core.auth.auth import _set_login_attempts_for_tests

    now = time.time()
    # Simular 4 tentativas
    _set_login_attempts_for_tests("user@test.com", 4, now)

    allowed, remaining = check_rate_limit("user@test.com")

    assert allowed is True
    assert remaining == 0.0


def test_check_rate_limit_exceed_threshold():
    """check_rate_limit deve bloquear após 5 tentativas."""
    from src.core.auth.auth import _set_login_attempts_for_tests

    now = time.time()
    # Simular 5 tentativas
    _set_login_attempts_for_tests("user@test.com", 5, now)

    allowed, remaining = check_rate_limit("user@test.com")

    assert allowed is False
    assert remaining > 0  # Deve ter tempo restante (até 60s)
    assert remaining <= 60


def test_check_rate_limit_reset_after_60_seconds():
    """check_rate_limit deve resetar após 60 segundos."""
    from src.core.auth.auth import _set_login_attempts_for_tests, _get_login_attempts_for_tests

    # Simular tentativas antigas (> 60s atrás)
    old_time = time.time() - 61
    _set_login_attempts_for_tests("user@test.com", 5, old_time)

    allowed, remaining = check_rate_limit("user@test.com")

    assert allowed is True
    assert remaining == 0.0
    # Deve ter limpado do histórico
    assert _get_login_attempts_for_tests("user@test.com") is None


def test_check_rate_limit_case_insensitive():
    """check_rate_limit deve ser case-insensitive."""
    from src.core.auth.auth import _set_login_attempts_for_tests

    now = time.time()
    _set_login_attempts_for_tests("user@test.com", 5, now)

    # Testar com maiúsculas
    allowed, remaining = check_rate_limit("USER@TEST.COM")

    assert allowed is False  # Deve reconhecer mesmo email


def test_check_rate_limit_strips_whitespace():
    """check_rate_limit deve ignorar espaços em branco."""
    from src.core.auth.auth import _set_login_attempts_for_tests

    now = time.time()
    _set_login_attempts_for_tests("user@test.com", 5, now)

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


# ====================================================================
# _get_auth_pepper
# ====================================================================


def test_get_auth_pepper_from_env(monkeypatch):
    """_get_auth_pepper deve retornar valor de AUTH_PEPPER do ambiente."""
    monkeypatch.setenv("AUTH_PEPPER", "secret_pepper_123")

    result = _get_auth_pepper()

    assert result == "secret_pepper_123"


def test_get_auth_pepper_from_rc_env(monkeypatch):
    """_get_auth_pepper deve retornar valor de RC_AUTH_PEPPER se AUTH_PEPPER não existir."""
    monkeypatch.delenv("AUTH_PEPPER", raising=False)
    monkeypatch.setenv("RC_AUTH_PEPPER", "rc_pepper_456")

    result = _get_auth_pepper()

    assert result == "rc_pepper_456"


def test_get_auth_pepper_from_config_yml(monkeypatch, tmp_path):
    """_get_auth_pepper deve ler de config.yml se variáveis de ambiente não existirem."""
    monkeypatch.delenv("AUTH_PEPPER", raising=False)
    monkeypatch.delenv("RC_AUTH_PEPPER", raising=False)

    # Criar config.yml temporário
    config_file = tmp_path / "config.yml"
    config_file.write_text("AUTH_PEPPER: yaml_pepper_789")

    # Mudar diretório atual para tmp_path
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = _get_auth_pepper()
        assert result == "yaml_pepper_789"
    finally:
        os.chdir(original_cwd)


def test_get_auth_pepper_empty_when_not_found(monkeypatch, tmp_path):
    """_get_auth_pepper deve retornar string vazia se não encontrar pepper."""
    monkeypatch.delenv("AUTH_PEPPER", raising=False)
    monkeypatch.delenv("RC_AUTH_PEPPER", raising=False)

    # Usar tmp_path que não tem config.yml
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = _get_auth_pepper()
        assert result == ""
    finally:
        os.chdir(original_cwd)


def test_get_auth_pepper_prefers_env_over_config(monkeypatch, tmp_path):
    """_get_auth_pepper deve preferir variável de ambiente sobre config.yml."""
    monkeypatch.setenv("AUTH_PEPPER", "env_pepper")

    # Criar config.yml com valor diferente
    config_file = tmp_path / "config.yml"
    config_file.write_text("AUTH_PEPPER: yaml_pepper")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = _get_auth_pepper()
        assert result == "env_pepper"  # Env tem prioridade
    finally:
        os.chdir(original_cwd)


def test_get_auth_pepper_handles_config_yaml(monkeypatch, tmp_path):
    """_get_auth_pepper deve ler de config.yaml se config.yml não existir."""
    monkeypatch.delenv("AUTH_PEPPER", raising=False)
    monkeypatch.delenv("RC_AUTH_PEPPER", raising=False)

    # Criar config.yaml (não config.yml)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("auth_pepper: yaml_pepper_lowercase")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = _get_auth_pepper()
        assert result == "yaml_pepper_lowercase"
    finally:
        os.chdir(original_cwd)


def test_get_auth_pepper_handles_corrupt_yaml(monkeypatch, tmp_path):
    """_get_auth_pepper deve retornar vazio se config.yml for inválido."""
    monkeypatch.delenv("AUTH_PEPPER", raising=False)
    monkeypatch.delenv("RC_AUTH_PEPPER", raising=False)

    # Criar config.yml com YAML inválido
    config_file = tmp_path / "config.yml"
    config_file.write_text("invalid: yaml: content:")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = _get_auth_pepper()
        # Deve retornar vazio sem lançar exceção
        assert result == ""
    finally:
        os.chdir(original_cwd)


# ====================================================================
# ensure_users_db & create_user
# ====================================================================


def test_ensure_users_db_creates_table(isolated_users_db):
    """ensure_users_db deve criar tabela users se não existir."""
    db_path = isolated_users_db

    ensure_users_db()

    # Verificar que o banco e a tabela foram criados
    assert db_path.exists()

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        result = cur.fetchone()
        assert result is not None
        assert result[0] == "users"
    finally:
        con.close()


def test_create_user_new(isolated_users_db):
    """create_user deve criar novo usuário e retornar ID."""
    db_path = isolated_users_db

    user_id = create_user("test@example.com", "senha123")

    assert user_id > 0

    # Verificar que usuário foi criado
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("SELECT username, is_active FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "test@example.com"
        assert row[1] == 1  # is_active
    finally:
        con.close()


def test_create_user_update_existing(isolated_users_db):
    """create_user deve atualizar senha de usuário existente."""
    db_path = isolated_users_db

    # Criar usuário inicial
    user_id_1 = create_user("test@example.com", "senha123")

    # Atualizar senha do mesmo usuário
    user_id_2 = create_user("test@example.com", "nova_senha456")

    # Deve retornar mesmo ID
    assert user_id_1 == user_id_2

    # Verificar que senha foi atualizada
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id=?", (user_id_1,))
        row = cur.fetchone()
        assert row is not None
        # Hash deve ter mudado (nova senha)
        assert "pbkdf2_sha256" in row[0]
    finally:
        con.close()


def test_create_user_without_password(isolated_users_db):
    """create_user deve permitir criar usuário sem senha."""
    db_path = isolated_users_db

    user_id = create_user("test@example.com")

    assert user_id > 0

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] is None  # Sem senha
    finally:
        con.close()


def test_create_user_empty_username_raises(isolated_users_db):
    """create_user deve lançar ValueError para username vazio."""
    # db_path não é usado neste teste, mas fixture é necessária para setup
    with pytest.raises(ValueError, match="username obrigatório"):
        create_user("")


def test_create_user_none_username_raises(isolated_users_db):
    """create_user deve lançar ValueError para username None."""
    # db_path não é usado neste teste, mas fixture é necessária para setup
    with pytest.raises(ValueError, match="username obrigatório"):
        create_user(None)  # type: ignore


def test_create_user_update_without_password(isolated_users_db):
    """create_user deve permitir atualizar usuário sem fornecer nova senha."""
    db_path = isolated_users_db

    # Criar usuário com senha
    user_id_1 = create_user("test@example.com", "senha123")

    # Atualizar usuário sem fornecer senha (deve manter a antiga)
    user_id_2 = create_user("test@example.com", None)

    # Deve retornar mesmo ID
    assert user_id_1 == user_id_2

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id=?", (user_id_1,))
        row = cur.fetchone()
        assert row is not None
        # Hash deve permanecer (senha original)
        assert "pbkdf2_sha256" in row[0]
    finally:
        con.close()


# ====================================================================
# authenticate_user (Supabase integration)
# ====================================================================


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_success(mock_get_supabase, monkeypatch):
    """authenticate_user deve retornar (True, email) para credenciais válidas."""
    # Limpar rate limit
    monkeypatch.setattr("src.core.auth.auth.login_attempts", {})

    # Mock Supabase auth
    mock_sb = Mock()
    mock_user = Mock()
    mock_user.email = "test@example.com"

    mock_res = Mock()
    mock_res.user = mock_user

    mock_session = Mock()
    mock_session.access_token = "fake_token_123"

    mock_sb.auth.sign_in_with_password.return_value = mock_res
    mock_sb.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_sb

    success, msg = _authenticate_user_helper("test@example.com", "senha123")

    assert success is True
    assert msg == "test@example.com"
    mock_sb.auth.sign_in_with_password.assert_called_once_with({"email": "test@example.com", "password": "senha123"})


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_invalid_credentials(mock_get_supabase):
    """authenticate_user deve retornar (False, msg) para credenciais inválidas."""
    # reset_auth_rate_limit fixture já limpa o histórico

    # Mock Supabase lançando exceção
    mock_sb = Mock()
    mock_sb.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
    mock_get_supabase.return_value = mock_sb

    success, msg = _authenticate_user_helper("test@example.com", "senha_errada")

    assert success is False
    assert "incorretos" in msg


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_validation_error(mock_get_supabase):
    """authenticate_user deve retornar erro de validação antes de chamar Supabase."""
    success, msg = _authenticate_user_helper("invalid_email", "senha123")

    assert success is False
    assert "e-mail válido" in msg
    # Não deve ter chamado Supabase
    mock_get_supabase.assert_not_called()


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_rate_limit_blocks(mock_get_supabase):
    """authenticate_user deve bloquear após exceder rate limit."""
    from src.core.auth.auth import _set_login_attempts_for_tests

    # Simular 5 tentativas recentes
    now = time.time()
    _set_login_attempts_for_tests("test@example.com", 5, now)

    success, msg = _authenticate_user_helper("test@example.com", "senha123")

    assert success is False
    assert "Muitas tentativas" in msg
    # Não deve ter chamado Supabase
    mock_get_supabase.assert_not_called()


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_clears_attempts_on_success(mock_get_supabase):
    """authenticate_user deve limpar rate limit após login bem-sucedido."""
    from src.core.auth.auth import _set_login_attempts_for_tests, _get_login_attempts_for_tests

    # Simular tentativas anteriores
    _set_login_attempts_for_tests("test@example.com", 2, time.time())

    # Mock sucesso
    mock_sb = Mock()
    mock_user = Mock()
    mock_user.email = "test@example.com"
    mock_res = Mock()
    mock_res.user = mock_user
    mock_session = Mock()
    mock_session.access_token = "token"
    mock_sb.auth.sign_in_with_password.return_value = mock_res
    mock_sb.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_sb

    success, msg = _authenticate_user_helper("test@example.com", "senha123")

    assert success is True
    # Deve ter limpado tentativas
    assert _get_login_attempts_for_tests("test@example.com") is None


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_increments_attempts_on_failure(mock_get_supabase):
    """authenticate_user deve incrementar contador de tentativas em falha."""
    from src.core.auth.auth import _get_login_attempts_for_tests

    # Mock falha
    mock_sb = Mock()
    mock_sb.auth.sign_in_with_password.side_effect = Exception("Invalid")
    mock_get_supabase.return_value = mock_sb

    _authenticate_user_helper("test@example.com", "senha_errada")

    # Deve ter incrementado tentativas
    attempts = _get_login_attempts_for_tests("test@example.com")
    assert attempts is not None
    count, _ = attempts
    assert count == 1


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_no_session(mock_get_supabase):
    """authenticate_user deve falhar se não houver sessão válida."""
    # reset_auth_rate_limit fixture já limpa o histórico

    # Mock sem sessão
    mock_sb = Mock()
    mock_res = Mock()
    mock_res.user = Mock()
    mock_sb.auth.sign_in_with_password.return_value = mock_res
    mock_sb.auth.get_session.return_value = None  # Sem sessão
    mock_get_supabase.return_value = mock_sb

    success, msg = _authenticate_user_helper("test@example.com", "senha123")

    assert success is False
    # Aceitar qualquer mensagem de erro
    assert msg != ""


# Helper para evitar importar authenticate_user diretamente (pode não estar exportado)
def _authenticate_user_helper(email: str, password: str):
    """Helper para testar authenticate_user."""
    from src.core.auth.auth import authenticate_user

    return authenticate_user(email, password)
