# -*- coding: utf-8 -*-
"""Componente de ações da TopBar.

DESATIVADO v1.5.99: Notificações removidas (eliminado para resolver ReadError no shutdown).
TopbarActions contém o botão de refresh com ícone light/dark e tooltip.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from typing import Any, Optional, Protocol

from PIL import Image

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
from src.ui.ui_tokens import TOOLTIP_BG, TOOLTIP_FG
from src.utils.resource_path import resource_path

_log = logging.getLogger(__name__)

# Hover sutil para icon-button sobre fundo SURFACE_DARK da topbar.
# Ligeiramente mais escuro/claro do que o fundo, sem formar bloco pesado.
_ICON_BTN_HOVER = ("#c8c8c8", "#252525")


def _attach_tooltip(widget: Any, text: str) -> None:
    """Anexa tooltip a um widget usando tk.Toplevel puro.

    Usa tk.Toplevel (não CTkToplevel) para evitar o overhead de inicialização
    do CustomTkinter, que causa flash e deslocamento no Windows.

    - Delay de 400 ms antes de exibir (evita flicker em passagens rápidas).
    - update_idletasks() antes de posicionar (dimensões reais do conteúdo).
    - Clamp de coordenadas para não sair da tela.
    - Cancela agendamento pendente no <Leave>.
    """
    _tip_win: list[Any] = [None]
    _after_id: list[Any] = [None]

    def _schedule_show(event: Any) -> None:
        if _after_id[0] is not None:
            try:
                widget.after_cancel(_after_id[0])
            except Exception:  # noqa: BLE001
                pass
        _after_id[0] = widget.after(400, lambda: _show(event.x_root, event.y_root))

    def _show(x_root: int, y_root: int) -> None:  # noqa: ARG001
        _after_id[0] = None
        if _tip_win[0] is not None:
            return
        try:
            win = tk.Toplevel(widget)
            win.withdraw()
            win.wm_overrideredirect(True)
            win.wm_attributes("-topmost", True)

            lbl = tk.Label(
                win,
                text=text,
                background=TOOLTIP_BG,
                foreground=TOOLTIP_FG,
                font=("Segoe UI", 9),
                relief="flat",
                padx=5,
                pady=3,
            )
            lbl.pack()

            # Forçar cálculo real do tamanho antes de posicionar
            win.update_idletasks()
            tw = win.winfo_reqwidth()
            th = win.winfo_reqheight()

            # Posição centrada abaixo do widget
            bx = widget.winfo_rootx()
            by = widget.winfo_rooty()
            bw = widget.winfo_width()
            bh = widget.winfo_height()

            x = bx + (bw - tw) // 2
            y = by + bh + 4

            # Clamp: não deixar sair da tela
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            if x + tw > sw:
                x = sw - tw - 4
            if x < 0:
                x = 4
            if y + th > sh:
                y = by - th - 4

            win.wm_geometry(f"+{x}+{y}")
            win.deiconify()
            _tip_win[0] = win
        except Exception as exc:  # noqa: BLE001
            _log.debug("Tooltip show falhou: %s", exc)

    def _hide(event: Any = None) -> None:  # noqa: ARG001
        if _after_id[0] is not None:
            try:
                widget.after_cancel(_after_id[0])
            except Exception:  # noqa: BLE001
                pass
            _after_id[0] = None
        win = _tip_win[0]
        if win is not None:
            try:
                win.destroy()
            except Exception:  # noqa: BLE001
                pass
            _tip_win[0] = None

    widget.bind("<Enter>", _schedule_show, add="+")
    widget.bind("<Leave>", _hide, add="+")
    widget.bind("<Destroy>", _hide, add="+")


class TopbarActionsCallbacks(Protocol):
    """Protocolo de callbacks para ações (mantido para compatibilidade)."""

    def on_notifications_clicked(self) -> None: ...
    def on_mark_all_read(self) -> bool: ...
    def on_delete_notification_for_me(self, notification_id: str) -> bool: ...
    def on_delete_all_notifications_for_me(self) -> bool: ...
    def on_refresh(self) -> None: ...


class TopbarActions(ctk.CTkFrame):
    """Componente de ações da TopBar (direita).

    Contém o botão de refresh com ícone light/dark e tooltip.
    Notificações desativadas v1.5.99.
    """

    def __init__(
        self,
        master,
        callbacks: TopbarActionsCallbacks,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._callbacks = callbacks
        self.btn_notifications = None  # Compatibilidade

        # Referências de imagem PIL (evitar GC)
        self._refresh_pil_light: Optional[Image.Image] = None
        self._refresh_pil_dark: Optional[Image.Image] = None
        self._refresh_image = None

        self._load_refresh_icon()
        self._build_buttons()

    # ===== Carregamento de ícone =====

    def _load_refresh_icon(self) -> None:
        """Carrega ícones de atualizar como CTkImage (light/dark)."""
        if not HAS_CUSTOMTKINTER or ctk is None:
            _log.debug("CustomTkinter não disponível, ícone de refresh desabilitado")
            return

        try:
            # light_image = versão escura (legível sobre fundo claro)
            path_light = resource_path("assets/topbar/atualizarblack.png")
            # dark_image  = versão clara  (legível sobre fundo escuro)
            path_dark = resource_path("assets/topbar/atualizarhigt.png")

            img_size = 20

            if os.path.exists(path_light):
                img = Image.open(path_light).convert("RGBA")
                if img.width > img_size or img.height > img_size:
                    img = img.copy()
                    img.thumbnail((img_size, img_size), Image.Resampling.LANCZOS)
                self._refresh_pil_light = img
            else:
                _log.warning("Ícone de refresh (light) não encontrado: %s", path_light)

            if os.path.exists(path_dark):
                img = Image.open(path_dark).convert("RGBA")
                if img.width > img_size or img.height > img_size:
                    img = img.copy()
                    img.thumbnail((img_size, img_size), Image.Resampling.LANCZOS)
                self._refresh_pil_dark = img
            else:
                _log.warning("Ícone de refresh (dark) não encontrado: %s", path_dark)

            if self._refresh_pil_light is not None and self._refresh_pil_dark is not None:
                self._refresh_image = ctk.CTkImage(
                    light_image=self._refresh_pil_light,
                    dark_image=self._refresh_pil_dark,
                    size=(img_size, img_size),
                )
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar ícone de refresh: %s", exc)

    # ===== Construção de botões =====

    def _build_buttons(self) -> None:
        """Cria o botão de refresh como icon-button limpo com tooltip."""
        if not HAS_CUSTOMTKINTER or ctk is None:
            return

        self.btn_refresh = ctk.CTkButton(
            self,
            text="",
            image=self._refresh_image,
            command=self._handle_refresh,
            width=28,
            height=28,
            corner_radius=6,
            border_spacing=2,
            fg_color="transparent",
            hover_color=_ICON_BTN_HOVER,
        )
        self.btn_refresh.pack(side="right", padx=(4, 0), pady=2)

        _attach_tooltip(self.btn_refresh, "Atualizar")

    # ===== Handlers =====

    def _handle_refresh(self) -> None:
        """Chama o callback de refresh de forma segura."""
        try:
            self._callbacks.on_refresh()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao executar on_refresh: %s", exc)

    # ===== Métodos públicos (no-ops de compatibilidade) =====

    def set_notifications_count(self, count: int) -> None:  # noqa: ARG002
        """NO-OP: Notificações desativadas v1.5.99."""

    def set_notifications_data(
        self,
        notifications: list[dict[str, Any]],  # noqa: ARG002
        mute_callback: Any = None,  # noqa: ARG002
    ) -> None:
        """NO-OP: Notificações desativadas v1.5.99."""
