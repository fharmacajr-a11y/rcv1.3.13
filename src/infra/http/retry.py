from __future__ import annotations

import random
import socket
import time
from typing import Any, Callable, Final, TypeVar
from collections.abc import Iterable

# Type aliases
ExceptionTuple = tuple[type[BaseException], ...]

# Type variable for preserving return type
T = TypeVar("T")

try:  # pragma: no cover - dependências opcionais em runtime
    import httpcore
    import httpx
except Exception:  # pragma: no cover
    httpx = None
    httpcore = None


def _collect_default_excs() -> ExceptionTuple:
    """Coleta exceções padrão para retry baseadas em disponibilidade de módulos.

    Returns:
        Tupla de classes de exceção disponíveis no runtime (socket, httpx, httpcore)

    Note:
        Fallback para (Exception,) caso nenhuma exceção específica esteja disponível
    """
    candidates: Iterable[type[BaseException] | None] = (
        getattr(socket, "error", None),
        Exception,
        getattr(httpx, "ReadError", None) if httpx else None,
        getattr(httpx, "ConnectError", None) if httpx else None,
        getattr(httpx, "RemoteProtocolError", None) if httpx else None,
        getattr(httpcore, "ReadError", None) if httpcore else None,
        getattr(httpcore, "WriteError", None) if httpcore else None,
    )
    filtered: list[type[BaseException]] = []
    for exc in candidates:
        if exc and isinstance(exc, type) and issubclass(exc, BaseException):
            filtered.append(exc)
    return tuple(filtered) or (Exception,)


DEFAULT_EXCS: Final[ExceptionTuple] = _collect_default_excs()


def retry_call(
    fn: Callable[..., T],
    *args: Any,
    tries: int = 3,
    backoff: float = 0.6,
    jitter: float = 0.2,
    exceptions: ExceptionTuple = DEFAULT_EXCS,
    **kwargs: Any,
) -> T:
    """Executa função com tentativas e backoff exponencial simples.

    Args:
        fn: Função a ser executada com retry
        *args: Argumentos posicionais para fn
        tries: Número máximo de tentativas (padrão: 3)
        backoff: Fator de backoff exponencial em segundos (padrão: 0.6)
        jitter: Jitter aleatório máximo adicionado ao backoff (padrão: 0.2)
        exceptions: Tupla de exceções que disparam retry (padrão: DEFAULT_EXCS)
        **kwargs: Argumentos nomeados para fn

    Returns:
        Retorno de fn (tipo preservado via TypeVar)

    Raises:
        Exception: Propaga exceção da última tentativa se todas falharem

    Example:
        >>> result = retry_call(requests.get, "http://example.com", tries=5)
        >>> data = retry_call(lambda: api.fetch(), backoff=1.0, jitter=0.5)

    Note:
        - Backoff: sleep = (backoff ** attempt) + random.uniform(0, jitter)
        - WinError 10035 (WSAEWOULDBLOCK) é transitório; sempre re-tenta
        - Primeira tentativa não tem delay (attempt=0 falha → attempt=1 com sleep)
    """
    attempt: int = 0
    while True:
        try:
            return fn(*args, **kwargs)
        except exceptions:
            attempt += 1
            # WinError 10035 é transitório; re-tentar
            if attempt >= tries:
                raise
            # jitter de retry; n?o usado como RNG criptogr?fico
            sleep: float = (backoff**attempt) + random.uniform(0, jitter)  # nosec B311
            time.sleep(sleep)
