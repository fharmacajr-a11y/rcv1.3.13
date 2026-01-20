from __future__ import annotations

from src.ui.ctk_config import ctk

from src.ui.ui_tokens import SURFACE_DARK

# -*- coding: utf-8 -*-
"""Componente de navegação da TopBar (botões principais à esquerda).

MICROFASE 24: Migrado para CustomTkinter.
"""

import logging
import os
from typing import Protocol

from PIL import Image

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
from src.utils.resource_path import resource_path

_log = logging.getLogger(__name__)

# Constantes de espaçamento (mesmas da TopBar)
BTN_PADX = 4
BTN_PADY = 4


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
        # Configurar strip cinza atrás dos botões
        if HAS_CUSTOMTKINTER and ctk is not None:
            super().__init__(master, fg_color=SURFACE_DARK, corner_radius=0, **kwargs)
        else:
            super().__init__(master, bg=SURFACE_DARK[0], **kwargs)
            
        self._callbacks = callbacks

        # Referências de imagens (IMPORTANTE: manter para evitar GC)
        self._sites_image = None
        self._chatgpt_image = None

        # Carregar ícones
        self._load_icons()

        # Construir botões
        self._build_buttons()

    def _load_icons(self) -> None:
        """Carrega ícones dos botões como CTkImage."""
        if not HAS_CUSTOMTKINTER or ctk is None:
            _log.debug("CustomTkinter não disponível, ícones desabilitados")
            return

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

        # Botão Início
        self.btn_home = ctk.CTkButton(
            self,
            text="Inicio",
            command=self._handle_home,
            width=80,
            height=28,
        )
        self.btn_home.pack(side="left", padx=(6, BTN_PADX), pady=BTN_PADY)

        # Botão Visualizador PDF
        self.btn_pdf_viewer = ctk.CTkButton(
            self,
            text="Visualizador PDF",
            command=self._handle_pdf_viewer,
            width=120,
            height=28,
        )
        self.btn_pdf_viewer.pack(side="left", padx=(BTN_PADX, BTN_PADX), pady=BTN_PADY)

        # Botão ChatGPT (sem ícone temporariamente para debugging)
        self.btn_chatgpt = ctk.CTkButton(
            self,
            text="ChatGPT",
            # image=self._chatgpt_image,
            # compound="left" if self._chatgpt_image else "none",
            command=self._handle_chatgpt,
            width=100,
            height=28,
        )
        self.btn_chatgpt.pack(side="left", padx=(BTN_PADX, BTN_PADX), pady=BTN_PADY)

        # Botão Sites (sem ícone temporariamente para debugging)
        self.btn_sites = ctk.CTkButton(
            self,
            text="Sites",
            # image=self._sites_image,
            # compound="left" if self._sites_image else "none",
            command=self._handle_sites,
            width=80,
            height=28,
        )
        self.btn_sites.pack(side="left", padx=(BTN_PADX, 0), pady=BTN_PADY)

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
        """
        # CTkButton usa configure(state="normal"/"disabled")
        buttons = [self.btn_home, self.btn_pdf_viewer, self.btn_chatgpt, self.btn_sites]
        for btn in buttons:
            try:
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
