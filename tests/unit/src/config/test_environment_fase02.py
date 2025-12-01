"""
Coverage Pack 05 - Testes para src/config/environment.py.

Foco: Cobrir linhas 15-17, 22-23, 44-48 (branches de erro).
"""

from __future__ import annotations

from unittest.mock import patch, Mock

import pytest

from src.config import environment


# ============================================================================
# Testes de load_env (linhas 15-17, 22-23)
# ============================================================================


def test_load_env_sem_dotenv_instalado():
    """
    Testa branch 15-17: quando dotenv não está disponível.
    Deve logar debug e retornar sem erro.
    """
    with patch("src.config.environment.logger") as mock_logger:
        # Simula ImportError ao tentar importar dotenv
        with patch("builtins.__import__", side_effect=ImportError("No module named 'dotenv'")):
            environment.load_env()

        # Deve ter logado o erro de forma não fatal
        assert mock_logger.debug.called
        call_args = mock_logger.debug.call_args[0]
        assert "dotenv" in call_args[0].lower()


def test_load_env_falha_ao_carregar_arquivo():
    """
    Testa branch 22-23: quando load_dotenv ou resource_path falham.
    Deve logar debug e retornar sem erro.
    """
    with patch("src.config.environment.logger") as mock_logger:
        # Mock dotenv disponível mas resource_path falha
        mock_resource_path = Mock(side_effect=FileNotFoundError(".env not found"))

        with patch("dotenv.load_dotenv"):
            with patch("src.utils.resource_path.resource_path", mock_resource_path):
                environment.load_env()

        # Deve ter logado a falha
        assert mock_logger.debug.called
        call_args = mock_logger.debug.call_args[0]
        assert "falha" in call_args[0].lower() or ".env" in call_args[0].lower()


def test_load_env_sucesso(monkeypatch, tmp_path):
    """
    Testa caminho feliz: dotenv disponível e carrega .env com sucesso.
    """
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_VAR=test_value\n")

    # Mock resource_path para retornar nosso arquivo temporário
    with patch("src.utils.resource_path.resource_path", return_value=str(env_file)):
        with patch("dotenv.load_dotenv") as mock_load:
            environment.load_env()

            # load_dotenv deve ter sido chamado
            assert mock_load.called


# ============================================================================
# Testes de env_str
# ============================================================================


def test_env_str_retorna_valor_presente(monkeypatch):
    """env_str retorna valor quando variável existe."""
    monkeypatch.setenv("TEST_STR_VAR", "test_value")

    result = environment.env_str("TEST_STR_VAR")

    assert result == "test_value"


def test_env_str_retorna_default_quando_ausente(monkeypatch):
    """env_str retorna default quando variável não existe."""
    monkeypatch.delenv("MISSING_VAR", raising=False)

    result = environment.env_str("MISSING_VAR", default="default_value")

    assert result == "default_value"


def test_env_str_retorna_none_quando_ausente_sem_default(monkeypatch):
    """env_str retorna None quando variável não existe e sem default."""
    monkeypatch.delenv("MISSING_VAR", raising=False)

    result = environment.env_str("MISSING_VAR")

    assert result is None


# ============================================================================
# Testes de env_bool
# ============================================================================


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("yes", True),
        ("Yes", True),
        ("YES", True),
        ("y", True),
        ("Y", True),
        ("on", True),
        ("On", True),
        ("ON", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
        ("random", False),
        ("", False),
    ],
)
def test_env_bool_valores_diversos(monkeypatch, value, expected):
    """env_bool trata diversos valores corretamente."""
    monkeypatch.setenv("TEST_BOOL_VAR", value)

    result = environment.env_bool("TEST_BOOL_VAR")

    assert result == expected


def test_env_bool_retorna_default_quando_ausente(monkeypatch):
    """env_bool retorna default quando variável não existe."""
    monkeypatch.delenv("MISSING_BOOL", raising=False)

    result_false = environment.env_bool("MISSING_BOOL", default=False)
    result_true = environment.env_bool("MISSING_BOOL", default=True)

    assert result_false is False
    assert result_true is True


def test_env_bool_trata_espacos(monkeypatch):
    """env_bool trata valores com espaços."""
    monkeypatch.setenv("TEST_BOOL_SPACES", "  true  ")

    result = environment.env_bool("TEST_BOOL_SPACES")

    assert result is True


# ============================================================================
# Testes de env_int (linhas 44-48)
# ============================================================================


def test_env_int_retorna_valor_valido(monkeypatch):
    """env_int retorna inteiro quando valor é válido."""
    monkeypatch.setenv("TEST_INT_VAR", "42")

    result = environment.env_int("TEST_INT_VAR")

    assert result == 42


def test_env_int_retorna_default_quando_ausente(monkeypatch):
    """env_int retorna default quando variável não existe."""
    monkeypatch.delenv("MISSING_INT", raising=False)

    result = environment.env_int("MISSING_INT", default=99)

    assert result == 99


def test_env_int_retorna_default_quando_valor_invalido(monkeypatch):
    """
    Testa branch 46-47: ValueError capturado quando valor não é int.
    Deve retornar default sem levantar exceção.
    """
    monkeypatch.setenv("INVALID_INT", "not_a_number")

    result = environment.env_int("INVALID_INT", default=10)

    assert result == 10


def test_env_int_retorna_default_quando_valor_vazio(monkeypatch):
    """env_int retorna default quando valor é string vazia."""
    monkeypatch.setenv("EMPTY_INT", "")

    result = environment.env_int("EMPTY_INT", default=5)

    assert result == 5


def test_env_int_aceita_negativos(monkeypatch):
    """env_int aceita números negativos."""
    monkeypatch.setenv("NEGATIVE_INT", "-42")

    result = environment.env_int("NEGATIVE_INT")

    assert result == -42


def test_env_int_aceita_zero(monkeypatch):
    """env_int aceita zero explícito."""
    monkeypatch.setenv("ZERO_INT", "0")

    result = environment.env_int("ZERO_INT", default=99)

    assert result == 0


# ============================================================================
# Testes de cloud_only_default
# ============================================================================


def test_cloud_only_default_true_quando_rc_no_local_fs_true(monkeypatch):
    """cloud_only_default retorna True quando RC_NO_LOCAL_FS=true."""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "true")

    result = environment.cloud_only_default()

    assert result is True


def test_cloud_only_default_false_quando_rc_no_local_fs_false(monkeypatch):
    """cloud_only_default retorna False quando RC_NO_LOCAL_FS=false."""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "false")

    result = environment.cloud_only_default()

    assert result is False


def test_cloud_only_default_usa_default_true_quando_ausente(monkeypatch):
    """cloud_only_default retorna True (default) quando RC_NO_LOCAL_FS ausente."""
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)

    result = environment.cloud_only_default()

    assert result is True
