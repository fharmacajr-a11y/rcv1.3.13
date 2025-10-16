"""Telas placeholder utilizadas para módulos ainda não implementados."""

from __future__ import annotations

import ttkbootstrap as tb


from typing import Callable


class ComingSoonScreen(tb.Frame):
    """Placeholder simples com header e mensagem padrão."""

    def __init__(self, master, *, title: str, on_back: Callable[[], None] | None = None) -> None:
        super().__init__(master, padding=20)

        header = tb.Label(self, text=title, font=("-size", 14, "bold"))
        header.pack(anchor="w")

        message = tb.Label(self, text="Em breve", font=("-size", 12))
        message.pack(anchor="w", pady=(8, 0))

        if on_back:
            tb.Button(self, text="Voltar", bootstyle="secondary", command=on_back).pack(
                anchor="w", pady=(16, 0)
            )
