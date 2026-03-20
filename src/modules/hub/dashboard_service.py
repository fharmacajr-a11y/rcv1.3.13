# -*- coding: utf-8 -*-
"""Dashboard service facade (compatibility shim).

DEPRECATED: Este módulo é um facade de compatibilidade.
Use: from src.modules.hub.dashboard.service import ...

Este arquivo existe para manter imports legados funcionando.
A implementação real está em src.modules.hub.dashboard.service.
"""

from __future__ import annotations

# Re-exports estáticos do módulo real (substitui importlib.import_module
# dinâmico que era invisível ao PyInstaller — causa do crash no EXE).
from src.modules.hub.dashboard.service import (  # noqa: F401
    DashboardSnapshot,
    _due_badge,
    _format_due_br,
    _get_first_day_of_month,
    _get_last_day_of_month,
    _parse_due_date_iso,
    _parse_timestamp,
    due_badge,
    format_due_br,
    get_dashboard_snapshot,
    get_first_day_of_month,
    get_last_day_of_month,
    parse_due_date_iso,
    parse_timestamp,
)
