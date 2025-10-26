# -*- coding: utf-8 -*-
from __future__ import annotations

import ttkbootstrap as tb
from tkinter import ttk
from typing import Optional, Callable


class TopBar(tb.Frame):
    """Barra superior simples com botão 'Início'."""

    def __init__(
        self, master=None, on_home: Optional[Callable[[], None]] = None, **kwargs
    ):
        super().__init__(master, **kwargs)
        self._on_home = on_home

        container = ttk.Frame(self)
        container.pack(fill="x", expand=True)

        self.btn_home = ttk.Button(container, text="Início", command=self._handle_home)
        self.btn_home.pack(side="left", padx=8, pady=6)

        self.right_container = ttk.Frame(container)
        self.right_container.pack(side="right")

    def _handle_home(self) -> None:
        if callable(self._on_home):
            try:
                self._on_home()
            except Exception:
                pass

    def set_is_hub(self, is_hub: bool) -> None:
        try:
            if is_hub:
                self.btn_home.state(["disabled"])
            else:
                self.btn_home.state(["!disabled"])
        except Exception:
            self.btn_home["state"] = "disabled" if is_hub else "normal"
