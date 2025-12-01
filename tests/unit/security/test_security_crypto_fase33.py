# tests/test_security_crypto_fase33.py
"""
Testes para o módulo security/crypto.py (COV-SEC-001 / SEG-004).
Objetivo: Aumentar cobertura de ~19,5% para ≥ 80%.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from security import crypto


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def valid_fernet_key() -> str:
    """Gera uma chave Fernet válida para testes."""
    return Fernet.generate_key().decode("utf-8")


@pytest.fixture
def mock_env_key(valid_fernet_key: str, monkeypatch):
    """Mock da variável de ambiente RC_CLIENT_SECRET_KEY com chave válida."""
    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", valid_fernet_key)
    return valid_fernet_key


@pytest.fixture
def mock_env_key_missing(monkeypatch):
    """Mock de ambiente SEM a chave (para testar erros)."""
    monkeypatch.delenv("RC_CLIENT_SECRET_KEY", raising=False)


# ========================================
# 2.3.1) Cenário "round-trip" (feliz)
# ========================================


def test_encrypt_decrypt_roundtrip_texto_simples(mock_env_key):
    """
    Testa que encrypt_text + decrypt_text recuperam o valor original
    para texto simples em ASCII.
    """
    original = "senha-teste"
    encrypted = crypto.encrypt_text(original)

    # Deve retornar algo diferente do original
    assert encrypted != original
    assert encrypted != ""

    # Descriptografar deve retornar o original
    decrypted = crypto.decrypt_text(encrypted)
    assert decrypted == original


def test_encrypt_decrypt_roundtrip_unicode(mock_env_key):
    """
    Testa round-trip com caracteres acentuados (unicode).
    """
    original = "áéíóú ç ãõ ÀÈÌÒÙ ñ €"
    encrypted = crypto.encrypt_text(original)

    assert encrypted != original
    assert encrypted != ""

    decrypted = crypto.decrypt_text(encrypted)
    assert decrypted == original


def test_encrypt_decrypt_roundtrip_texto_longo(mock_env_key):
    """
    Testa round-trip com texto longo (múltiplas linhas).
    """
    original = "Linha 1\nLinha 2 com áçêntös\nLinha 3 com emoji 🔐\n" * 10
    encrypted = crypto.encrypt_text(original)

    assert encrypted != original

    decrypted = crypto.decrypt_text(encrypted)
    assert decrypted == original


def test_encrypt_decrypt_roundtrip_string_vazia(mock_env_key):
    """
    Testa comportamento com string vazia (deve retornar vazio sem erro).
    """
    original = ""
    encrypted = crypto.encrypt_text(original)
    assert encrypted == ""

    decrypted = crypto.decrypt_text(encrypted)
    assert decrypted == ""


def test_encrypt_text_nao_retorna_valor_original(mock_env_key):
    """
    Garante que o texto criptografado é diferente do original
    e não é vazio.
    """
    original = "valor-secreto-123"
    encrypted = crypto.encrypt_text(original)

    assert encrypted != original
    assert len(encrypted) > len(original)
    assert encrypted != ""

    # Token Fernet deve começar com caracteres base64-like
    # (Fernet pode incluir quebras de linha em tokens longos)
    assert any(c.isalnum() or c in "=_-" for c in encrypted)


# ========================================
# 2.3.2) Entradas inválidas
# ========================================


def test_encrypt_text_com_none_retorna_vazio(mock_env_key):
    """
    Testa que encrypt_text(None) não levanta exceção,
    mas retorna string vazia (comportamento atual do código).
    """
    # O código atual faz: if not plain: return ""
    # None é falsy, então deve retornar ""
    result = crypto.encrypt_text(None)
    assert result == ""


def test_decrypt_text_com_none_retorna_vazio(mock_env_key):
    """
    Testa que decrypt_text(None) retorna vazio sem erro.
    """
    result = crypto.decrypt_text(None)
    assert result == ""


def test_encrypt_text_sem_chave_no_env_levanta_runtime_error(mock_env_key_missing):
    """
    Testa que sem RC_CLIENT_SECRET_KEY no ambiente,
    encrypt_text levanta RuntimeError.
    """
    with pytest.raises(RuntimeError, match="RC_CLIENT_SECRET_KEY não encontrada"):
        crypto.encrypt_text("algum-texto")


def test_decrypt_text_sem_chave_no_env_levanta_runtime_error(mock_env_key_missing):
    """
    Testa que sem RC_CLIENT_SECRET_KEY no ambiente,
    decrypt_text levanta RuntimeError.
    """
    with pytest.raises(RuntimeError, match="RC_CLIENT_SECRET_KEY não encontrada"):
        crypto.decrypt_text("algum-token")


def test_get_encryption_key_com_chave_invalida_levanta_runtime_error(monkeypatch):
    """
    Testa que se RC_CLIENT_SECRET_KEY não for uma chave Fernet válida,
    ao tentar usar (encrypt_text), Fernet levanta exceção que é capturada
    e re-levantada como RuntimeError.
    """
    # Chave inválida (não é base64 Fernet válido)
    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", "chave-invalida-nao-base64")

    with pytest.raises(RuntimeError, match="Falha na criptografia"):
        crypto.encrypt_text("teste")


# ========================================
# 2.3.3) Chave errada / corrupção de dados
# ========================================


def test_decrypt_with_wrong_key_levanta_runtime_error(valid_fernet_key, monkeypatch):
    """
    Testa que descriptografar com chave diferente da usada
    para criptografar levanta RuntimeError.
    """
    # Criptografar com uma chave
    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", valid_fernet_key)
    encrypted = crypto.encrypt_text("texto-secreto")

    # Trocar para outra chave válida mas diferente
    outra_chave = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", outra_chave)

    # Tentar descriptografar deve falhar
    with pytest.raises(RuntimeError, match="Falha na descriptografia"):
        crypto.decrypt_text(encrypted)


def test_decrypt_token_corrompido_levanta_runtime_error(mock_env_key):
    """
    Testa que um token corrompido (base64 inválido ou modificado)
    levanta RuntimeError ao descriptografar.
    """
    original = "texto-original"
    encrypted = crypto.encrypt_text(original)

    # Corromper o token (modificar caracteres no meio)
    corrupted = encrypted[:10] + "XXXXX" + encrypted[15:]

    with pytest.raises(RuntimeError, match="Falha na descriptografia"):
        crypto.decrypt_text(corrupted)


def test_decrypt_token_base64_invalido_levanta_runtime_error(mock_env_key):
    """
    Testa que um token que não é base64 válido levanta RuntimeError.
    """
    token_invalido = "isso-não-é-base64-fernet!!!@#$%"

    with pytest.raises(RuntimeError, match="Falha na descriptografia"):
        crypto.decrypt_text(token_invalido)


# ========================================
# 2.3.4) Compatibilidade com API usada no app
# ========================================


def test_encrypt_text_formato_usado_em_data_supabase_repo(mock_env_key):
    """
    Testa que encrypt_text pode ser usado conforme data/supabase_repo.py:
    - Recebe string (senha em texto plano)
    - Retorna string (token criptografado)
    """
    senha_plana = "minha-senha-123"
    token = crypto.encrypt_text(senha_plana)

    assert isinstance(token, str)
    assert token != senha_plana
    assert len(token) > 0


def test_decrypt_text_formato_usado_em_passwords_controller(mock_env_key):
    """
    Testa que decrypt_text pode ser usado conforme src/modules/passwords/controller.py:
    - Recebe token (string)
    - Retorna texto plano (string)
    """
    senha_plana = "senha-original-456"
    token = crypto.encrypt_text(senha_plana)

    senha_recuperada = crypto.decrypt_text(token)

    assert isinstance(senha_recuperada, str)
    assert senha_recuperada == senha_plana


def test_encrypt_decrypt_com_espacos_e_caracteres_especiais(mock_env_key):
    """
    Testa que senhas com espaços, tabs, newlines são preservadas.
    Caso de uso real: senhas complexas podem ter qualquer caractere.
    """
    senha_complexa = "  senha com espaços\t\ne\nquebras  "
    token = crypto.encrypt_text(senha_complexa)
    recuperada = crypto.decrypt_text(token)

    assert recuperada == senha_complexa


# ========================================
# 2.3.5) Branches e comportamentos condicionais
# ========================================


def test_get_encryption_key_retorna_bytes(mock_env_key):
    """
    Testa diretamente a função _get_encryption_key para garantir
    que retorna bytes no formato esperado pelo Fernet.
    """
    key = crypto._get_encryption_key()

    assert isinstance(key, bytes)
    assert len(key) > 0

    # Deve ser uma chave Fernet válida (pode instanciar Fernet sem erro)
    try:
        Fernet(key)
    except Exception as e:
        pytest.fail(f"Chave retornada não é Fernet válida: {e}")


def test_encrypt_text_com_exception_no_fernet_e_capturada(monkeypatch, valid_fernet_key):
    """
    Testa que se Fernet.encrypt levantar exceção,
    ela é capturada e re-levantada como RuntimeError com mensagem apropriada.
    """
    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", valid_fernet_key)

    # Mock Fernet.encrypt para levantar exceção
    with patch("security.crypto.Fernet") as mock_fernet:
        mock_fernet.return_value.encrypt.side_effect = ValueError("Erro simulado")

        with pytest.raises(RuntimeError, match="Falha na criptografia"):
            crypto.encrypt_text("teste")


def test_decrypt_text_com_exception_no_fernet_e_capturada(monkeypatch, valid_fernet_key):
    """
    Testa que se Fernet.decrypt levantar exceção,
    ela é capturada e re-levantada como RuntimeError.
    """
    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", valid_fernet_key)

    with patch("security.crypto.Fernet") as mock_fernet:
        mock_fernet.return_value.decrypt.side_effect = ValueError("Erro simulado")

        with pytest.raises(RuntimeError, match="Falha na descriptografia"):
            crypto.decrypt_text("algum-token")


# ========================================
# Testes de logging
# ========================================


def test_encrypt_text_loga_exception_em_caso_de_erro(monkeypatch, valid_fernet_key, caplog):
    """
    Testa que quando encrypt_text falha, a exceção é logada.
    """
    import logging

    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", valid_fernet_key)

    with patch("security.crypto.Fernet") as mock_fernet:
        mock_fernet.return_value.encrypt.side_effect = ValueError("Erro de teste")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                crypto.encrypt_text("teste")

        # Verifica que houve log de exceção
        assert any("Erro ao criptografar texto" in record.message for record in caplog.records)


def test_decrypt_text_loga_exception_em_caso_de_erro(monkeypatch, valid_fernet_key, caplog):
    """
    Testa que quando decrypt_text falha, a exceção é logada.
    """
    import logging

    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", valid_fernet_key)

    with patch("security.crypto.Fernet") as mock_fernet:
        mock_fernet.return_value.decrypt.side_effect = ValueError("Erro de teste")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                crypto.decrypt_text("token-qualquer")

        # Verifica que houve log de exceção
        assert any("Erro ao descriptografar token" in record.message for record in caplog.records)


# ========================================
# Coverage Pack 05 - Linha 24-25 (except do _get_encryption_key)
# ========================================


def test_get_encryption_key_erro_ao_processar_chave(monkeypatch):
    """
    Testa branch de exceção no .encode() da chave (linhas 24-25).
    Simula uma situação onde key_str.encode() levanta exceção.
    """

    # Mock de os.getenv retornando objeto que falha no encode
    class BadString:
        def __str__(self):
            return "bad_key"

        def encode(self, *args, **kwargs):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "test error")

    with patch("security.crypto.os.getenv", return_value=BadString()):
        with pytest.raises(RuntimeError, match="Erro ao processar RC_CLIENT_SECRET_KEY"):
            crypto.encrypt_text("test")
