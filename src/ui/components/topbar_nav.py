# -*- coding: utf-8 -*-
"""Componente de navegação da TopBar (botões principais à esquerda).

MICROFASE 24: Migrado para CustomTkinter.
"""

from __future__ import annotations

from src.ui.ctk_config import ctk

from src.ui.widgets.button_factory import make_btn
from src.ui.ui_tokens import (
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    BTN_TEXT_ON_COLOR,
    TOOLTIP_BG,
    TOOLTIP_FG,
)

import logging
import os
from typing import Protocol

from PIL import Image

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER
from src.utils.resource_path import resource_path

_log = logging.getLogger(__name__)

# Hover sutil para icon-button — mesmo padrão do botão de atualizar (TopbarActions)
_ICON_BTN_HOVER = ("#c8c8c8", "#252525")

# Constantes de espaçamento (mesmas da TopBar)
BTN_PADX = 4
BTN_PADY = 4


def _attach_tooltip(widget, text: str) -> None:
    """Tooltip com delay — mesmo padrão do TopbarActions."""
    import tkinter as _tk

    _tip_win: list = [None]
    _after_id: list = [None]

    def _schedule_show(event):
        if _after_id[0] is not None:
            try:
                widget.after_cancel(_after_id[0])
            except Exception:  # noqa: BLE001
                pass
        _after_id[0] = widget.after(400, lambda: _show(event.x_root, event.y_root))

    def _show(x_root, y_root):  # noqa: ARG001
        _after_id[0] = None
        if _tip_win[0] is not None:
            return
        try:
            win = _tk.Toplevel(widget)
            win.withdraw()
            win.wm_overrideredirect(True)
            win.wm_attributes("-topmost", True)
            _tk.Label(
                win,
                text=text,
                background=TOOLTIP_BG,
                foreground=TOOLTIP_FG,
                font=("Segoe UI", 9),
                relief="flat",
                padx=5,
                pady=3,
            ).pack()
            win.update_idletasks()
            bx = widget.winfo_rootx()
            by = widget.winfo_rooty()
            bw = widget.winfo_width()
            bh = widget.winfo_height()
            tw = win.winfo_reqwidth()
            x = bx + (bw - tw) // 2
            y = by + bh + 4
            win.wm_geometry(f"+{x}+{y}")
            win.deiconify()
            _tip_win[0] = win
        except Exception:  # noqa: BLE001
            pass

    def _hide(event=None):
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


class TopbarNavCallbacks(Protocol):
    """Protocolo de callbacks para navegação."""

    def on_home(self) -> None:
        """Callback para botão Início."""
        ...

    def on_pdf_viewer(self) -> None:
        """Callback para botão Visualizador PDF."""
        ...

    def on_chatgpt(self) -> None:
        """Callback para botão ChatGPT."""
        ...

    def on_sites(self) -> None:
        """Callback para botão Sites."""
        ...


class TopbarNav(ctk.CTkFrame):
    """Componente de navegação da TopBar com botões principais.

    Responsável pelos botões de navegação do lado esquerdo:
    - Início
    - Visualizador PDF
    - ChatGPT
    - Sites

    MICROFASE 24: Usa CTkButton ao invés de ttkbootstrap.
    """

    def __init__(
        self,
        master,
        callbacks: TopbarNavCallbacks,
        **kwargs,
    ):
        """Inicializa o componente de navegação.

        Args:
            master: Widget pai
            callbacks: Objeto com callbacks de navegação
        """
        # Fundo transparente (o cinza vem do container pai)
        if HAS_CUSTOMTKINTER and ctk is not None:
            super().__init__(master, fg_color="transparent", **kwargs)
        else:
            super().__init__(master, bg=master["bg"], **kwargs)

        self._callbacks = callbacks

        # Referências de imagens (IMPORTANTE: manter para evitar GC)
        self._sites_image = None
        self._chatgpt_image = None
        self._home_image = None

        # Carregar ícones
        self._load_icons()

        # Construir botões
        self._build_buttons()

    def _load_icons(self) -> None:
        """Carrega ícones dos botões como CTkImage."""
        if not HAS_CUSTOMTKINTER or ctk is None:
            _log.debug("CustomTkinter não disponível, ícones desabilitados")
            return

        # Ícone Início (light/dark aware)
        try:
            img_size = 20
            path_light = resource_path("assets/topbar/inicioblack.png")
            path_dark = resource_path("assets/topbar/iniciolight.png")
            if os.path.exists(path_light) and os.path.exists(path_dark):
                pil_light = Image.open(path_light).convert("RGBA")
                pil_dark = Image.open(path_dark).convert("RGBA")
                if pil_light.width > img_size or pil_light.height > img_size:
                    pil_light = pil_light.copy()
                    pil_light.thumbnail((img_size, img_size), Image.Resampling.LANCZOS)
                if pil_dark.width > img_size or pil_dark.height > img_size:
                    pil_dark = pil_dark.copy()
                    pil_dark.thumbnail((img_size, img_size), Image.Resampling.LANCZOS)
                self._home_pil_light = pil_light
                self._home_pil_dark = pil_dark
                self._home_image = ctk.CTkImage(
                    light_image=pil_light,
                    dark_image=pil_dark,
                    size=(img_size, img_size),
                )
            else:
                _log.warning("Ícone de Início não encontrado: %s / %s", path_light, path_dark)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar ícone de Início: %s", exc)

        # Ícone Sites
        try:
            icon_path = resource_path("assets/topbar/sites.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                # Manter referência da PIL Image também para evitar GC
                self._sites_pil = img
                # Redimensionar se necessário
                max_size = 16
                if img.width > max_size or img.height > max_size:
                    img = img.copy()
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    self._sites_pil = img
                # Criar CTkImage
                self._sites_image = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            else:
                _log.warning("Ícone do Sites não encontrado: %s", icon_path)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar ícone do Sites: %s", exc)

        # Ícone ChatGPT
        try:
            chatgpt_icon_path = resource_path("assets/topbar/chatgpt.png")
            if os.path.exists(chatgpt_icon_path):
                img = Image.open(chatgpt_icon_path)
                # Manter referência da PIL Image também para evitar GC
                self._chatgpt_pil = img
                # Redimensionar se necessário
                max_size = 16
                if img.width > max_size or img.height > max_size:
                    img = img.copy()
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    self._chatgpt_pil = img
                # Criar CTkImage
                self._chatgpt_image = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            else:
                _log.warning("Ícone do ChatGPT não encontrado: %s", chatgpt_icon_path)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar ícone do ChatGPT: %s", exc)

    def _build_buttons(self) -> None:
        """Constrói os botões de navegação usando CTkButton."""
        if not HAS_CUSTOMTKINTER or ctk is None:
            _log.warning("CustomTkinter não disponível, botões não criados")
            return

        # Botão Início — icon-only discreto (mesmo padrão do botão de atualizar)
        self.btn_home = ctk.CTkButton(  # type: ignore[union-attr]
            self,
            text="",
            image=self._home_image,
            command=self._handle_home,
            width=28,
            height=28,
            corner_radius=6,
            border_spacing=2,
            fg_color="transparent",
            hover_color=_ICON_BTN_HOVER,
        )
        self.btn_home.pack(side="left", padx=(0, 5), pady=2)
        _attach_tooltip(self.btn_home, "Início")

        # Botão Visualizador PDF
        self.btn_pdf_viewer = make_btn(
            self,
            text="Visualizador PDF",
            command=self._handle_pdf_viewer,
            width=130,  # Ligeiramente maior para acomodar texto
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_TEXT_ON_COLOR,
            font=("Segoe UI", 11),
        )
        self.btn_pdf_viewer.pack(side="left", padx=5, pady=2)

        # Botão ChatGPT (sem ícone temporariamente para debugging)
        self.btn_chatgpt = make_btn(
            self,
            text="ChatGPT",
            # image=self._chatgpt_image,
            # compound="left" if self._chatgpt_image else "none",
            command=self._handle_chatgpt,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_TEXT_ON_COLOR,
            font=("Segoe UI", 11),
        )
        self.btn_chatgpt.pack(side="left", padx=5, pady=2)

        # Botão Sites (sem ícone temporariamente para debugging)
        self.btn_sites = make_btn(
            self,
            text="Sites",
            # image=self._sites_image,
            # compound="left" if self._sites_image else "none",
            command=self._handle_sites,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_TEXT_ON_COLOR,
            font=("Segoe UI", 11),
        )
        self.btn_sites.pack(side="left", padx=(5, 0), pady=2)

    def _handle_home(self) -> None:
        """Handler para botão Início."""
        try:
            self._callbacks.on_home()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao executar on_home: %s", exc)

    def _handle_pdf_viewer(self) -> None:
        """Handler para botão Visualizador PDF."""
        try:
            self._callbacks.on_pdf_viewer()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao executar on_pdf_viewer: %s", exc)

    def _handle_chatgpt(self) -> None:
        """Handler para botão ChatGPT."""
        try:
            self._callbacks.on_chatgpt()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao executar on_chatgpt: %s", exc)

    def _handle_sites(self) -> None:
        """Handler para botão Sites."""
        try:
            self._callbacks.on_sites()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao executar on_sites: %s", exc)

    def set_active_screen(self, screen_name: str) -> None:
        """Atualiza estado dos botões baseado na tela ativa.

        Args:
            screen_name: Nome da tela ativa ("main", "hub", "sites", "passwords", etc.)

        NOTA: btn_home é excluído intencionalmente — ele é sempre "normal" e nunca
        é desabilitado por nenhum fluxo. Chamadas configure() em btn_home (transparent
        + CTkImage) geram um ciclo _draw() com _detect_color_of_master() + image-redraw
        que causa flash visual nos botões vizinhos. set_pick_mode_active() segue o mesmo
        critério e também não inclui btn_home.
        """
        buttons = [self.btn_pdf_viewer, self.btn_chatgpt, self.btn_sites]
        for btn in buttons:
            try:
                if btn.cget("state") != "normal":
                    btn.configure(state="normal")
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao habilitar botão %s: %s", btn, exc)

    def set_is_hub(self, is_hub: bool) -> None:
        """[DEPRECATED] Atualiza estado do botão Início conforme contexto Hub.

        NOTA: Mantido para compatibilidade. Prefira usar set_active_screen().
        btn_home sempre habilitado.

        Args:
            is_hub: True se está no Hub, False caso contrário
        """
        # CTkButton: sempre mantém habilitado
        try:
            self.btn_home.configure(state="normal")
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao manter btn_home habilitado: %s", exc)

    def set_pick_mode_active(self, active: bool) -> None:
        """Habilita/desabilita botões durante modo seleção de clientes.

        Args:
            active: True para desabilitar, False para habilitar
        """
        # btn_home sempre habilitado, desabilita apenas PDF/ChatGPT/Sites durante pick mode
        buttons = [self.btn_pdf_viewer, self.btn_chatgpt, self.btn_sites]
        state = "disabled" if active else "normal"
        for btn in buttons:
            try:
                btn.configure(state=state)
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao atualizar estado do botão %s: %s", btn, exc)

        # Garantir que btn_home permanece habilitado
        try:
            self.btn_home.configure(state="normal")
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao manter btn_home habilitado: %s", exc)
