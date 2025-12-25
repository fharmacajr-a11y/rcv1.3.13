# -*- coding: utf-8 -*-
"""
DEPRECATED: Use src.modules.hub.helpers.session (mantido para compatibilidade).

ORG-003: Helpers de sessão foram consolidados em hub/helpers/session.py.
Este arquivo permanece como shim de compatibilidade para não quebrar imports externos.

Para novos códigos, importe diretamente de:
    from src.modules.hub.helpers.session import ...
"""

from __future__ import annotations

# Re-exports do novo local (ORG-003)
from ..helpers.session import (
    calculate_retry_delay_ms,
    extract_email_prefix,
    format_author_fallback,
    is_auth_ready,
    should_skip_refresh_by_cooldown,
)

__all__ = [
    "is_auth_ready",
    "extract_email_prefix",
    "format_author_fallback",
    "should_skip_refresh_by_cooldown",
    "calculate_retry_delay_ms",
]
