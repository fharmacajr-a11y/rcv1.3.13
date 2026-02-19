"""Constantes para HubNotesView.

ORG-009: Constantes extraídas de hub_notes_view.py.
ORG-011: Convertido em wrapper que re-exporta de hub_messages.py para
         centralizar manutenção e evitar duplicação entre módulos do Hub.

Este módulo mantém compatibilidade com código existente que importa daqui,
mas as definições reais estão em hub_messages.py.
"""

from src.modules.hub.views.hub_messages import (
    MSG_EMPTY_DEFAULT,
    MSG_ERROR_PREFIX,
    MSG_LOADING,
)

__all__ = [
    "MSG_LOADING",
    "MSG_EMPTY_DEFAULT",
    "MSG_ERROR_PREFIX",
]
