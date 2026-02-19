# -*- coding: utf-8 -*-
"""Performance measurement helpers for startup/UI diagnostics.

BUGFIX-UX-STARTUP-HUB-001: Criado para instrumentação leve de performance
durante startup/inicialização de componentes UI complexos.

Uso:
    import os
    from time import perf_counter
    from src.utils.perf import perf_mark

    if os.getenv("RC_DEBUG_STARTUP_UI") == "1":
        t0 = perf_counter()
        # ... código a medir ...
        perf_mark("Descrição da operação", t0, logger)

Design:
- Zero overhead quando RC_DEBUG_STARTUP_UI != "1"
- Log simples com tempo decorrido em segundos
- Não interfere com código de produção
"""

from __future__ import annotations

import logging
from typing import Optional


def perf_mark(label: str, t0: float, logger: Optional[logging.Logger] = None) -> None:
    """Marca tempo decorrido desde t0 (perf_counter()).

    Args:
        label: Descrição da operação medida
        t0: Timestamp inicial (de perf_counter())
        logger: Logger para output (usa root logger se None)

    Exemplo:
        >>> from time import perf_counter
        >>> t0 = perf_counter()
        >>> # ... código ...
        >>> perf_mark("Build UI", t0, log)
        [PERF] Build UI 0.123s
    """
    from time import perf_counter

    elapsed = perf_counter() - t0
    log = logger or logging.getLogger(__name__)
    log.info("[PERF] %s %.3fs", label, elapsed)
