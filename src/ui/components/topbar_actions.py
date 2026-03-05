# -*- coding: utf-8 -*-
"""Componente de ações da TopBar.

DESATIVADO v1.5.99: Notificações removidas (eliminado para resolver ReadError no shutdown).
TopbarActions agora é um frame vazio — mantido para compatibilidade de layout.
"""

from __future__ import annotations

from src.ui.ctk_config import ctk

import logging
from typing import Any, Protocol

_log = logging.getLogger(__name__)


class TopbarActionsCallbacks(Protocol):
    """Protocolo de callbacks para ações (mantido para compatibilidade)."""

    def on_notifications_clicked(self) -> None: ...
    def on_mark_all_read(self) -> bool: ...
    def on_delete_notification_for_me(self, notification_id: str) -> bool: ...
    def on_delete_all_notifications_for_me(self) -> bool: ...


class TopbarActions(ctk.CTkFrame):
    """Frame vazio — notificações desativadas v1.5.99.

    Mantém interface pública (no-ops) para não quebrar TopBar/MainWindow.
    """

    def __init__(
        self,
        master,
        callbacks: TopbarActionsCallbacks,  # noqa: ARG002
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        # Nenhum sub-componente criado — frame vazio
        self.btn_notifications = None  # Compatibilidade

    # ===== Métodos públicos (no-ops) =====

    def set_notifications_count(self, count: int) -> None:  # noqa: ARG002
        """NO-OP: Notificações desativadas v1.5.99."""

    def set_notifications_data(
        self,
        notifications: list[dict[str, Any]],  # noqa: ARG002
        mute_callback: Any = None,  # noqa: ARG002
    ) -> None:
        """NO-OP: Notificações desativadas v1.5.99."""
