"""Upload com retry e backoff para erros de rede/servidor.

FASE 7 - Wrapper sobre operações de upload que adiciona:
1. Retry automático para erros de conexão
2. Retry para erros 5xx com backoff exponencial
3. Sem retry para erros 4xx (exceto 429 rate limit)
4. Conversão de exceções para tipos semânticos (UploadNetworkError, etc.)

Referência: https://developers.google.com/drive/api/guides/manage-uploads#resumable-uploads
"""

from __future__ import annotations

import logging
import random
import socket
import time
from typing import Any, Callable, TypeVar

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
DEFAULT_JITTER: float = 0.3  # fração do delay


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
    """Executa funçõão de upload com retry e backoff exponencial.

    Args:
        upload_fn: Funçõão de upload a executar.
        *args: Argumentos posicionais para upload_fn.
        max_retries: Nº máximo de tentativas (padrão: 3).
        backoff_base: Base do backoff exponencial em segundos.
        backoff_max: Delay máximo de backoff em segundos.
        jitter: Fração de variação aleatória no delay.
        on_retry: Callback(attempt, exception, delay) chamado antes de cada retry.
        **kwargs: Argumentos nomeados para upload_fn.

    Returns:
        Retorno de upload_fn se sucesso.

    Raises:
        UploadNetworkError: Se todas as tentativas falharem por erro de rede.
        UploadServerError: Se todas as tentativas falharem por erro de servidor.
        UploadError: Para outros erros sem retry.
    """
    local_path_value = kwargs.get("local_path")
    remote_key_value = kwargs.get("remote_key")
    if local_path_value is None and args:
        local_path_value = args[0]
    if remote_key_value is None and len(args) > 1:
        remote_key_value = args[1]

    local_path_str = str(local_path_value) if local_path_value is not None else None
    remote_key_str = str(remote_key_value) if remote_key_value is not None else None
    base_extra = {
        "remote_key": remote_key_str,
        "local_path": local_path_str,
    }

    last_exception: Exception | None = None
    attempt = 0

    logger.info(
        "Upload iniciado com retry",
        extra={
            **base_extra,
            "max_retries": max_retries,
        },
    )

    while attempt <= max_retries:
        current_attempt = attempt + 1
        logger.debug(
            "Tentativa de upload",
            extra={
                **base_extra,
                "attempt": current_attempt,
                "max_retries": max_retries,
            },
        )

        try:
            result = upload_fn(*args, **kwargs)
            logger.info(
                "Upload concluído com sucesso",
                extra=base_extra,
            )
            return result

        except Exception as exc:
            last_exception = exc
            attempt = current_attempt

            # Verificar tipo de erro
            is_network = _is_network_error(exc)
            is_server, server_code = _is_server_error(exc)
            is_client, client_code = _is_client_error(exc)
            error_type_name = exc.__class__.__name__

            # Erros de cliente (4xx) - sem retry
            if is_client:
                logger.warning(
                    "Upload falhou com erro de cliente (HTTP %s): %s",
                    client_code,
                    exc,
                )
                logger.error(
                    "Falha definitiva no upload",
                    extra={
                        **base_extra,
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "error_type": error_type_name,
                    },
                )
                if _is_permission_error(exc):
                    raise make_server_error("permission", original=exc, status_code=client_code) from exc
                if _is_duplicate_error(exc):
                    raise make_server_error("duplicate", original=exc, status_code=client_code) from exc
                # Outros 4xx - erro genérico sem retry
                raise UploadError(
                    f"Erro ao enviar arquivo (código {client_code}).",
                    detail=f"HTTP {client_code}: {exc}",
                ) from exc

            # Se não é erro de rede nem servidor, não retry
            if not is_network and not is_server:
                logger.warning("Upload falhou com erro não-recuperável: %s", exc)
                logger.error(
                    "Falha definitiva no upload",
                    extra={
                        **base_extra,
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "error_type": error_type_name,
                    },
                )
                raise UploadError(
                    "Ocorreu um erro inesperado ao enviar o arquivo.",
                    detail=str(exc),
                ) from exc

            # Verificar se ainda temos retries
            if attempt > max_retries:
                break

            logger.warning(
                "Falha de upload, será feito retry",
                extra={
                    **base_extra,
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "error_type": error_type_name,
                },
            )

            # Calcular delay com backoff exponencial
            delay = min(backoff_base * (2 ** (attempt - 1)), backoff_max)
            # Adicionar jitter para evitar thundering herd
            jitter_amount = delay * jitter * random.random()  # nosec B311
            delay += jitter_amount

            error_type = "rede" if is_network else f"servidor (HTTP {server_code})"
            logger.info(
                "Upload tentativa %d/%d falhou (%s). Retry em %.1fs...",
                attempt,
                max_retries + 1,
                error_type,
                delay,
            )

            # Callback de retry (para UI mostrar "Tentando novamente...")
            if on_retry:
                try:
                    on_retry(attempt, exc, delay)
                except Exception as cb_exc:  # noqa: BLE001
                    logger.debug("Erro no callback on_retry: %s", cb_exc)

            _sleep(delay)

    # Todas as tentativas falharam
    if last_exception is None:
        raise RuntimeError("upload_with_retry terminou sem exceção registrada; verifique os parâmetros de retry.")

    logger.error(
        "Falha definitiva no upload",
        extra={
            **base_extra,
            "attempt": attempt,
            "max_retries": max_retries,
            "error_type": last_exception.__class__.__name__,
        },
    )

    if _is_network_error(last_exception):
        raise make_network_error("network", original=last_exception) from last_exception
    else:
        _, code = _is_server_error(last_exception)
        raise make_server_error("server", original=last_exception, status_code=code) from last_exception


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
