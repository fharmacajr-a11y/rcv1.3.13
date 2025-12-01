# utils/net_retry.py
from __future__ import annotations

import time
from typing import Callable, TypeVar

from src.core.session.session_guard import SessionGuard

T = TypeVar("T")


def run_cloud_op(op: Callable[[], T], retries: int = 2, base_delay: float = 0.5) -> T:
    """Executa operação Supabase com tentativas extras e refresh de sessão.

    - Para erros de sessão (ex.: 401/expiração), chama SessionGuard.ensure_alive()
      antes de tentar novamente.
    - Backoff simples: base_delay * (2 ** tentativa).
    - Propaga a última exceção se todas as tentativas falharem.

    Args:
        op: Função/lambda que executa a operação de rede.
        retries: Número de tentativas extras (padrão: 2).
        base_delay: Delay base em segundos para o backoff (padrão: 0.5).

    Returns:
        Retorno da operação bem-sucedida.

    Raises:
        Última exceção capturada caso todas as tentativas falhem.
    """
    last_exc: Exception | None = None
    for i in range(retries + 1):
        try:
            if i > 0:
                # entre tentativas, tentar garantir sessão e esperar backoff
                SessionGuard.ensure_alive()
                time.sleep(base_delay * (2 ** (i - 1)))
            return op()
        except Exception as e:
            last_exc = e
            # segue para próxima tentativa
    if last_exc is None:
        raise RuntimeError("run_cloud_op failed without captured exception")
    raise last_exc


__all__ = ["run_cloud_op"]
