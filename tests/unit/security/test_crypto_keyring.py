# tests/unit/security/test_crypto_keyring.py
"""Testes para integração de keyring no módulo crypto."""

from unittest.mock import patch

import pytest

from security import crypto


@pytest.fixture(autouse=True)
def reset_crypto_state():
    """Reseta o singleton do Fernet antes de cada teste."""
    crypto._reset_fernet_cache()
    yield
    crypto._reset_fernet_cache()


@pytest.fixture
def mock_keyring_available():
    """Mock para simular keyring disponível."""
    with patch("security.crypto._keyring_is_available", return_value=True):
        yield


@pytest.fixture
def mock_keyring_unavailable():
    """Mock para simular keyring indisponível."""
    with patch("security.crypto._keyring_is_available", return_value=False):
        yield


@pytest.fixture
def mock_keyring_get(mock_keyring_available):
    """Mock para keyring.get_password."""
    with patch("security.crypto._keyring_get_secret_key") as mock_get:
        yield mock_get


@pytest.fixture
def mock_keyring_set(mock_keyring_available):
    """Mock para keyring.set_password."""
    with patch("security.crypto._keyring_set_secret_key") as mock_set:
        yield mock_set


def test_priority_1_env_var_takes_precedence(monkeypatch, mock_keyring_get):
    """
    PRIORIDADE 1: Se RC_CLIENT_SECRET_KEY está definida no ambiente,
    deve usar essa chave e NÃO consultar o keyring.
    """
    # Gera uma chave válida para teste
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key().decode("utf-8")

    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", test_key)

    # Executa criptografia/descriptografia para garantir que _get_fernet() foi chamado
    plaintext = "senha-teste"
    encrypted = crypto.encrypt_text(plaintext)
    decrypted = crypto.decrypt_text(encrypted)

    assert decrypted == plaintext
    # Verifica que keyring NÃO foi consultado
    mock_keyring_get.assert_not_called()


def test_priority_2_keyring_found(monkeypatch, mock_keyring_get, mock_keyring_set):
    """
    PRIORIDADE 2: Se não há env var, mas keyring tem chave, usa essa chave.
    """
    from cryptography.fernet import Fernet

    stored_key = Fernet.generate_key().decode("utf-8")

    # Simula keyring retornando uma chave existente
    mock_keyring_get.return_value = stored_key
    monkeypatch.delenv("RC_CLIENT_SECRET_KEY", raising=False)

    plaintext = "senha-teste"
    encrypted = crypto.encrypt_text(plaintext)
    decrypted = crypto.decrypt_text(encrypted)

    assert decrypted == plaintext
    mock_keyring_get.assert_called_once()
    # NÃO deve salvar (já existe)
    mock_keyring_set.assert_not_called()


def test_priority_2_keyring_not_found_generates_new(monkeypatch, mock_keyring_get, mock_keyring_set):
    """
    PRIORIDADE 2: Se keyring está disponível mas não tem chave, gera nova e salva.
    """
    mock_keyring_get.return_value = None  # Nenhuma chave armazenada
    mock_keyring_set.return_value = True  # Sucesso ao salvar
    monkeypatch.delenv("RC_CLIENT_SECRET_KEY", raising=False)

    plaintext = "senha-teste"
    encrypted = crypto.encrypt_text(plaintext)
    decrypted = crypto.decrypt_text(encrypted)

    assert decrypted == plaintext
    mock_keyring_get.assert_called_once()
    # Deve ter salvo uma nova chave
    mock_keyring_set.assert_called_once()
    # Valida formato da chave gerada (base64, 44 caracteres)
    generated_key = mock_keyring_set.call_args[0][0]
    assert len(generated_key) == 44
    assert generated_key.endswith("=")


def test_fallback_keyring_unavailable_raises_error(monkeypatch, mock_keyring_unavailable):
    """
    FALLBACK: Se não há env var E keyring indisponível, levanta RuntimeError.
    """
    monkeypatch.delenv("RC_CLIENT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="RC_CLIENT_SECRET_KEY não encontrada e keyring indisponível"):
        crypto.encrypt_text("teste")


def test_keyring_disabled_in_pytest_environment(monkeypatch):
    """
    Keyring deve ser desabilitado automaticamente se PYTEST_CURRENT_TEST está presente.
    """
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/unit/security/test_crypto_keyring.py::test_exemplo")
    monkeypatch.delenv("RC_CLIENT_SECRET_KEY", raising=False)

    assert crypto._keyring_is_available() is False


def test_keyring_disabled_with_rc_testing_flag(monkeypatch):
    """
    Keyring deve ser desabilitado se RC_TESTING=1.
    """
    monkeypatch.setenv("RC_TESTING", "1")

    assert crypto._keyring_is_available() is False


def test_invalid_key_format_raises_error(monkeypatch):
    """
    Se chave tiver formato inválido (não base64 ou tamanho incorreto), deve levantar RuntimeError.
    """
    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", "chave-invalida-123")

    with pytest.raises(RuntimeError, match="formato inválido"):
        crypto.encrypt_text("teste")


def test_encrypt_decrypt_roundtrip_with_keyring(monkeypatch, mock_keyring_get):
    """
    Teste de integração: criptografa e descriptografa usando chave do keyring.
    """
    from cryptography.fernet import Fernet

    keyring_key = Fernet.generate_key().decode("utf-8")

    mock_keyring_get.return_value = keyring_key
    monkeypatch.delenv("RC_CLIENT_SECRET_KEY", raising=False)

    original = "senha-complexa-123!@#"
    encrypted = crypto.encrypt_text(original)
    decrypted = crypto.decrypt_text(encrypted)

    assert encrypted != original  # Criptografado deve ser diferente
    assert decrypted == original  # Descriptografia deve recuperar original
    assert len(encrypted) > len(original)  # Token é maior que texto original


def test_keyring_save_failure_does_not_crash(monkeypatch, mock_keyring_get, mock_keyring_set):
    """
    Se falha ao salvar chave no keyring, sistema deve continuar funcionando
    com chave em memória (log de warning, mas sem crash).
    """
    mock_keyring_get.return_value = None
    mock_keyring_set.return_value = False  # Falha ao salvar
    monkeypatch.delenv("RC_CLIENT_SECRET_KEY", raising=False)

    # Deve funcionar normalmente apesar do erro ao salvar
    plaintext = "senha-teste"
    encrypted = crypto.encrypt_text(plaintext)
    decrypted = crypto.decrypt_text(encrypted)

    assert decrypted == plaintext
