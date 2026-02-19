# -*- coding: utf-8 -*-
"""Helpers puros (sem UI) para o HubScreen.

ORG-004: Extraído de hub_screen.py para reduzir complexidade.
Contém funções utilitárias puras sem dependências de tkinter.
"""

from __future__ import annotations

from datetime import datetime, timezone

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


def get_local_timezone():
    """Obtém timezone local com fallback seguro.

    Returns:
        tzinfo: Timezone local, ou UTC como fallback
    """
    try:
        import tzlocal  # type: ignore[import-not-found]

        return tzlocal.get_localzone()
    except Exception:
        # Fallback: usa tzinfo do sistema
        try:
            return datetime.now().astimezone().tzinfo
        except Exception:
            return timezone.utc
