from __future__ import annotations

import atexit
import logging
import threading
from typing import Final

import httpx
from httpx import Timeout

_log = logging.getLogger(__name__)

# Type aliases
HttpClient = httpx.Client
HttpResponse = httpx.Response

# Timeout para operações leves (health, auth, RPC simples)
HTTPX_TIMEOUT_LIGHT: Final[Timeout] = Timeout(connect=10.0, read=30.0, write=30.0, pool=None)

# Timeout para operações pesadas (upload/download de arquivos)
# storage3 usa esse valor em segundos via storage_client_timeout=180
HTTPX_TIMEOUT_HEAVY: Final[Timeout] = Timeout(connect=15.0, read=180.0, write=180.0, pool=None)

# --- Compatibilidade: alias para código legado ---
# Mantém o nome antigo apontando para LIGHT (semântica original)
HTTPX_TIMEOUT: Final[Timeout] = HTTPX_TIMEOUT_LIGHT

# Cliente padrão usa timeout leve (a maioria das operações)
HTTPX_CLIENT: Final[HttpClient] = httpx.Client(
    http2=False,  # manter compat com PR-H1
    timeout=HTTPX_TIMEOUT_LIGHT,
)

# ------------------------------------------------------------------
# Lifecycle — cleanup idempotente via atexit
# ------------------------------------------------------------------

_close_lock = threading.Lock()
_client_closed: bool = False


def close_http_client() -> None:
    """Fecha HTTPX_CLIENT de forma idempotente.

    - Segura para chamar múltiplas vezes: segunda chamada é no-op.
    - Registrada em atexit para rodar no encerramento normal do processo.
    - Pode também ser chamada explicitamente no shutdown do app.
    - Exceções são suprimidas e logadas em DEBUG para não atrapalhar o exit.
    """
    global _client_closed
    with _close_lock:
        if _client_closed:
            return
        _client_closed = True
    try:
        HTTPX_CLIENT.close()
        _log.debug("close_http_client: HTTPX_CLIENT fechado com sucesso.")
    except Exception as exc:  # noqa: BLE001
        _log.debug("close_http_client: erro ao fechar HTTPX_CLIENT: %s", exc)


atexit.register(close_http_client)


def get_http_client() -> HttpClient:
    """Retorna o singleton HTTPX_CLIENT.

    Alias funcional para uso explícito; preserva compatibilidade com
    código que já importa ``HTTPX_CLIENT`` diretamente.
    """
    return HTTPX_CLIENT


# Exportação pública explícita
__all__ = [
    "HTTPX_CLIENT",
    "HTTPX_TIMEOUT",  # alias compatível (legado)
    "HTTPX_TIMEOUT_LIGHT",  # novo (30s)
    "HTTPX_TIMEOUT_HEAVY",  # novo (60s)
    "Timeout",
    "close_http_client",
    "get_http_client",
]
