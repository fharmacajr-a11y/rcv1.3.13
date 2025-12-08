# -*- coding: utf-8 -*-
# pyright: strict, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false, reportUntypedBaseClass=false, reportPrivateUsage=false

"""Main screen frame extracted from app_gui (clients list).

Este módulo serve como façade para MainScreenFrame, que foi dividido em:
- main_screen_frame.py: Classe principal, ciclo de vida, wiring
- main_screen_events.py: Handlers de eventos (treeview, toolbar, status)
- main_screen_dataflow.py: Carregamento, filtros, dataflow
- main_screen_batch.py: Operações em lote (batch delete/restore/export)
"""

from __future__ import annotations

from src.modules.clientes.views.main_screen_constants import (
    PICK_MODE_BANNER_TEXT,
    PICK_MODE_CANCEL_TEXT,
    PICK_MODE_SELECT_TEXT,
)
from src.modules.clientes.views.main_screen_frame import MainScreenFrame
from src.modules.clientes.views.main_screen_helpers import (
    DEFAULT_ORDER_LABEL,
    ORDER_CHOICES,
)

__all__ = [
    "MainScreenFrame",
    "DEFAULT_ORDER_LABEL",
    "ORDER_CHOICES",
    "PICK_MODE_BANNER_TEXT",
    "PICK_MODE_CANCEL_TEXT",
    "PICK_MODE_SELECT_TEXT",
]
