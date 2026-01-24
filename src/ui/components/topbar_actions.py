# -*- coding: utf-8 -*-
"""Componente de ações da TopBar - compositor para NotificationsButton e NotificationsPopup.

REFATORAÇÃO P2 (Microfase 2 → MF3):
- TopbarActions como compositor de NotificationsButton + NotificationsPopup
- P2-MF3: adiciona controller headless para apresentação de notificações
- UI agora consome ViewModels do controller
"""

from __future__ import annotations

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import SURFACE_DARK

import logging
from typing import Any, Protocol

from src.ui.controllers import TopbarNotificationsController

from .notifications import NotificationsButton, NotificationsPopup

_log = logging.getLogger(__name__)


class TopbarActionsCallbacks(Protocol):
    """Protocolo de callbacks para ações."""

    def on_notifications_clicked(self) -> None:
        """Callback quando usuário clica no botão de notificações."""
        ...

    def on_mark_all_read(self) -> bool:
        """Callback para marcar todas notificações como lidas.

        Returns:
            True se sucesso, False caso contrário
        """
        ...

    def on_delete_notification_for_me(self, notification_id: str) -> bool:
        """Callback para excluir uma notificação (apenas para o usuário atual).

        Args:
            notification_id: ID da notificação a excluir

        Returns:
            True se sucesso, False caso contrário
        """
        ...

    def on_delete_all_notifications_for_me(self) -> bool:
        """Callback para excluir todas notificações (apenas para o usuário atual).

        Returns:
            True se sucesso, False caso contrário
        """
        ...


class TopbarActions(ctk.CTkFrame):
    """Componente compositor de ações da TopBar (lado direito).

    Orquestra:
    - NotificationsButton (botão + badge)
    - NotificationsPopup (popup com treeview)
    """

    def __init__(
        self,
        master,
        callbacks: TopbarActionsCallbacks,
        **kwargs,
    ):
        """Inicializa o componente compositor.

        Args:
            master: Widget pai
            callbacks: Objeto com callbacks de ações
        """
        super().__init__(master, fg_color=SURFACE_DARK, corner_radius=0, **kwargs)
        self._callbacks = callbacks

        # Criar controller headless (MF3)
        self._controller = TopbarNotificationsController(preview_max=120)

        # Criar subcomponentes
        self._button = NotificationsButton(
            self,
            on_click=self._handle_button_click,
        )
        self._button.pack(side="right", padx=(0, 6))

        self._popup = NotificationsPopup(
            parent_widget=self,
            on_mark_all_read=self._handle_mark_all_read,
            on_reload_notifications=self._handle_reload_notifications,
            on_update_count=self._handle_update_count,
            on_delete_selected=self._handle_delete_selected,
            on_delete_all=self._handle_delete_all,
        )

        # Expor botão para compatibilidade
        self.btn_notifications = self._button.btn_notifications

    def _handle_button_click(self) -> None:
        """Handler do clique no botão de notificações."""
        # Alternar popup
        self._popup.toggle()

        # Notificar controller para buscar notificações
        try:
            self._callbacks.on_notifications_clicked()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao executar on_notifications_clicked: %s", exc)

    def _handle_mark_all_read(self) -> bool:
        """Handler para marcar todas notificações como lidas."""
        try:
            return self._callbacks.on_mark_all_read()
        except Exception as exc:  # noqa: BLE001
            _log.exception("Falha ao executar on_mark_all_read: %s", exc)
            return False

    def _handle_reload_notifications(self) -> None:
        """Handler para recarregar notificações."""
        try:
            self._callbacks.on_notifications_clicked()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao recarregar notificações: %s", exc)

    def _handle_update_count(self, count: int) -> None:
        """Handler para atualizar contador no badge."""
        self._button.set_count(count)

    def _handle_delete_selected(self, notification_id: str) -> bool:
        """Handler para excluir notificação selecionada (apenas para o usuário).

        Args:
            notification_id: ID da notificação a excluir

        Returns:
            True se sucesso, False caso contrário
        """
        try:
            return self._callbacks.on_delete_notification_for_me(notification_id)
        except Exception as exc:  # noqa: BLE001
            _log.exception("Falha ao executar on_delete_notification_for_me: %s", exc)
            return False

    def _handle_delete_all(self) -> bool:
        """Handler para excluir todas notificações (apenas para o usuário).

        Returns:
            True se sucesso, False caso contrário
        """
        try:
            return self._callbacks.on_delete_all_notifications_for_me()
        except Exception as exc:  # noqa: BLE001
            _log.exception("Falha ao executar on_delete_all_notifications_for_me: %s", exc)
            return False

    # ===== Métodos públicos (delegam para subcomponentes) =====

    def set_notifications_count(self, count: int) -> None:
        """Atualiza contador de notificações não lidas.

        Args:
            count: Número de notificações não lidas
        """
        self._button.set_count(count)

    def set_notifications_data(
        self,
        notifications: list[dict[str, Any]],
        mute_callback: Any = None,
    ) -> None:
        """Atualiza dados das notificações.

        Args:
            notifications: Lista de notificações (dicts brutos)
            mute_callback: Callback para toggle de mute (recebe bool)
        """
        # Delegar para popup com controller (MF3)
        self._popup.set_notifications_data(
            notifications,
            controller=self._controller,
            mute_callback=mute_callback,
        )

        # Abrir popup se ainda não estiver aberto
        if not self._popup.is_open():
            self._popup.open()
