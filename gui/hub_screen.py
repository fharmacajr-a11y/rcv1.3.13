# -*- coding: utf-8 -*-
"""Tela Hub apresentada após o login."""

from __future__ import annotations

from typing import Callable, Optional

import ttkbootstrap as tb


class HubScreen(tb.Frame):
    """Tela inicial com atalhos para módulos principais."""

    def __init__(
        self,
        master,
        *,
        open_sifap: Optional[Callable[[], None]] = None,
        open_anvisa: Optional[Callable[[], None]] = None,
        open_auditoria: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_snjpc: Optional[Callable[[], None]] = None,
        open_senhas: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        on_open_sifap = kwargs.pop("on_open_sifap", None)
        on_open_anvisa = kwargs.pop("on_open_anvisa", None)
        on_open_auditoria = kwargs.pop("on_open_auditoria", None)
        on_open_farmacia_popular = kwargs.pop("on_open_farmacia_popular", None)
        on_open_snjpc = kwargs.pop("on_open_snjpc", None)
        on_open_senhas = kwargs.pop("on_open_passwords", None) or kwargs.pop(
            "on_open_senhas", None
        )

        open_sifap = open_sifap or on_open_sifap
        open_anvisa = open_anvisa or on_open_anvisa
        open_auditoria = open_auditoria or on_open_auditoria
        open_farmacia_popular = open_farmacia_popular or on_open_farmacia_popular
        open_snjpc = open_snjpc or on_open_snjpc
        open_senhas = open_senhas or on_open_senhas

        super().__init__(master, padding=(16, 12), **kwargs)

        self.open_sifap = self.on_open_sifap = open_sifap
        self.open_anvisa = self.on_open_anvisa = open_anvisa
        self.open_auditoria = self.on_open_auditoria = open_auditoria
        self.open_farmacia_popular = self.on_open_farmacia_popular = (
            open_farmacia_popular
        )
        self.open_snjpc = self.on_open_snjpc = open_snjpc
        self.open_senhas = self.on_open_senhas = open_senhas

        top = tb.Frame(self)
        top.pack(anchor="nw", fill="x")

        items = [
            ("SIFAP", self.open_sifap),
            ("ANVISA", self.open_anvisa),
            ("AUDITORIA", self.open_auditoria),
            ("FARMACIA POPULAR", self.open_farmacia_popular),
            ("SNJPC", self.open_snjpc),
            ("SENHAS", self.open_senhas),
        ]

        for label, cmd in items:
            btn = tb.Button(top, text=label, bootstyle="secondary", command=cmd)
            btn.configure(width=18)
            btn.pack(side="left", padx=2, pady=2)
            try:
                btn.configure(font=("-size", 9))
            except Exception:
                pass

        content = tb.Frame(self, padding=(12, 16))
        content.pack(fill="both", expand=True)

        tb.Label(
            content,
            text="Selecione um módulo para continuar.",
            font=("-size", 12),
            anchor="w",
        ).pack(anchor="nw", pady=(0, 8))
