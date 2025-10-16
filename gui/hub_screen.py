"""Tela Hub (pré-home) apresentada após o login."""

from __future__ import annotations

import ttkbootstrap as tb
from typing import Callable


class HubScreen(tb.Frame):
    """Tela inicial com atalhos para módulos principais."""

    def __init__(
        self,
        master,
        *,
        on_open_sifap: Callable[[], None],
        on_open_anvisa: Callable[[], None],
        on_open_passwords: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=(16, 12))

        toolbar = tb.Frame(self, padding=(4, 4, 4, 4))
        toolbar.pack(anchor="nw")

        # Configuração base para botões pequenos e discretos.
        btn_opts = {"bootstyle": "secondary-outline", "width": 12}

        self.btn_sifap = tb.Button(toolbar, text="sIFAP", command=on_open_sifap, **btn_opts)
        self.btn_sifap.pack(side="left", padx=(0, 6))

        self.btn_anvisa = tb.Button(toolbar, text="ANVISA", command=on_open_anvisa, **btn_opts)
        self.btn_anvisa.pack(side="left", padx=(0, 6))

        self.btn_passwords = tb.Button(
            toolbar, text="senhas", command=on_open_passwords, **btn_opts
        )
        self.btn_passwords.pack(side="left")

        # Espaçador para aproveitar o centro da tela no futuro.
        content = tb.Frame(self)
        content.pack(fill="both", expand=True)

        tb.Label(
            content,
            text="Selecione um módulo para continuar.",
            font=("-size", 12),
            anchor="w",
        ).pack(anchor="nw", padx=4, pady=(12, 0))
