# -*- coding: utf-8 -*-
"""Controllers para o módulo HUB.

Controllers headless que encapsulam lógica de ações de usuário,
sem dependências de Tkinter.
"""

from __future__ import annotations

from src.modules.hub.controllers.dashboard_actions import (
    DashboardActionController,
    HubNavigatorProtocol,
)
from src.modules.hub.controllers.notes_controller import (
    NotesController,
    NotesGatewayProtocol,
)
from src.modules.hub.controllers.quick_actions_controller import (
    HubQuickActionsNavigatorProtocol,
    QuickActionsController,
)

__all__ = [
    "DashboardActionController",
    "HubNavigatorProtocol",
    "NotesController",
    "NotesGatewayProtocol",
    "QuickActionsController",
    "HubQuickActionsNavigatorProtocol",
]
