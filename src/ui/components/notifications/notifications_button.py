# -*- coding: utf-8 -*-
"""Componente de botão de notificações com badge."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, Optional

import ttkbootstrap as tb

from src.utils.resource_path import resource_path

if TYPE_CHECKING:
    from tkinter import PhotoImage

_log = logging.getLogger(__name__)

# Caminhos do ícone de sino (sem acento preferencial, com acento fallback)
_ICON_PATHS = [
    "assets/notificacoes/sino.png",
    "assets/notificações/sino.png",
]
# Tamanho alvo do ícone em pixels
_ICON_TARGET_SIZE = 16
# Tamanho do container (para manter layout estável)
_CONTAINER_SIZE = 32


class NotificationsButton(ttk.Frame):
    """Botão de notificações com badge de contador.

    Responsável apenas por:
    - Exibir botão de notificações (ícone sino ou fallback 🔔)
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
        self._icon_img: Optional[PhotoImage] = None

        # Fixar tamanho do container para não encolher topbar
        self.configure(width=_CONTAINER_SIZE, height=_CONTAINER_SIZE)
        self.pack_propagate(False)

        # Construir UI
        self._build_ui()

    def _load_icon(self) -> Optional[tk.PhotoImage]:
        """Carrega ícone PNG do sino com fallback.

        Tenta múltiplos caminhos (sem acento preferencial, com acento fallback).
        Redimensiona dinamicamente para _ICON_TARGET_SIZE se necessário.

        Returns:
            PhotoImage se sucesso, None se falhar
        """
        for icon_path in _ICON_PATHS:
            try:
                icon_full_path = resource_path(icon_path)
                img = tk.PhotoImage(file=icon_full_path)

                # Escala dinâmica: só reduzir se maior que target
                w, h = img.width(), img.height()
                target = _ICON_TARGET_SIZE

                if w > target or h > target:
                    fx = max(1, w // target)
                    fy = max(1, h // target)
                    img = img.subsample(fx, fy)
                    _log.debug(
                        "[NotificationsButton] Ícone redimensionado: %dx%d -> %dx%d (subsample %d,%d)",
                        w,
                        h,
                        img.width(),
                        img.height(),
                        fx,
                        fy,
                    )
                else:
                    _log.debug("[NotificationsButton] Ícone já no tamanho adequado: %dx%d", w, h)

                _log.debug("[NotificationsButton] Ícone carregado: %s", icon_full_path)
                return img

            except Exception as exc:  # noqa: BLE001
                _log.debug("[NotificationsButton] Falha ao carregar %s: %s", icon_path, exc)
                continue

        _log.debug("[NotificationsButton] Fallback para emoji 🔔")
        return None

    def _build_ui(self) -> None:
        """Constrói a interface do botão."""
        # Tentar carregar ícone PNG
        self._icon_img = self._load_icon()

        # Botão de notificações (ícone ou fallback)
        if self._icon_img:
            self.btn_notifications = tb.Button(
                self,
                image=self._icon_img,
                text="",
                command=self._handle_click,
                bootstyle="link",
                takefocus=False,
            )
        else:
            self.btn_notifications = tb.Button(
                self,
                text="🔔",
                command=self._handle_click,
                bootstyle="info",
                width=3,
            )
        # Centralizar botão no container usando place
        self.btn_notifications.place(relx=0.5, rely=0.5, anchor="center")

        # Badge com contador (posicionado no canto superior direito)
        self._lbl_badge = ttk.Label(
            self,
            text="",
            foreground="white",
            background="#dc3545",
            font=("Arial", 8, "bold"),
            padding=(3, 0),
        )
        # Badge começa oculto
        # Não usar pack/grid - será posicionado com place quando necessário

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
            # Mostrar badge no canto superior direito
            self._lbl_badge.configure(text=str(count))
            self._lbl_badge.place(relx=1.0, rely=0.0, anchor="ne", x=-2, y=2)
        else:
            # Ocultar badge
            self._lbl_badge.place_forget()

    def get_count(self) -> int:
        """Retorna contador atual.

        Returns:
            Número de notificações não lidas
        """
        return self._count
