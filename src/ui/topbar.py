# -*- coding: utf-8 -*-
"""TopBar compositor - orquestra componentes TopbarNav e TopbarActions.

REFATORAÇÃO P2 (Microfase 1):
- TopBar agora é um compositor que monta TopbarNav (navegação) e TopbarActions (notificações)
- Mantém interface pública compatível com main_window.py
- Reduz acoplamento e facilita manutenção
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Any, Callable, Optional

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
from src.ui.ui_tokens import APP_BG, BORDER, BORDER_WIDTH, CARD_RADIUS, SURFACE_DARK

from src.ui.components.topbar_actions import TopbarActions
from src.ui.components.topbar_nav import TopbarNav

_log = logging.getLogger(__name__)

# Classe base dinâmica: CTkFrame se CTk disponível, senão tk.Frame
BaseTopBar = ctk.CTkFrame if (HAS_CUSTOMTKINTER and ctk is not None) else tk.Frame


class _NavCallbacks:
    """Adapter de callbacks de navegação."""

    def __init__(self, topbar: TopBar):
        self._topbar = topbar

    def on_home(self) -> None:
        self._topbar._handle_home()

    def on_pdf_viewer(self) -> None:
        self._topbar._handle_pdf_viewer()

    def on_chatgpt(self) -> None:
        self._topbar._handle_chatgpt()

    def on_sites(self) -> None:
        self._topbar._handle_sites()


class _ActionsCallbacks:
    """Adapter de callbacks de ações."""

    def __init__(self, topbar: TopBar):
        self._topbar = topbar

    def on_notifications_clicked(self) -> None:
        if callable(self._topbar._on_notifications_clicked):
            try:
                self._topbar._on_notifications_clicked()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_notifications_clicked: %s", exc)

    def on_mark_all_read(self) -> bool:
        if callable(self._topbar._on_mark_all_read):
            try:
                return self._topbar._on_mark_all_read()
            except Exception as exc:  # noqa: BLE001
                _log.exception("Falha ao executar on_mark_all_read: %s", exc)
                return False
        return False

    def on_delete_notification_for_me(self, notification_id: str) -> bool:
        if callable(self._topbar._on_delete_notification_for_me):
            try:
                return self._topbar._on_delete_notification_for_me(notification_id)
            except Exception as exc:  # noqa: BLE001
                _log.exception("Falha ao executar on_delete_notification_for_me: %s", exc)
                return False
        return False

    def on_delete_all_notifications_for_me(self) -> bool:
        if callable(self._topbar._on_delete_all_notifications_for_me):
            try:
                return self._topbar._on_delete_all_notifications_for_me()
            except Exception as exc:  # noqa: BLE001
                _log.exception("Falha ao executar on_delete_all_notifications_for_me: %s", exc)
                return False
        return False


class TopBar(BaseTopBar):
    """Barra superior compositor - monta TopbarNav e TopbarActions.

    Mantém interface pública compatível para não quebrar main_window.py.
    Usa CTkFrame quando CustomTkinter disponível, tk.Frame como fallback.
    """

    def __init__(
        self,
        master=None,
        on_home: Optional[Callable[[], None]] = None,
        on_pdf_converter: Optional[Callable[[], None]] = None,
        on_pdf_viewer: Optional[Callable[[], None]] = None,
        on_chatgpt: Optional[Callable[[], None]] = None,
        on_sites: Optional[Callable[[], None]] = None,
        on_notifications_clicked: Optional[Callable[[], None]] = None,
        on_mark_all_read: Optional[Callable[[], bool]] = None,
        on_delete_notification_for_me: Optional[Callable[[str], bool]] = None,
        on_delete_all_notifications_for_me: Optional[Callable[[], bool]] = None,
        **kwargs,
    ):
        """Inicializa TopBar compositor.

        Args:
            master: Widget pai
            on_home: Callback para botão Início
            on_pdf_converter: Callback para conversor PDF (deprecated, mantido para compatibilidade)
            on_pdf_viewer: Callback para visualizador PDF
            on_chatgpt: Callback para ChatGPT
            on_sites: Callback para Sites
            on_notifications_clicked: Callback para clique em notificações
            on_mark_all_read: Callback para marcar todas notificações como lidas
            on_delete_notification_for_me: Callback para excluir notificação (só para o usuário)
            on_delete_all_notifications_for_me: Callback para excluir todas notificações (só para o usuário)
        """
        # Wrapper transparente — quem desenha o fundo arredondado é o "bar" interno
        if HAS_CUSTOMTKINTER and ctk is not None:
            super().__init__(master, fg_color=APP_BG, corner_radius=0, **kwargs)
        else:
            super().__init__(master, bg=APP_BG[0], **kwargs)

        # Guardar callbacks
        self._on_home = on_home
        self._on_pdf_converter = on_pdf_converter  # Mantido para compatibilidade
        self._on_pdf_viewer = on_pdf_viewer
        self._on_chatgpt = on_chatgpt
        self._on_sites = on_sites
        self._on_notifications_clicked = on_notifications_clicked
        self._on_mark_all_read = on_mark_all_read
        self._on_delete_notification_for_me = on_delete_notification_for_me
        self._on_delete_all_notifications_for_me = on_delete_all_notifications_for_me

        # "Card" arredondado — fundo cinza, borda fina, altura fixa
        if HAS_CUSTOMTKINTER and ctk is not None:
            bar = ctk.CTkFrame(
                self,
                fg_color=SURFACE_DARK,
                bg_color=APP_BG,
                corner_radius=CARD_RADIUS,
                border_width=BORDER_WIDTH,
                border_color=BORDER,
                height=48,
            )
        else:
            bar = tk.Frame(self, bg=SURFACE_DARK[0], height=48)
        bar.pack(side="top", fill="x", padx=10, pady=(0, 8))
        bar.pack_propagate(False)  # respeitar height fixa

        # Container transparente dentro do bar
        if HAS_CUSTOMTKINTER and ctk is not None:
            container = ctk.CTkFrame(bar, fg_color="transparent")
        else:
            container = tk.Frame(bar, bg=SURFACE_DARK[0])
        container.pack(fill="both", expand=True, padx=8, pady=6)

        # Criar componentes com padding interno p/ não encostar nos cantos
        self._nav = TopbarNav(container, callbacks=_NavCallbacks(self))
        self._nav.pack(side="left", fill="y", padx=(18, 0))

        self._actions = TopbarActions(container, callbacks=_ActionsCallbacks(self))
        self._actions.pack(side="right", fill="y", padx=(0, 12))

        # Expor botões para compatibilidade com código existente
        self.btn_home = self._nav.btn_home
        self.btn_pdf_viewer = self._nav.btn_pdf_viewer
        self.btn_chatgpt = self._nav.btn_chatgpt
        self.btn_sites = self._nav.btn_sites
        self.btn_notifications = self._actions.btn_notifications

    def _handle_home(self) -> None:
        """Handler para o botão Início."""
        if callable(self._on_home):
            try:
                self._on_home()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_home: %s", exc)

    def _handle_pdf_converter(self) -> None:
        """NO-OP seguro - botão removido mas mantém compatibilidade."""
        if callable(self._on_pdf_converter):
            try:
                self._on_pdf_converter()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_pdf_converter: %s", exc)

    def _handle_pdf_viewer(self) -> None:
        """Handler para o botão Visualizador PDF."""
        if callable(self._on_pdf_viewer):
            try:
                self._on_pdf_viewer()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_pdf_viewer: %s", exc)

    def _handle_chatgpt(self) -> None:
        """Handler para o botão ChatGPT."""
        if callable(self._on_chatgpt):
            try:
                self._on_chatgpt()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_chatgpt: %s", exc)

    def _handle_sites(self) -> None:
        """Handler para o botão Sites."""
        if callable(self._on_sites):
            try:
                self._on_sites()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_sites: %s", exc)

    # ===== Métodos públicos (delegam para subcomponentes) =====

    def set_active_screen(self, screen_name: str) -> None:
        """Atualiza estado dos botões baseado na tela ativa.

        Args:
            screen_name: Nome da tela ativa ("main", "hub", "sites", "passwords", etc.)
        """
        self._nav.set_active_screen(screen_name)

    def set_is_hub(self, is_hub: bool) -> None:
        """[DEPRECATED] Atualiza estado do botão Início conforme contexto Hub.

        NOTA: Mantido para compatibilidade. Prefira usar set_active_screen().

        Args:
            is_hub: True se está no Hub, False caso contrário
        """
        self._nav.set_is_hub(is_hub)

    def set_pick_mode_active(self, active: bool) -> None:
        """Desabilita/habilita botões durante modo seleção de clientes.

        Args:
            active: True para desabilitar, False para habilitar
        """
        self._nav.set_pick_mode_active(active)

    def set_notifications_count(self, count: int) -> None:
        """Atualiza contador de notificações não lidas.

        Args:
            count: Número de notificações não lidas
        """
        self._actions.set_notifications_count(count)

    def set_notifications_data(
        self,
        notifications: list[dict[str, Any]],
        mute_callback: Any = None,
    ) -> None:
        """Atualiza dados das notificações.

        Args:
            notifications: Lista de notificações
            mute_callback: Callback para toggle de mute (recebe bool)
        """
        self._actions.set_notifications_data(notifications, mute_callback)
