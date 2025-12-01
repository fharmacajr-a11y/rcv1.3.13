# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

import ttkbootstrap as tb

from src.utils.resource_path import resource_path

_log = logging.getLogger(__name__)


class TopBar(tb.Frame):
    """Barra superior simples com botoes principais."""

    def __init__(
        self,
        master=None,
        on_home: Optional[Callable[[], None]] = None,
        on_pdf_converter: Optional[Callable[[], None]] = None,
        on_chatgpt: Optional[Callable[[], None]] = None,
        on_sites: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._on_home = on_home
        self._on_pdf_converter = on_pdf_converter
        self._on_chatgpt = on_chatgpt
        self._on_sites = on_sites

        self._sites_image = None
        self._chatgpt_image = None
        try:
            icon_path = resource_path("assets/topbar/sites.png")
            if os.path.exists(icon_path):
                self._sites_image = tk.PhotoImage(file=icon_path)
            else:
                _log.warning("Icone do Sites nao encontrado: %s", icon_path)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar icone do Sites: %s", exc)

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
                _log.warning("Icone do ChatGPT nao encontrado: %s", chatgpt_icon_path)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar icone do ChatGPT: %s", exc)

        container = ttk.Frame(self)
        container.pack(fill="x", expand=True)

        # Tornar o botão "Inicio" azul claro (mesmo estilo dos botões ChatGPT/Sites)
        self._home_bootstyle_inactive = "info"
        self._home_bootstyle_active = "info"

        self.btn_home = tb.Button(
            container,
            text="Inicio",
            command=self._handle_home,
            bootstyle=self._home_bootstyle_inactive,
        )
        self.btn_home.pack(side="left", padx=8, pady=6)

        # Usar tb.Button com mesmo bootstyle 'info' para ficar azul claro
        self.btn_pdf_converter = tb.Button(
            container,
            text="Conversor PDF",
            command=self._handle_pdf_converter,
            bootstyle="info",
        )
        self.btn_pdf_converter.pack(side="left", padx=0, pady=6)

        self.btn_chatgpt = tb.Button(
            container,
            text="ChatGPT",
            image=self._chatgpt_image,
            compound="left" if self._chatgpt_image else None,
            command=self._handle_chatgpt,
            bootstyle="info",
        )
        self.btn_chatgpt.pack(side="left", padx=8, pady=6)

        self.btn_sites = tb.Button(
            container,
            text="Sites",
            image=self._sites_image,
            compound="left" if self._sites_image else None,
            command=self._handle_sites,
            bootstyle="info",
        )
        self.btn_sites.pack(side="left", padx=0, pady=6)

        self.right_container = ttk.Frame(container)
        self.right_container.pack(side="right")

    def _handle_home(self) -> None:
        if callable(self._on_home):
            try:
                self._on_home()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_home: %s", exc)

    def _handle_pdf_converter(self) -> None:
        if callable(self._on_pdf_converter):
            try:
                self._on_pdf_converter()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_pdf_converter: %s", exc)

    def _handle_chatgpt(self) -> None:
        if callable(self._on_chatgpt):
            try:
                self._on_chatgpt()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_chatgpt: %s", exc)

    def _handle_sites(self) -> None:
        if callable(self._on_sites):
            try:
                self._on_sites()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_sites: %s", exc)

    def set_is_hub(self, is_hub: bool) -> None:
        try:
            target_style = self._home_bootstyle_active if is_hub else self._home_bootstyle_inactive
            self.btn_home.configure(bootstyle=target_style)
        except Exception:
            _log.debug("Falha ao aplicar estilo no botão Home da topbar", exc_info=True)
        try:
            if is_hub:
                self.btn_home.state(["disabled"])
            else:
                self.btn_home.state(["!disabled"])
        except Exception:
            self.btn_home["state"] = "disabled" if is_hub else "normal"

    def set_pick_mode_active(self, active: bool) -> None:
        """Desabilita/habilita botões durante modo seleção de clientes (FIX-CLIENTES-005)."""
        try:
            if active:
                self.btn_pdf_converter.state(["disabled"])
            else:
                self.btn_pdf_converter.state(["!disabled"])
        except Exception:
            self.btn_pdf_converter["state"] = "disabled" if active else "normal"
