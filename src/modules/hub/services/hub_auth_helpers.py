# -*- coding: utf-8 -*-
"""DEPRECATED: Use src.modules.hub.helpers.session (mantido para compatibilidade).

ORG-003: Helpers de auth foram consolidados em hub/helpers/session.py.
Este arquivo permanece como shim de compatibilidade para não quebrar imports externos.

Para novos códigos, importe diretamente de:
    from src.modules.hub.helpers.session import ...
"""

from __future__ import annotations

# Re-exports do novo local (ORG-003)
from ..helpers.session import (
    get_app_from_widget,
    get_email_safe_from_widget,
    get_org_id_safe_from_widget,
    get_user_id_safe_from_widget,
    is_online_from_widget,
)

__all__ = [
    "get_app_from_widget",
    "get_org_id_safe_from_widget",
    "get_email_safe_from_widget",
    "get_user_id_safe_from_widget",
    "is_online_from_widget",
]
