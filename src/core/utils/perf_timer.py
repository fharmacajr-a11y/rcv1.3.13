# -*- coding: utf-8 -*-
"""Performance timer para diagnosticar gargalos de performance.

Context manager que mede tempo de execução de blocos críticos.
Habilitado via ENV RC_PROFILE_STARTUP=1.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Generator

# Cache para verificação de ENV (evitar múltiplas chamadas)
# Não usar maiúsculas para variáveis mutáveis (Pyright warning)
_profiling_enabled: bool | None = None


def is_profiling_enabled() -> bool:
    """Verifica se profiling está habilitado via ENV.

    Returns:
        True se RC_PROFILE_STARTUP=1, False caso contrário
    """
    global _profiling_enabled
    if _profiling_enabled is None:
        _profiling_enabled = os.getenv("RC_PROFILE_STARTUP", "0") == "1"
    return _profiling_enabled


@contextmanager
def perf_timer(
    name: str,
    logger: logging.Logger,
    threshold_ms: float = 50.0,
    level: str = "info",
) -> Generator[None, None, None]:
    """Context manager para medir performance de blocos críticos.

    Args:
        name: Nome identificador do bloco (ex: "hub.load_recent_activity")
        logger: Logger para emitir métricas
        threshold_ms: Threshold em ms. Se ultrapassar, log em WARNING (padrão 50ms)
        level: Nível de log padrão ("info" ou "debug")

    Yields:
        None

    Example:
        >>> with perf_timer("startup.bootstrap", logger):
        ...     bootstrap_app()
        # Se RC_PROFILE_STARTUP=1:
        # INFO: [PERF] startup.bootstrap = 120ms
    """
    # Se profiling desabilitado, não fazer nada
    if not is_profiling_enabled():
        yield
        return

    start = time.monotonic()
    try:
        yield
    finally:
        elapsed_ms = (time.monotonic() - start) * 1000

        # Determinar nível de log
        if elapsed_ms > threshold_ms:
            log_level = logging.WARNING
            prefix = "⚠️ [PERF-SLOW]"
        else:
            log_level = logging.INFO if level == "info" else logging.DEBUG
            prefix = "⏱️ [PERF]"

        # Emitir métrica
        logger.log(log_level, f"{prefix} {name} = {elapsed_ms:.0f}ms")


class PerfTimer:
    """Classe auxiliar para usar perf_timer como decorator ou context manager.

    Example:
        >>> timer = PerfTimer("operation", logger)
        >>> with timer:
        ...     do_work()
    """

    def __init__(
        self,
        name: str,
        logger: logging.Logger,
        threshold_ms: float = 50.0,
        level: str = "info",
    ) -> None:
        """Inicializa timer.

        Args:
            name: Nome identificador
            logger: Logger
            threshold_ms: Threshold para WARNING
            level: Nível padrão de log
        """
        self.name = name
        self.logger = logger
        self.threshold_ms = threshold_ms
        self.level = level

    def __enter__(self) -> PerfTimer:
        """Entrada do context manager."""
        self._cm = perf_timer(self.name, self.logger, self.threshold_ms, self.level)
        self._cm.__enter__()
        return self

    def __exit__(self, *args) -> None:
        """Saída do context manager."""
        self._cm.__exit__(*args)
