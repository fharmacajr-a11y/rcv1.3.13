# -*- coding: utf-8 -*-
"""
TEST-001: Cobertura de src/core/auth/auth.py

Testes focados em lógica core de autenticação:
- pbkdf2_hash: formato, consistência, diferentes salts
- validate_credentials: email/senha inválidos
- create_user/ensure_users_db: CRUD de usuários locais
- authenticate_user: sucesso/falha via mock Supabase
- check_rate_limit: bloqueio após 5 tentativas
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.auth import auth


@pytest.fixture(autouse=True)
def reset_auth_state():
    """Limpa estado global de rate limiting antes de cada teste."""
    auth._reset_auth_for_tests()
    yield
    auth._reset_auth_for_tests()


@pytest.fixture
def temp_users_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Cria DB temporário de usuários para testes."""
    db_path = tmp_path / "users.db"
    monkeypatch.setattr("src.core.auth.auth.USERS_DB_PATH", db_path)
    return db_path


@pytest.fixture
def mock_supabase():
    """Mock do cliente Supabase para testes de authenticate_user."""
    mock_client = MagicMock()
    mock_client.auth = MagicMock()
    return mock_client


# ============================================================================
# 1) pbkdf2_hash
# ============================================================================


def test_pbkdf2_hash_formato(monkeypatch: pytest.MonkeyPatch):
    """Hash deve ter formato pbkdf2_sha256$iter$hex_salt$hex_hash."""
    monkeypatch.setenv("RC_PBKDF2_ITERS", "10")  # Rápido para testes

    result = auth.pbkdf2_hash("senha123")

    parts = result.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert parts[1] == "10"  # iterações
    assert len(parts[2]) == 32  # 16 bytes = 32 hex chars (salt)
    assert len(parts[3]) == 64  # 32 bytes = 64 hex chars (hash)


def test_pbkdf2_hash_diferentes_salts_geram_hashes_diferentes(monkeypatch: pytest.MonkeyPatch):
    """Mesma senha com salts diferentes deve gerar hashes diferentes."""
    monkeypatch.setenv("RC_PBKDF2_ITERS", "10")

    hash1 = auth.pbkdf2_hash("senha123")
    hash2 = auth.pbkdf2_hash("senha123")

    # Salts devem ser diferentes (random)
    salt1 = hash1.split("$")[2]
    salt2 = hash2.split("$")[2]
    assert salt1 != salt2

    # Hashes devem ser diferentes
    assert hash1 != hash2


def test_pbkdf2_hash_mesmo_salt_gera_mesmo_hash(monkeypatch: pytest.MonkeyPatch):
    """Mesma senha e mesmo salt devem gerar mesmo hash."""
    monkeypatch.setenv("RC_PBKDF2_ITERS", "10")

    salt = b"1234567890123456"  # 16 bytes fixos
    hash1 = auth.pbkdf2_hash("senha123", salt=salt)
    hash2 = auth.pbkdf2_hash("senha123", salt=salt)

    assert hash1 == hash2


def test_pbkdf2_hash_senha_vazia_levanta_erro():
    """Senha vazia deve levantar ValueError."""
    with pytest.raises(ValueError, match="password vazio"):
        auth.pbkdf2_hash("")


# ============================================================================
# 2) validate_credentials
# ============================================================================


def test_validate_credentials_email_invalido():
    """Email inválido deve retornar mensagem de erro."""
    result = auth.validate_credentials("invalido", "senha123")
    assert result == "Informe um e-mail válido."


def test_validate_credentials_senha_curta():
    """Senha < 6 caracteres deve retornar mensagem de erro."""
    result = auth.validate_credentials("user@example.com", "12345")
    assert result == "A senha deve ter ao menos 6 caracteres."


def test_validate_credentials_senha_vazia():
    """Senha vazia deve retornar mensagem de erro."""
    result = auth.validate_credentials("user@example.com", "")
    assert result == "A senha deve ter ao menos 6 caracteres."


def test_validate_credentials_validos():
    """Email e senha válidos devem retornar None."""
    result = auth.validate_credentials("user@example.com", "senha123")
    assert result is None


# ============================================================================
# 3) create_user / ensure_users_db
# ============================================================================


def test_ensure_users_db_cria_tabela(temp_users_db: Path):
    """ensure_users_db deve criar tabela users."""
    auth.ensure_users_db()

    con = sqlite3.connect(str(temp_users_db))
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    result = cur.fetchone()
    con.close()

    assert result is not None
    assert result[0] == "users"


def test_create_user_cria_novo_usuario(temp_users_db: Path, monkeypatch: pytest.MonkeyPatch):
    """create_user deve criar novo usuário e retornar ID."""
    monkeypatch.setenv("RC_PBKDF2_ITERS", "10")

    user_id = auth.create_user("testuser", "senha123")

    assert user_id > 0

    # Verificar no banco
    con = sqlite3.connect(str(temp_users_db))
    cur = con.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    con.close()

    assert row is not None
    assert row[1] == "testuser"
    assert row[2] is not None  # Hash de senha
    assert row[2].startswith("pbkdf2_sha256$")


def test_create_user_duplicado_atualiza_senha(temp_users_db: Path, monkeypatch: pytest.MonkeyPatch):
    """create_user com username existente deve atualizar senha."""
    monkeypatch.setenv("RC_PBKDF2_ITERS", "10")

    # Criar usuário
    user_id = auth.create_user("testuser", "senha123")

    # Obter hash original
    con = sqlite3.connect(str(temp_users_db))
    cur = con.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id=?", (user_id,))
    hash_original = cur.fetchone()[0]
    con.close()

    # Atualizar senha
    user_id2 = auth.create_user("testuser", "novasenha")

    # Mesmo ID
    assert user_id2 == user_id

    # Hash mudou
    con = sqlite3.connect(str(temp_users_db))
    cur = con.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id=?", (user_id,))
    hash_novo = cur.fetchone()[0]
    con.close()

    assert hash_novo != hash_original


def test_create_user_username_vazio_levanta_erro(temp_users_db: Path):
    """Username vazio deve levantar ValueError."""
    with pytest.raises(ValueError, match="username obrigatório"):
        auth.create_user("", "senha123")


# ============================================================================
# 4) authenticate_user
# ============================================================================


def test_authenticate_user_sucesso(mock_supabase: MagicMock):
    """Login válido deve retornar (True, email)."""
    # Mock user e session
    mock_user = MagicMock()
    mock_user.email = "user@example.com"

    mock_session = MagicMock()
    mock_session.access_token = "fake_token"

    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(user=mock_user)
    mock_supabase.auth.get_session.return_value = mock_session

    with patch("src.core.auth.auth.get_supabase", return_value=mock_supabase):
        ok, msg = auth.authenticate_user("user@example.com", "senha123")

    assert ok is True
    assert msg == "user@example.com"


def test_authenticate_user_credenciais_invalidas(mock_supabase: MagicMock):
    """Credenciais inválidas devem retornar (False, mensagem)."""
    mock_supabase.auth.sign_in_with_password.side_effect = Exception("invalid credentials")

    with patch("src.core.auth.auth.get_supabase", return_value=mock_supabase):
        ok, msg = auth.authenticate_user("user@example.com", "senhaerrada")

    assert ok is False
    assert "E-mail ou senha incorretos" in msg


def test_authenticate_user_email_invalido(mock_supabase: MagicMock):
    """Email inválido deve retornar (False, mensagem) sem chamar Supabase."""
    ok, msg = auth.authenticate_user("invalido", "senha123")

    assert ok is False
    assert msg == "Informe um e-mail válido."

    # Não deve ter chamado Supabase
    mock_supabase.auth.sign_in_with_password.assert_not_called()


def test_authenticate_user_senha_curta(mock_supabase: MagicMock):
    """Senha curta deve retornar (False, mensagem) sem chamar Supabase."""
    ok, msg = auth.authenticate_user("user@example.com", "123")

    assert ok is False
    assert msg == "A senha deve ter ao menos 6 caracteres."

    # Não deve ter chamado Supabase
    mock_supabase.auth.sign_in_with_password.assert_not_called()


def test_authenticate_user_erro_conexao(mock_supabase: MagicMock):
    """Erro de conexão deve retornar (False, mensagem)."""
    mock_supabase.auth.sign_in_with_password.side_effect = Exception("Network error")

    with patch("src.core.auth.auth.get_supabase", return_value=mock_supabase):
        ok, msg = auth.authenticate_user("user@example.com", "senha123")

    assert ok is False
    assert "Falha ao conectar no Supabase" in msg


# ============================================================================
# 5) check_rate_limit
# ============================================================================


def test_check_rate_limit_primeira_tentativa():
    """Primeira tentativa deve ser permitida."""
    allowed, remaining = auth.check_rate_limit("user@example.com")

    assert allowed is True
    assert remaining == 0.0


def test_check_rate_limit_bloqueia_apos_5_tentativas():
    """Após 5 tentativas, deve bloquear por 60 segundos."""
    email = "user@example.com"
    now = time.time()

    # Simular 5 tentativas recentes
    auth._set_login_attempts_for_tests(email, 5, now)

    allowed, remaining = auth.check_rate_limit(email)

    assert allowed is False
    assert 59.0 < remaining <= 60.0


def test_check_rate_limit_reset_apos_60_segundos():
    """Após 60 segundos, tentativas devem ser resetadas."""
    email = "user@example.com"
    old_time = time.time() - 61  # 61 segundos atrás

    # Simular 5 tentativas antigas
    auth._set_login_attempts_for_tests(email, 5, old_time)

    allowed, remaining = auth.check_rate_limit(email)

    assert allowed is True
    assert remaining == 0.0


def test_check_rate_limit_incrementa_tentativas_apos_falha(mock_supabase: MagicMock):
    """Falha de login deve incrementar contador de tentativas."""
    email = "user@example.com"
    mock_supabase.auth.sign_in_with_password.side_effect = Exception("invalid credentials")

    with patch("src.core.auth.auth.get_supabase", return_value=mock_supabase):
        # 5 tentativas falhadas
        for _ in range(5):
            auth.authenticate_user(email, "senhaerrada")

        # 6ª tentativa deve ser bloqueada por rate limit
        ok, msg = auth.authenticate_user(email, "senhaerrada")

    assert ok is False
    assert "Muitas tentativas recentes" in msg


def test_check_rate_limit_limpa_contador_apos_sucesso(mock_supabase: MagicMock):
    """Login bem-sucedido deve limpar contador de tentativas."""
    email = "user@example.com"

    # Mock user e session
    mock_user = MagicMock()
    mock_user.email = email
    mock_session = MagicMock()
    mock_session.access_token = "fake_token"
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(user=mock_user)
    mock_supabase.auth.get_session.return_value = mock_session

    with patch("src.core.auth.auth.get_supabase", return_value=mock_supabase):
        # Simular 3 tentativas falhadas
        auth._set_login_attempts_for_tests(email, 3, time.time())

        # Login bem-sucedido
        ok, msg = auth.authenticate_user(email, "senhacerta")

        # Contador deve ter sido limpo
        attempts = auth._get_login_attempts_for_tests(email)
        assert attempts is None


# ============================================================================
# 6) Helpers de teste (garantir que existem)
# ============================================================================


def test_reset_auth_for_tests():
    """_reset_auth_for_tests deve limpar tentativas."""
    auth._set_login_attempts_for_tests("test@example.com", 5, time.time())

    auth._reset_auth_for_tests()

    attempts = auth._get_login_attempts_for_tests("test@example.com")
    assert attempts is None


def test_set_login_attempts_for_tests():
    """_set_login_attempts_for_tests deve definir tentativas."""
    email = "test@example.com"
    now = time.time()

    auth._set_login_attempts_for_tests(email, 3, now)

    attempts = auth._get_login_attempts_for_tests(email)
    assert attempts is not None
    assert attempts[0] == 3
    assert attempts[1] == now


def test_get_login_attempts_for_tests():
    """_get_login_attempts_for_tests deve retornar tentativas."""
    email = "test@example.com"
    now = time.time()

    auth._set_login_attempts_for_tests(email, 2, now)

    attempts = auth._get_login_attempts_for_tests(email)
    assert attempts == (2, now)
