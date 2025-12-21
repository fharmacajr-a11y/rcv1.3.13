from __future__ import annotations

import tkinter as tk
from tkinter import ttk as tk_ttk
from typing import TYPE_CHECKING, Callable, Optional, cast

# Tentar importar ttkbootstrap, fallback para tkinter.ttk
try:
    import ttkbootstrap as ttk
except ImportError:
    ttk = tk_ttk  # type: ignore[assignment]

if TYPE_CHECKING:
    # Para type hints, use tipos estáticos
    from tkinter.ttk import Button as TtkButton, Frame as TtkFrame
else:
    # Em runtime, use as classes importadas dinamicamente
    TtkButton = ttk.Button  # type: ignore[misc]
    TtkFrame = ttk.Frame  # type: ignore[misc]


class ActionBar(tk_ttk.Frame):
    """Barra com botões de ações rápidas."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_download: Optional[Callable[[], None]] = None,
        on_download_folder: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_view: Optional[Callable[[], None]] = None,
        on_refresh: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        # Guardar referências dos botões
        self.btn_download: Optional[TtkButton] = None
        self.btn_download_folder: Optional[TtkButton] = None
        self.btn_delete: Optional[TtkButton] = None
        self.btn_view: Optional[TtkButton] = None
        self.btn_refresh: Optional[TtkButton] = None
        self.btn_close: Optional[TtkButton] = None

        # Frame esquerdo (botões principais)
        left = cast(TtkFrame, ttk.Frame(self))
        left.grid(row=0, column=0, sticky="w")

        col = 0

        if on_download is not None:
            btn = ttk.Button(left, text="Baixar", command=on_download, bootstyle="info")
            btn.grid(row=0, column=col, padx=(0, 8))
            self.btn_download = btn
            col += 1

        if on_download_folder is not None:
            btn = ttk.Button(left, text="Baixar pasta (.zip)", command=on_download_folder, bootstyle="info")
            btn.grid(row=0, column=col, padx=(0, 8))
            self.btn_download_folder = btn
            col += 1

        if on_delete is not None:
            btn = ttk.Button(left, text="Excluir", command=on_delete, bootstyle="danger")
            btn.grid(row=0, column=col, padx=(0, 8))
            self.btn_delete = btn
            col += 1

        if on_view is not None:
            btn = ttk.Button(left, text="Visualizar", command=on_view, bootstyle="success")
            btn.grid(row=0, column=col, padx=(0, 8))
            self.btn_view = btn
            col += 1

        # Frame direito (botões auxiliares)
        right = cast(TtkFrame, ttk.Frame(self))
        right.grid(row=0, column=1, sticky="e")

        col_right = 0

        if on_close is not None:
            self.btn_close = ttk.Button(right, text="Fechar", command=on_close, bootstyle="secondary")
            # Type narrowing: garantir que btn_close foi criado
            if self.btn_close is not None:
                self.btn_close.grid(row=0, column=col_right)

        # Coluna elástica para empurrar right para a direita
        self.columnconfigure(0, weight=1)

        # Inicializar com botões principais desabilitados
        self.set_enabled(download=False, download_folder=False, delete=False, view=False)

    def set_enabled(self, *, download: bool, download_folder: bool, delete: bool, view: bool) -> None:
        """Habilita ou desabilita os botões conforme os parâmetros."""
        if self.btn_download is not None:
            self.btn_download.configure(state="normal" if download else "disabled")
        if self.btn_download_folder is not None:
            self.btn_download_folder.configure(state="normal" if download_folder else "disabled")
        if self.btn_delete is not None:
            self.btn_delete.configure(state="normal" if delete else "disabled")
        if self.btn_view is not None:
            self.btn_view.configure(state="normal" if view else "disabled")
