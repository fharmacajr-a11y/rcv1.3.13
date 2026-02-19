"""Constantes para callbacks de dashboard do Hub.

ORG-010: Constantes extraídas de hub_dashboard_callbacks.py.
ORG-011: Convertido em wrapper que re-exporta de hub_messages.py para
         centralizar manutenção e evitar duplicação entre módulos do Hub.

Este módulo mantém compatibilidade com código existente que importa daqui,
mas as definições reais estão em hub_messages.py.
"""

from src.modules.hub.views.hub_messages import (
    BANNER_CLIENT_PICK_OBLIGATIONS,
    MSG_ACTIVITY_VIEW_COMING_SOON,
    MSG_APP_NOT_FOUND,
    MSG_ERROR_OPEN_DIALOG,
    MSG_ERROR_OPEN_VIEW,
    MSG_ERROR_PROCESS_ACTION,
    MSG_ERROR_PROCESS_SELECTION,
    MSG_ERROR_START_FLOW,
    MSG_LOGIN_REQUIRED_OBLIGATIONS,
    MSG_LOGIN_REQUIRED_TASKS,
    TITLE_AUTH_REQUIRED,
    TITLE_ERROR,
    TITLE_IN_DEVELOPMENT,
)

__all__ = [
    "TITLE_AUTH_REQUIRED",
    "TITLE_ERROR",
    "TITLE_IN_DEVELOPMENT",
    "MSG_LOGIN_REQUIRED_TASKS",
    "MSG_LOGIN_REQUIRED_OBLIGATIONS",
    "MSG_APP_NOT_FOUND",
    "MSG_ERROR_OPEN_DIALOG",
    "MSG_ERROR_START_FLOW",
    "MSG_ERROR_OPEN_VIEW",
    "MSG_ERROR_PROCESS_SELECTION",
    "MSG_ERROR_PROCESS_ACTION",
    "MSG_ACTIVITY_VIEW_COMING_SOON",
    "BANNER_CLIENT_PICK_OBLIGATIONS",
]
