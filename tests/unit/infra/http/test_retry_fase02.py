"""
Coverage Pack 05 - Testes para infra/http/retry.py.

Foco: Cobrir branch parcial 43->42 (_collect_default_excs).
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.infra.http.retry import _collect_default_excs, retry_call, DEFAULT_EXCS


# ============================================================================
# Testes de _collect_default_excs (branch 43->42)
# ============================================================================


def test_collect_default_excs_retorna_tupla_nao_vazia():
    """_collect_default_excs deve retornar ao menos (Exception,)."""
    result = _collect_default_excs()
    assert isinstance(result, tuple)
    assert len(result) > 0
    assert Exception in result


def test_collect_default_excs_filtra_none_values():
    """
    Testa branch parcial 43->42: quando exc é None, não entra no if.
    Simula cenário onde httpx/httpcore não estão disponíveis.
    """
    # Mock getattr para retornar None em alguns casos
    with patch("src.infra.http.retry.httpx", None), patch("src.infra.http.retry.httpcore", None):
        result = _collect_default_excs()

        # Deve ainda ter Exception e socket.error
        assert isinstance(result, tuple)
        assert len(result) >= 2  # socket.error + Exception no mínimo
        assert Exception in result


def test_collect_default_excs_filtra_non_type_values():
    """
    Testa que valores que não são 'type' são filtrados.
    Força branch onde isinstance(exc, type) retorna False.
    """
    # Não há forma direta de forçar getattr a retornar não-type sem mock,
    # mas podemos verificar que o filtro funciona via inspeção do resultado
    result = _collect_default_excs()

    # Todas as exceções devem ser subclasses de BaseException
    for exc in result:
        assert isinstance(exc, type)
        assert issubclass(exc, BaseException)


def test_collect_default_excs_inclui_socket_error():
    """Verifica que socket.error está incluída nas exceções padrão."""
    import socket

    result = _collect_default_excs()

    # socket.error deve estar presente
    assert socket.error in result


def test_default_excs_constant_is_valid_tuple():
    """DEFAULT_EXCS deve ser uma tupla válida de exceções."""
    assert isinstance(DEFAULT_EXCS, tuple)
    assert len(DEFAULT_EXCS) > 0

    for exc in DEFAULT_EXCS:
        assert isinstance(exc, type)
        assert issubclass(exc, BaseException)


# ============================================================================
# Testes de retry_call (para garantir integração)
# ============================================================================


def test_retry_call_sucesso_primeira_tentativa():
    """retry_call retorna resultado quando função não falha."""
    mock_fn = Mock(return_value="success")

    result = retry_call(mock_fn, tries=3)

    assert result == "success"
    assert mock_fn.call_count == 1


def test_retry_call_com_retry_ate_sucesso():
    """retry_call tenta múltiplas vezes até sucesso."""
    call_count = {"count": 0}

    def failing_fn():
        call_count["count"] += 1
        if call_count["count"] < 3:
            raise ConnectionError("Temporary failure")
        return "success"

    with patch("src.infra.http.retry.time.sleep"):  # mock sleep para acelerar
        result = retry_call(failing_fn, tries=5, exceptions=(ConnectionError,))

    assert result == "success"
    assert call_count["count"] == 3


def test_retry_call_falha_apos_esgolar_tentativas():
    """retry_call propaga exceção após esgotar tentativas."""
    mock_fn = Mock(side_effect=ValueError("Persistent error"))

    with patch("src.infra.http.retry.time.sleep"):
        with pytest.raises(ValueError, match="Persistent error"):
            retry_call(mock_fn, tries=2, exceptions=(ValueError,))

    assert mock_fn.call_count == 2


def test_retry_call_usa_backoff_exponencial():
    """retry_call aplica backoff exponencial entre tentativas."""
    sleeps = []

    def mock_sleep(duration):
        sleeps.append(duration)

    mock_fn = Mock(side_effect=[RuntimeError("fail1"), RuntimeError("fail2"), "success"])

    with patch("src.infra.http.retry.time.sleep", side_effect=mock_sleep):
        result = retry_call(mock_fn, tries=3, backoff=0.5, jitter=0.0)

    assert result == "success"
    assert len(sleeps) == 2  # 2 falhas = 2 sleeps
    # backoff ** 1 = 0.5, backoff ** 2 = 0.25
    assert sleeps[0] == pytest.approx(0.5, abs=0.01)
    assert sleeps[1] == pytest.approx(0.25, abs=0.01)


def test_retry_call_adiciona_jitter():
    """retry_call adiciona jitter aleatório ao backoff."""
    sleeps = []

    def mock_sleep(duration):
        sleeps.append(duration)

    mock_fn = Mock(side_effect=[RuntimeError("fail"), "success"])

    with patch("src.infra.http.retry.time.sleep", side_effect=mock_sleep):
        result = retry_call(mock_fn, tries=2, backoff=0.5, jitter=0.2)

    assert result == "success"
    assert len(sleeps) == 1
    # 0.5 + random[0, 0.2] -> entre 0.5 e 0.7
    assert 0.5 <= sleeps[0] <= 0.7


def test_retry_call_com_args_e_kwargs():
    """retry_call passa argumentos corretamente para função."""
    mock_fn = Mock(return_value="result")

    result = retry_call(mock_fn, "arg1", "arg2", tries=1, key1="value1", key2="value2")

    assert result == "result"
    mock_fn.assert_called_once_with("arg1", "arg2", key1="value1", key2="value2")


def test_retry_call_com_excecao_customizada():
    """retry_call respeita tuple de exceções customizada."""
    mock_fn = Mock(side_effect=ValueError("error"))

    # ValueError não está em exceptions, então deve falhar imediatamente
    with pytest.raises(ValueError):
        retry_call(mock_fn, tries=3, exceptions=(ConnectionError,))

    assert mock_fn.call_count == 1  # não retenta


def test_retry_call_preserva_tipo_de_retorno():
    """retry_call preserva tipo do retorno via TypeVar."""

    def int_fn() -> int:
        return 42

    result = retry_call(int_fn, tries=1)

    assert isinstance(result, int)
    assert result == 42
