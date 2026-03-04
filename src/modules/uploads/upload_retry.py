"""Upload com retry e backoff para erros de rede/servidor.

FASE 7 → PR-10: Implementação agora delega ao núcleo ``retry_call``
de ``src.infra.retry_policy``. Mantém classificação de erros upload-specific
e conversão de exceções para tipos semânticos.

Referência: https://developers.google.com/drive/api/guides/manage-uploads#resumable-uploads
"""

from __future__ import annotations

import logging
import socket
import time
from typing import Any, Callable, TypeVar

from src.infra.retry_policy import retry_call as _core_retry

from .exceptions import (
    UploadError,
    make_network_error,
    make_server_error,
)

logger = logging.getLogger(__name__)

# Alias interno para permitir patch local em testes (sem afetar outros módulos)
_sleep = time.sleep

T = TypeVar("T")

# ============================================================================
# Configuração de retry
# ============================================================================

DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_BASE: float = 0.5  # segundos
DEFAULT_BACKOFF_MAX: float = 8.0  # segundos
DEFAULT_JITTER: float = 0.3  # fração do delay (≈ jitter máximo em segundos)


# ============================================================================
# Classificação de erros
# ============================================================================


def _is_network_error(exc: Exception) -> bool:
    """Verifica se a exceção é um erro de rede (retry).

    Erros de rede são transitórios e merecem retry.
    """
    # Erros de socket
    if isinstance(exc, (socket.error, socket.timeout, OSError)):
        return True

    # Erros de bibliotecas HTTP
    exc_name = type(exc).__name__.lower()
    network_indicators = (
        "connection",
        "timeout",
        "network",
        "socket",
        "read",
        "write",
        "protocol",
        "dns",
    )
    if any(ind in exc_name for ind in network_indicators):
        return True

    # Verificar mensagem de erro
    exc_msg = str(exc).lower()
    if any(ind in exc_msg for ind in ("connection", "timeout", "network unreachable")):
        return True

    return False


def _is_server_error(exc: Exception) -> tuple[bool, int | None]:
    """Verifica se a exceção é um erro de servidor (5xx, retry).

    Returns:
        Tupla (is_server_error, status_code_or_none).
    """
    exc_str = str(exc)

    # Detectar código HTTP na mensagem
    for code in range(500, 600):
        if str(code) in exc_str:
            return True, code

    # Palavras-chave de erro de servidor
    server_indicators = ("internal server", "bad gateway", "service unavailable", "gateway timeout")
    if any(ind in exc_str.lower() for ind in server_indicators):
        return True, None

    return False, None


def _is_client_error(exc: Exception) -> tuple[bool, int | None]:
    """Verifica se a exceção é um erro de cliente (4xx, sem retry).

    Exceção: 429 Too Many Requests pode ter retry.

    Returns:
        Tupla (is_client_error, status_code_or_none).
    """
    exc_str = str(exc)

    # Detectar código HTTP 4xx na mensagem
    for code in range(400, 500):
        if str(code) in exc_str:
            # 429 é rate limit - pode ter retry
            if code == 429:
                return False, 429
            return True, code

    return False, None


def _is_duplicate_error(exc: Exception) -> bool:
    """Verifica se é erro de duplicação (arquivo já existe)."""
    exc_str = str(exc).lower()
    return any(ind in exc_str for ind in ("duplicate", "already exists", "conflict", "409"))


def _is_permission_error(exc: Exception) -> bool:
    """Verifica se é erro de permissão (RLS, 403)."""
    exc_str = str(exc).lower()
    return any(ind in exc_str for ind in ("permission", "forbidden", "403", "rls", "unauthorized", "401"))


# ============================================================================
# Função principal de retry
# ============================================================================


def _is_upload_transient(exc: Exception) -> bool:
    """Classifica se a exceção merece retry no contexto de upload."""
    # Client errors (4xx exceto 429) → NÃO retry
    is_client, _ = _is_client_error(exc)
    if is_client:
        return False
    # Duplicate (409) → NÃO retry
    if _is_duplicate_error(exc):
        return False
    # Permission → NÃO retry
    if _is_permission_error(exc):
        return False
    # Network ou server → retry
    return _is_network_error(exc) or _is_server_error(exc)[0]


def upload_with_retry(
    upload_fn: Callable[..., T],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    backoff_max: float = DEFAULT_BACKOFF_MAX,
    jitter: float = DEFAULT_JITTER,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    **kwargs: Any,
) -> T:
    """Executa função de upload com retry via ``retry_call`` centralizado.

    Args:
        upload_fn: Função de upload a executar.
        *args: Argumentos posicionais para upload_fn.
        max_retries: Nº máximo de re-tentativas (padrão: 3).
        backoff_base: Base do backoff exponencial em segundos.
        backoff_max: Delay máximo de backoff em segundos.
        jitter: Jitter máximo em segundos.
        on_retry: Callback(attempt, exception, delay) chamado antes de cada retry.
        **kwargs: Argumentos nomeados para upload_fn.

    Returns:
        Retorno de upload_fn se sucesso.

    Raises:
        UploadNetworkError: Se todas as tentativas falharem por erro de rede.
        UploadServerError: Se todas as tentativas falharem por erro de servidor.
        UploadError: Para outros erros sem retry.
    """
    try:
        return _core_retry(
            upload_fn,
            *args,
            max_attempts=max_retries + 1,
            base_delay=backoff_base,
            max_delay=backoff_max,
            jitter=jitter,
            is_transient=_is_upload_transient,
            sleep_fn=_sleep,
            on_retry=on_retry,
            **kwargs,
        )
    except UploadError:
        raise
    except Exception as exc:
        # Converte exceção genérica final em tipo semântico de upload
        if _is_duplicate_error(exc):
            _, code = _is_client_error(exc)
            raise make_server_error("duplicate", original=exc, status_code=code) from exc
        if _is_permission_error(exc):
            _, code = _is_client_error(exc)
            raise make_server_error("permission", original=exc, status_code=code) from exc
        is_client, client_code = _is_client_error(exc)
        if is_client:
            raise UploadError(
                f"Erro ao enviar arquivo (código {client_code}).",
                detail=f"HTTP {client_code}: {exc}",
            ) from exc
        if _is_network_error(exc):
            raise make_network_error("network", original=exc) from exc
        is_server, server_code = _is_server_error(exc)
        if is_server:
            raise make_server_error("server", original=exc, status_code=server_code) from exc
        raise UploadError(
            "Ocorreu um erro inesperado ao enviar o arquivo.",
            detail=str(exc),
        ) from exc


def classify_upload_exception(exc: Exception) -> UploadError:
    """Classifica uma exceção de upload em tipo semântico.

    Útil para converter exceções genéricas em exceções tipadas
    sem usar retry (por exemplo, em código legado).

    Args:
        exc: Exceção original.

    Returns:
        UploadError (ou subclasse) com mensagem apropriada.
        A exceção original é preservada em __cause__.
    """
    if isinstance(exc, UploadError):
        return exc

    if _is_duplicate_error(exc):
        return make_server_error("duplicate", original=exc)

    if _is_permission_error(exc):
        return make_server_error("permission", original=exc)

    if _is_network_error(exc):
        return make_network_error("network", original=exc)

    is_server, code = _is_server_error(exc)
    if is_server:
        return make_server_error("server", original=exc, status_code=code)

    is_client, code = _is_client_error(exc)
    if is_client:
        err = UploadError(
            f"Erro ao enviar arquivo (código {code}).",
            detail=f"HTTP {code}: {exc}",
        )
        # Preservar exceção original em __cause__
        err.__cause__ = exc
        return err

    # Erro genérico/inesperado
    err = UploadError(
        "Ocorreu um erro inesperado ao enviar o arquivo.",
        detail=str(exc),
    )
    # Preservar exceção original em __cause__
    err.__cause__ = exc
    return err


__all__ = [
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_BACKOFF_BASE",
    "DEFAULT_BACKOFF_MAX",
    "DEFAULT_JITTER",
    "upload_with_retry",
    "classify_upload_exception",
]
