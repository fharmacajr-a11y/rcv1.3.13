# utils/net_retry.py
from __future__ import annotations
import time
from typing import Callable, TypeVar
from src.core.session.session_guard import SessionGuard

T = TypeVar("T")


def run_cloud_op(op: Callable[[], T], retries: int = 2, base_delay: float = 0.5) -> T:
    """
    Executa operação que chama Supabase com retries + refresh de sessão.
    - Se 401/expiração: tenta SessionGuard.ensure_alive() e repete.
    - Backoff simples: base_delay * (2**tentativa)
    Levanta última exceção se falhar.

    Args:
        op: Função/lambda que executa a operação de rede
        retries: Número de tentativas (padrão: 2)
        base_delay: Delay base em segundos para backoff (padrão: 0.5)

    Returns:
        Resultado da operação

    Raises:
        Última exceção se todas as tentativas falharem

    Exemplo:
        from src.utils.net_retry import run_cloud_op
        from infra.supabase_client import get_supabase

        sb = get_supabase()
        result = run_cloud_op(lambda: sb.storage.from_("bucket").list())
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
    assert last_exc is not None
    raise last_exc
