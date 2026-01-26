from __future__ import annotations

import logging
from typing import Optional

from src.config.environment import env_str
from src.core.logs.filters import RedactSensitiveData

_configured = False


def configure_logging(level: Optional[str] = None) -> None:
    global _configured
    if _configured:
        return

    level_name = (level or env_str("LOG_LEVEL") or "INFO").upper()
    lvl = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=lvl,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Adiciona filtro de redação de dados sensíveis
    # Baseado em OWASP Secrets Management Cheat Sheet
    root_logger = logging.getLogger()
    root_logger.addFilter(RedactSensitiveData())

    _configured = True
