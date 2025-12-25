# -*- coding: utf-8 -*-
"""Componente de navegação da TopBar (botões principais à esquerda)."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import ttk
from typing import Protocol

import ttkbootstrap as tb

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


class TopbarNav(ttk.Frame):
    """Componente de navegação da TopBar com botões principais.

    Responsável pelos botões de navegação do lado esquerdo:
    - Início
    - Visualizador PDF
    - ChatGPT
    - Sites
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
        super().__init__(master, **kwargs)
        self._callbacks = callbacks

        # Carregar ícones
        self._sites_image = None
        self._chatgpt_image = None
        self._load_icons()

        # Estilos para botão Início
        self._home_bootstyle_inactive = "info"
        self._home_bootstyle_active = "info"

        # Construir botões
        self._build_buttons()

    def _load_icons(self) -> None:
        """Carrega ícones dos botões."""
        # Ícone Sites
        try:
            icon_path = resource_path("assets/topbar/sites.png")
            if os.path.exists(icon_path):
                self._sites_image = tk.PhotoImage(file=icon_path)
            else:
                _log.warning("Ícone do Sites não encontrado: %s", icon_path)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar ícone do Sites: %s", exc)

        # Ícone ChatGPT
        try:
            chatgpt_icon_path = resource_path("assets/topbar/chatgpt.png")
            if os.path.exists(chatgpt_icon_path):
                img = tk.PhotoImage(file=chatgpt_icon_path)
                max_size = 16
                width, height = img.width(), img.height()
                if width > max_size or height > max_size:
                    scale_x = max(1, (width + max_size - 1) // max_size)
                    scale_y = max(1, (height + max_size - 1) // max_size)
                    img = img.subsample(scale_x, scale_y)
                self._chatgpt_image = img
            else:
                _log.warning("Ícone do ChatGPT não encontrado: %s", chatgpt_icon_path)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar ícone do ChatGPT: %s", exc)

    def _build_buttons(self) -> None:
        """Constrói os botões de navegação."""
        # Botão Início
        self.btn_home = tb.Button(
            self,
            text="Inicio",
            command=self._handle_home,
            bootstyle=self._home_bootstyle_inactive,
        )
        self.btn_home.pack(side="left", padx=(6, BTN_PADX), pady=BTN_PADY)

        # Botão Visualizador PDF
        self.btn_pdf_viewer = tb.Button(
            self,
            text="Visualizador PDF",
            command=self._handle_pdf_viewer,
            bootstyle="info",
        )
        self.btn_pdf_viewer.pack(side="left", padx=(BTN_PADX, BTN_PADX), pady=BTN_PADY)

        # Botão ChatGPT
        self.btn_chatgpt = tb.Button(
            self,
            text="ChatGPT",
            image=self._chatgpt_image,
            compound="left" if self._chatgpt_image else None,
            command=self._handle_chatgpt,
            bootstyle="info",
        )
        self.btn_chatgpt.pack(side="left", padx=(BTN_PADX, BTN_PADX), pady=BTN_PADY)

        # Botão Sites
        self.btn_sites = tb.Button(
            self,
            text="Sites",
            image=self._sites_image,
            compound="left" if self._sites_image else None,
            command=self._handle_sites,
            bootstyle="info",
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
        # FIX DEFINITIVO: btn_home SEMPRE habilitado (!disabled)
        # Se precisar indicar "tela ativa", usar apenas mudança de estilo/cor
        buttons = [self.btn_home, self.btn_pdf_viewer, self.btn_chatgpt, self.btn_sites]
        for btn in buttons:
            try:
                btn.state(["!disabled"])
            except Exception:
                try:
                    btn["state"] = "normal"
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao habilitar botão %s: %s", btn, exc)

        # Opcional: Aplicar estilo visual diferente para indicar tela ativa
        # (sem desabilitar o botão)
        try:
            if screen_name in ("main", "hub"):
                # Poderia aplicar bootstyle diferente aqui se necessário
                # self.btn_home.configure(bootstyle="success")
                pass
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao aplicar estilo de tela ativa: %s", exc)

    def set_is_hub(self, is_hub: bool) -> None:
        """[DEPRECATED] Atualiza estado do botão Início conforme contexto Hub.

        NOTA: Mantido para compatibilidade. Prefira usar set_active_screen().
        FIX: btn_home SEMPRE habilitado, apenas muda estilo visual.

        Args:
            is_hub: True se está no Hub, False caso contrário
        """
        # Aplicar estilo visual diferente
        try:
            target_style = self._home_bootstyle_active if is_hub else self._home_bootstyle_inactive
            self.btn_home.configure(bootstyle=target_style)
        except Exception:
            _log.debug("Falha ao aplicar estilo no botão Home", exc_info=True)

        # FIX DEFINITIVO: NUNCA desabilitar btn_home
        # Sempre manter habilitado para permitir navegação
        try:
            self.btn_home.state(["!disabled"])
        except Exception:
            try:
                self.btn_home["state"] = "normal"
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao habilitar botão Home: %s", exc)

    def set_pick_mode_active(self, active: bool) -> None:
        """Habilita/desabilita botões durante modo seleção de clientes.

        Args:
            active: True para desabilitar, False para habilitar
        """
        # FIX: btn_home SEMPRE habilitado, mesmo no modo pick
        # Desabilita apenas PDF/ChatGPT/Sites durante pick mode
        buttons = [self.btn_pdf_viewer, self.btn_chatgpt, self.btn_sites]
        for btn in buttons:
            try:
                if active:
                    btn.state(["disabled"])
                else:
                    btn.state(["!disabled"])
            except Exception:
                try:
                    btn["state"] = "disabled" if active else "normal"
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao atualizar estado do botão %s: %s", btn, exc)

        # Garantir que btn_home permanece habilitado
        try:
            self.btn_home.state(["!disabled"])
        except Exception:
            try:
                self.btn_home["state"] = "normal"
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao manter btn_home habilitado: %s", exc)
