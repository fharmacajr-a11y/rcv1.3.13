from __future__ import annotations

import random
import socket
import time
from typing import Callable, Iterable, Tuple, Type

try:  # pragma: no cover - dependências opcionais em runtime
    import httpcore
    import httpx
except Exception:  # pragma: no cover
    httpx = None
    httpcore = None


def _collect_default_excs() -> Tuple[Type[BaseException], ...]:
    candidates: Iterable[Type[BaseException] | None] = (
        getattr(socket, "error", None),
        Exception,
        getattr(httpx, "ReadError", None) if httpx else None,
        getattr(httpx, "ConnectError", None) if httpx else None,
        getattr(httpx, "RemoteProtocolError", None) if httpx else None,
        getattr(httpcore, "ReadError", None) if httpcore else None,
        getattr(httpcore, "WriteError", None) if httpcore else None,
    )
    filtered = []
    for exc in candidates:
        if exc and isinstance(exc, type) and issubclass(exc, BaseException):
            filtered.append(exc)
    return tuple(filtered) or (Exception,)


DEFAULT_EXCS: Tuple[Type[BaseException], ...] = _collect_default_excs()


def retry_call(
    fn: Callable,
    *args,
    tries: int = 3,
    backoff: float = 0.6,
    jitter: float = 0.2,
    exceptions: Tuple[Type[BaseException], ...] = DEFAULT_EXCS,
    **kwargs,
):
    """Executa fn com tentativas e backoff exponencial simples."""
    attempt = 0
    while True:
        try:
            return fn(*args, **kwargs)
        except exceptions as exc:
            attempt += 1
            # WinError 10035 é transitório; re-tentar
            if attempt >= tries:
                raise
            sleep = (backoff**attempt) + random.uniform(0, jitter)
            time.sleep(sleep)
