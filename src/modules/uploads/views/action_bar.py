from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Callable, Optional

# CustomTkinter (fonte centralizada)
from src.ui.ctk_config import ctk

if TYPE_CHECKING:
    pass  # ctk já importado via src.ui.ctk_config


class ActionBar(ctk.CTkFrame):  # type: ignore[misc]
    """Barra com botões de ações rápidas (CustomTkinter)."""

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
        self.btn_download: Optional[CTkButton] = None  # type: ignore[valid-type]
        self.btn_download_folder: Optional[CTkButton] = None  # type: ignore[valid-type]
        self.btn_delete: Optional[CTkButton] = None  # type: ignore[valid-type]
        self.btn_view: Optional[CTkButton] = None  # type: ignore[valid-type]
        self.btn_refresh: Optional[CTkButton] = None  # type: ignore[valid-type]
        self.btn_close: Optional[CTkButton] = None  # type: ignore[valid-type]

        # Frame esquerdo (botões principais)
        left = ctk.CTkFrame(self)  # type: ignore[union-attr]
        left.grid(row=0, column=0, sticky="w")

        col = 0

        if on_download is not None:
            btn = ctk.CTkButton(left, text="Baixar", command=on_download)  # type: ignore[union-attr]
            btn.grid(row=0, column=col, padx=(0, 8))
            self.btn_download = btn  # type: ignore[assignment]
            col += 1

        if on_download_folder is not None:
            btn = ctk.CTkButton(left, text="Baixar pasta (.zip)", command=on_download_folder)  # type: ignore[union-attr]
            btn.grid(row=0, column=col, padx=(0, 8))
            self.btn_download_folder = btn  # type: ignore[assignment]
            col += 1

        if on_delete is not None:
            btn = ctk.CTkButton(left, text="Excluir", command=on_delete, fg_color="red", hover_color="darkred")  # type: ignore[union-attr]
            btn.grid(row=0, column=col, padx=(0, 8))
            self.btn_delete = btn  # type: ignore[assignment]
            col += 1

        if on_view is not None:
            btn = ctk.CTkButton(left, text="Visualizar", command=on_view, fg_color="green", hover_color="darkgreen")  # type: ignore[union-attr]
            btn.grid(row=0, column=col, padx=(0, 8))
            self.btn_view = btn  # type: ignore[assignment]
            col += 1

        # Frame direito (botões auxiliares)
        right = ctk.CTkFrame(self)  # type: ignore[union-attr]
        right.grid(row=0, column=1, sticky="e")

        col_right = 0

        if on_close is not None:
            self.btn_close = ctk.CTkButton(
                right, text="Fechar", command=on_close, fg_color="gray", hover_color="darkgray"
            )  # type: ignore[assignment]
            if self.btn_close is not None:
                self.btn_close.grid(row=0, column=col_right)

        # Coluna elástica para empurrar right para a direita
        self.columnconfigure(0, weight=1)

        # Inicializar com botões principais desabilitados
        self.set_enabled(download=False, download_folder=False, delete=False, view=False)

    def set_enabled(self, *, download: bool, download_folder: bool, delete: bool, view: bool) -> None:
        """Habilita ou desabilita os botões conforme os parâmetros."""
        if self.btn_download is not None:
            self.btn_download.configure(state="normal" if download else "disabled")  # type: ignore[union-attr]
        if self.btn_download_folder is not None:
            self.btn_download_folder.configure(state="normal" if download_folder else "disabled")  # type: ignore[union-attr]
        if self.btn_delete is not None:
            self.btn_delete.configure(state="normal" if delete else "disabled")  # type: ignore[union-attr]
        if self.btn_view is not None:
            self.btn_view.configure(state="normal" if view else "disabled")  # type: ignore[union-attr]
