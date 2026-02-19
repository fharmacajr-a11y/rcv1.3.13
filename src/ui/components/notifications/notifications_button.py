# -*- coding: utf-8 -*-
"""Componente de botão de notificações com badge.

MICROFASE 24: Migrado para CustomTkinter.
"""

from __future__ import annotations

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn_icon

import logging
from typing import TYPE_CHECKING, Callable, Optional

from PIL import Image

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER
from src.utils.resource_path import resource_path

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

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


class NotificationsButton(ctk.CTkFrame):
    """Botão de notificações com badge de contador.

    Responsável apenas por:
    - Exibir botão de notificações (ícone sino ou fallback 🔔)
    - Mostrar/ocultar badge com contador de não lidas

    MICROFASE 24: Usa CTkButton ao invés de ttkbootstrap.
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
        self._icon_img: Optional[ctk.CTkImage] = None
        self._icon_pil: Optional[PILImage] = None

        # Fixar tamanho do container para não encolher topbar
        self.configure(width=_CONTAINER_SIZE, height=_CONTAINER_SIZE)
        self.pack_propagate(False)

        # Construir UI
        self._build_ui()

    def _load_icon(self) -> Optional[ctk.CTkImage]:
        """Carrega ícone PNG do sino com fallback.

        Tenta múltiplos caminhos (sem acento preferencial, com acento fallback).
        Redimensiona dinamicamente para _ICON_TARGET_SIZE se necessário.

        Returns:
            CTkImage se sucesso, None se falhar
        """
        if not HAS_CUSTOMTKINTER or ctk is None:
            return None

        for icon_path in _ICON_PATHS:
            try:
                icon_full_path = resource_path(icon_path)
                img = Image.open(icon_full_path)

                # Manter referência PIL para evitar GC
                self._icon_pil = img

                # Escala dinâmica: só reduzir se maior que target
                w, h = img.width, img.height
                target = _ICON_TARGET_SIZE

                if w > target or h > target:
                    img = img.copy()
                    img.thumbnail((target, target), Image.Resampling.LANCZOS)
                    self._icon_pil = img
                    _log.debug(
                        "[NotificationsButton] Ícone redimensionado: %dx%d -> %dx%d",
                        w,
                        h,
                        img.width,
                        img.height,
                    )
                else:
                    _log.debug("[NotificationsButton] Ícone já no tamanho adequado: %dx%d", w, h)

                # Criar CTkImage
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                _log.debug("[NotificationsButton] Ícone carregado: %s", icon_full_path)
                return ctk_img

            except Exception as exc:  # noqa: BLE001
                _log.debug("[NotificationsButton] Falha ao carregar %s: %s", icon_path, exc)
                continue

        _log.debug("[NotificationsButton] Fallback para emoji 🔔")
        return None

    def _build_ui(self) -> None:
        """Constrói a interface do botão."""
        if not HAS_CUSTOMTKINTER or ctk is None:
            _log.warning("CustomTkinter não disponível, botão de notificações não criado")
            return

        # Tentar carregar ícone PNG
        # TEMPORÁRIO: desabilitar ícones por problema de pyimage
        # self._icon_img = self._load_icon()
        self._icon_img = None

        # Botão de notificações (emoji como fallback seguro)
        self.btn_notifications = make_btn_icon(
            self,
            text="🔔",
            command=self._handle_click,
            width=28,
            height=28,
        )
        # Centralizar botão no container usando place
        self.btn_notifications.place(relx=0.5, rely=0.5, anchor="center")

        # Badge com contador (posicionado no canto superior direito)
        self._lbl_badge = ctk.CTkLabel(
            self,
            text="",
            text_color="white",  # foreground -> text_color
            fg_color="#dc3545",  # background -> fg_color
            font=("Arial", 8, "bold"),
            width=20,  # padding equivalente via width/height
            height=16,
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
