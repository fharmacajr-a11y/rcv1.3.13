from __future__ import annotations

from src.ui.ctk_config import ctk

import tkinter as tk
from typing import Callable


class PdfToolbar(ctk.CTkFrame):
    """
    Barra superior do PDF Preview:
    - botões de zoom (-, 100%, +)
    - botão "Largura"
    - labels de página e zoom
    - toggle "Texto"
    - botões de download (PDF/Imagem)

    Não conhece PyMuPDF; apenas encaminha eventos via callbacks.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_zoom_in: Callable[[], None],
        on_zoom_out: Callable[[], None],
        on_zoom_100: Callable[[], None],
        on_fit_width: Callable[[], None],
        on_toggle_text: Callable[[bool], None],
        on_download_pdf: Callable[[], None],
        on_download_image: Callable[[], None],
        on_open_converter: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)

        self._on_toggle_text = on_toggle_text
        self.var_text = tk.BooleanVar(master=self, value=False)

        ctk.CTkButton(self, text="\u2212", width=3, command=on_zoom_out).pack(side="left", padx=(8, 0), pady=6)
        ctk.CTkButton(self, text="100%", command=on_zoom_100).pack(side="left", padx=4, pady=6)
        ctk.CTkButton(self, text="+", width=3, command=on_zoom_in).pack(side="left", padx=4, pady=6)
        ctk.CTkButton(self, text="Largura", command=on_fit_width).pack(side="left", padx=8, pady=6)

        self.lbl_page = ctk.CTkLabel(self, text="Página 1/1")
        self.lbl_page.pack(side="left", padx=12)
        self.lbl_zoom = ctk.CTkLabel(self, text="100%")
        self.lbl_zoom.pack(side="left", padx=6)

        self.chk_text = ctk.CTkCheckBox(self, text="Texto", variable=self.var_text, command=self._handle_toggle_text)
        self.chk_text.pack(side="left", padx=12)

        # Botões da direita (ordem de pack para visual correto)
        self.btn_download_pdf = ctk.CTkButton(self, text="Baixar PDF", command=on_download_pdf)
        self.btn_download_pdf.pack(side="right", padx=8, pady=6)
        self.btn_download_img = ctk.CTkButton(self, text="Baixar imagem", command=on_download_image)
        self.btn_download_img.pack(side="right", padx=8, pady=6)

        # Novo botão Conversor PDF (pack por último para ficar à esquerda dos downloads)
        self.btn_converter = ctk.CTkButton(self, text="Conversor PDF", command=on_open_converter or (lambda: None))
        self.btn_converter.pack(side="right", padx=8, pady=6)

        # Se callback não fornecido, desabilita botão
        if on_open_converter is None:
            from src.ui.widget_state import set_disabled

            set_disabled(self.btn_converter)

    def _handle_toggle_text(self) -> None:
        """Propaga o valor atual do toggle de texto para o callback da view."""
        callback = getattr(self, "_on_toggle_text", None)
        if callback is not None:
            callback(bool(self.var_text.get()))
