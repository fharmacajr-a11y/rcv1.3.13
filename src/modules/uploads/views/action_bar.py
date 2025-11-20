from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ActionBar(ttk.Frame):
    """Barra com botoes de acoes rapidas."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_download: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.columnconfigure(1, weight=1)
        download_btn = ttk.Button(self, text="Baixar", command=on_download)
        download_btn.grid(row=0, column=0, padx=(0, 8))
        delete_btn = ttk.Button(self, text="Excluir", command=on_delete)
        delete_btn.grid(row=0, column=1, sticky="w")
