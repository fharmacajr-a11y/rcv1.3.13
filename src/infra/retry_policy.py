# infra/retry_policy.py
"""Módulo unificado de retry com backoff exponencial + jitter + cap.

PR-10 — Centraliza TODA a lógica de retry do projeto em UM único local.

Política padrão
~~~~~~~~~~~~~~~~
- max_attempts: 3 tentativas
- base_delay: 0.4 s
- max_delay: 8.0 s  (cap exponencial)
- jitter: até 0.15 s (uniform, via ``secrets`` para evitar B311)

Backoff: ``delay = min(base_delay × 2^(attempt-1), max_delay) + jitter``

Somente erros classificados como transitórios por ``is_transient_error()``
são re-tentados. Erros não-transitórios propagam imediatamente.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any, Callable, Final, TypeVar

T = TypeVar("T")

logger: Final = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceções transitórias conhecidas (importadas de forma defensiva)
# ---------------------------------------------------------------------------
_TRANSIENT_TYPES: tuple[type[BaseException], ...] = ()

try:  # pragma: no cover — dependências opcionais
    import httpx

    _TRANSIENT_TYPES += (
        httpx.ReadError,
        httpx.WriteError,
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.RemoteProtocolError,
    )
except Exception:  # pragma: no cover
    pass

try:  # pragma: no cover
    import httpcore

    _TRANSIENT_TYPES += (
        httpcore.ReadError,
        httpcore.WriteError,
    )
except Exception:  # pragma: no cover
    pass

# Erros de socket / rede do Python
import socket  # noqa: E402

_TRANSIENT_TYPES += (socket.timeout, ConnectionError, TimeoutError)

# Palavras-chave de erros 5xx / transitórios em mensagens de exceção
_TRANSIENT_MSG_KEYWORDS: Final[tuple[str, ...]] = (
    "502",
    "503",
    "504",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
    "internal server",
    "5xx",
    "temporarily unavailable",
    "temporary failure",
    "connection",
    "timeout",
    "network unreachable",
    "rate limit",
    "too many requests",
    "429",
)


# ---------------------------------------------------------------------------
# Classificador universal de erros transitórios
# ---------------------------------------------------------------------------
def is_transient_error(exc: Exception) -> bool:
    """Retorna ``True`` se *exc* é um erro transitório de rede/servidor.

    Regras:
    - ``OSError`` com ``winerror == 10035`` (WSAEWOULDBLOCK) → transitório
    - ``OSError`` sem ``winerror`` ou com outro código → **não** transitório
    - Tipos em ``_TRANSIENT_TYPES`` → transitório
    - Mensagem contém keyword de 5xx / rate-limit / rede → transitório
    - ``errno`` EWOULDBLOCK / EAGAIN → transitório
    """
    # OSError especial: WinError 10035 é transitório; outros não.
    if isinstance(exc, OSError):
        winerror = getattr(exc, "winerror", None)
        if winerror == 10035:
            return True
        # socket.error é subclasse de OSError — aceitar se for tipo transitório
        if isinstance(exc, (socket.timeout, ConnectionError, TimeoutError)):
            return True
        # errno EWOULDBLOCK / EAGAIN
        import errno as _errno

        if hasattr(exc, "errno") and getattr(exc, "errno") in (_errno.EWOULDBLOCK, _errno.EAGAIN):
            return True
        # Outros OSError (permissão, arquivo não encontrado…) — NÃO transitório
        return False

    # Tipos conhecidos
    if isinstance(exc, _TRANSIENT_TYPES):
        return True

    # Heurística textual
    msg = str(exc).lower()
    return any(kw in msg for kw in _TRANSIENT_MSG_KEYWORDS)


# ---------------------------------------------------------------------------
# Cálculo de delay
# ---------------------------------------------------------------------------
def calculate_delay(attempt: int, base_delay: float, max_delay: float, jitter: float) -> float:
    """Calcula delay com backoff exponencial + cap + jitter.

    Args:
        attempt: Número da tentativa (1-based, indica a tentativa que FALHOU).
        base_delay: Delay base em segundos.
        max_delay: Cap máximo em segundos.
        jitter: Jitter máximo em segundos (uniform [0, jitter)).

    Returns:
        Delay em segundos.
    """
    exp = min(base_delay * (2 ** (attempt - 1)), max_delay)
    # jitter via secrets para evitar B311 (Bandit)
    jitter_ms = secrets.randbelow(max(int(jitter * 10_000), 1))
    return exp + jitter_ms / 10_000


# ---------------------------------------------------------------------------
# Função principal de retry
# ---------------------------------------------------------------------------
def retry_call(
    fn: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 0.4,
    max_delay: float = 8.0,
    jitter: float = 0.15,
    is_transient: Callable[[Exception], bool] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    **kwargs: Any,
) -> T:
    """Executa *fn* com retry, backoff exponencial, jitter e cap.

    Apenas exceções classificadas como transitórias são retentadas.
    Erros não-transitórios propagam imediatamente (sem sleep, sem retry).

    Args:
        fn: Callable a executar.
        *args: Argumentos posicionais para *fn*.
        max_attempts: Total de tentativas (incluindo a primeira). Padrão 3.
        base_delay: Delay base para backoff exponencial (segundos).
        max_delay: Cap máximo de delay (segundos).
        jitter: Jitter máximo adicionado ao delay (segundos).
        is_transient: Classificador customizado. Se ``None``, usa
            ``is_transient_error()`` (padrão universal).
        sleep_fn: Função de sleep (injetável para testes).
        on_retry: Callback ``(attempt, exception, delay)`` chamado antes
            de cada retry. Exceções no callback são engolidas em log.
        **kwargs: Argumentos nomeados para *fn*.

    Returns:
        Retorno de *fn* (tipo preservado via TypeVar).

    Raises:
        Exception: Última exceção após esgotar tentativas, ou exceção
            não-transitória propagada imediatamente.
    """
    classifier = is_transient or is_transient_error

    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            # Não-transitório ou última tentativa → propaga
            if not classifier(exc) or attempt >= max_attempts:
                raise

            delay = calculate_delay(attempt, base_delay, max_delay, jitter)

            logger.debug(
                "retry attempt %d/%d failed (%s: %s). retrying in %.2fs",
                attempt,
                max_attempts,
                type(exc).__name__,
                str(exc)[:120],
                delay,
            )

            if on_retry is not None:
                try:
                    on_retry(attempt, exc, delay)
                except Exception as cb_exc:  # noqa: BLE001
                    logger.debug("on_retry callback error: %s", cb_exc)

            sleep_fn(delay)

    # Não deveria chegar aqui; guard defensivo
    raise RuntimeError("retry_call: todas as tentativas esgotadas sem exceção registrada.")  # pragma: no cover


__all__ = [
    "calculate_delay",
    "is_transient_error",
    "retry_call",
]
