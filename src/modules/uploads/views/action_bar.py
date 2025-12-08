from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ActionBar(ttk.Frame):
    """Barra com botões de ações rápidas."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_download: Optional[Callable[[], None]] = None,
        on_download_folder: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_view: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        col = 0

        if on_download is not None:
            download_btn = ttk.Button(self, text="Baixar", command=on_download)
            download_btn.grid(row=0, column=col, padx=(0, 8))
            col += 1

        if on_download_folder is not None:
            folder_btn = ttk.Button(self, text="Baixar pasta (.zip)", command=on_download_folder)
            folder_btn.grid(row=0, column=col, padx=(0, 8))
            col += 1

        if on_delete is not None:
            delete_btn = ttk.Button(self, text="Excluir", command=on_delete)
            delete_btn.grid(row=0, column=col, padx=(0, 8))
            col += 1

        if on_view is not None:
            view_btn = ttk.Button(self, text="Visualizar", command=on_view)
            view_btn.grid(row=0, column=col, padx=(0, 8))
            col += 1

        # Coluna elástica depois do último botão para empurrar tudo para a esquerda
        self.columnconfigure(col, weight=1)
