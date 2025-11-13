# infra/net_session.py
"""
Helper de sessão requests com retry e timeout padronizados.

Baseado em:
- urllib3.Retry: https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry
- requests.Session: https://requests.readthedocs.io/en/latest/user/advanced/#session-objects
- HTTPAdapter: https://requests.readthedocs.io/en/latest/user/advanced/#transport-adapters
"""

from __future__ import annotations

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Timeout padrão: (connect, read) em segundos
# connect: tempo para estabelecer conexão
# read: tempo para receber resposta após conectar
DEFAULT_TIMEOUT = (5, 20)


class TimeoutHTTPAdapter(HTTPAdapter):
    """
    HTTPAdapter que garante timeout em todas as requisições.

    Sem timeout explícito, requests não expira conexões.
    Referência: https://requests.readthedocs.io/en/latest/user/advanced/#timeouts
    """

    def __init__(self, *args, timeout=DEFAULT_TIMEOUT, **kwargs):
        self._timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        """Garante timeout mesmo se o caller esquecer."""
        kwargs.setdefault("timeout", self._timeout)
        return super().send(request, **kwargs)


def make_session() -> Session:
    """
    Cria Session com retry automático e timeout.

    Retry:
    - total=3: até 3 tentativas totais
    - backoff_factor=0.5: espera 0.5s, 1.0s, 2.0s entre tentativas (exponencial)
    - allowed_methods: apenas métodos idempotentes (GET, HEAD, PUT, DELETE, OPTIONS, TRACE)
    - status_forcelist: retenta em 413, 429 (rate limit), 500, 502, 503, 504
    - respect_retry_after_header=True: respeita header Retry-After do servidor

    Timeout:
    - (5, 20): 5s para conectar, 20s para ler resposta
    - Aplicado automaticamente em todas as requisições via TimeoutHTTPAdapter

    Returns:
        Session configurada com retry e timeout

    Referências:
    - urllib3.Retry: https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry
    - Backoff: backoff_factor * 2**retries (com jitter opcional)
    - allowed_methods: apenas idempotentes por segurança (não retenta POST/PATCH por padrão)
    """
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,  # 0.5s, 1.0s, 2.0s entre tentativas
        allowed_methods=Retry.DEFAULT_ALLOWED_METHODS,  # GET, HEAD, PUT, DELETE, OPTIONS, TRACE
        status_forcelist=(
            413,
            429,
            500,
            502,
            503,
            504,
        ),  # 413=Payload, 429=Rate limit, 5xx=Server error
        raise_on_status=False,  # Não lança exceção em status HTTP (deixa caller decidir)
        respect_retry_after_header=True,  # Respeita Retry-After do servidor
    )

    adapter = TimeoutHTTPAdapter(max_retries=retry, timeout=DEFAULT_TIMEOUT)

    session = Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


__all__ = ["make_session", "DEFAULT_TIMEOUT", "TimeoutHTTPAdapter"]
