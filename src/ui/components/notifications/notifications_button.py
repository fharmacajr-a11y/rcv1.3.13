# -*- coding: utf-8 -*-
"""Componente de botão de notificações com badge."""

from __future__ import annotations

import logging
from tkinter import ttk
from typing import Callable, Optional

import ttkbootstrap as tb

_log = logging.getLogger(__name__)


class NotificationsButton(ttk.Frame):
    """Botão de notificações com badge de contador.

    Responsável apenas por:
    - Exibir botão de notificações (sininho 🔔)
    - Mostrar/ocultar badge com contador de não lidas
    """

    def __init__(
        self,
        master,
        on_click: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """Inicializa o botão de notificações.

        Args:
            master: Widget pai
            on_click: Callback para quando usuário clica no botão
        """
        super().__init__(master, **kwargs)
        self._on_click = on_click
        self._count = 0

        # Construir UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Constrói a interface do botão."""
        # Botão de notificações (sininho)
        self.btn_notifications = tb.Button(
            self,
            text="🔔",
            command=self._handle_click,
            bootstyle="info",
            width=3,
        )
        self.btn_notifications.pack(side="left")

        # Badge com contador
        self._lbl_badge = ttk.Label(
            self,
            text="",
            foreground="white",
            background="#dc3545",
            font=("Arial", 8, "bold"),
            padding=(4, 0),
        )
        # Badge começa oculto
        self._lbl_badge.pack_forget()

    def _handle_click(self) -> None:
        """Handler do clique no botão."""
        if callable(self._on_click):
            try:
                self._on_click()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_click: %s", exc)

    def set_count(self, count: int) -> None:
        """Atualiza contador de notificações não lidas.

        Args:
            count: Número de notificações não lidas
        """
        self._count = count

        if count > 0:
            # Mostrar badge com número
            self._lbl_badge.configure(text=str(count))
            self._lbl_badge.pack(side="left", padx=(2, 0))
        else:
            # Ocultar badge
            self._lbl_badge.pack_forget()

    def get_count(self) -> int:
        """Retorna contador atual.

        Returns:
            Número de notificações não lidas
        """
        return self._count
