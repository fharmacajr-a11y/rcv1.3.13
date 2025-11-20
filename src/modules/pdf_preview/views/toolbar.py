from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class PdfToolbar(ttk.Frame):
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
    ) -> None:
        super().__init__(master)

        self.var_text = tk.BooleanVar(value=False)

        ttk.Button(self, text="\u2212", width=3, command=on_zoom_out).pack(side="left", padx=(8, 0), pady=6)
        ttk.Button(self, text="100%", command=on_zoom_100).pack(side="left", padx=4, pady=6)
        ttk.Button(self, text="+", width=3, command=on_zoom_in).pack(side="left", padx=4, pady=6)
        ttk.Button(self, text="Largura", command=on_fit_width).pack(side="left", padx=8, pady=6)

        self.lbl_page = ttk.Label(self, text="Página 1/1")
        self.lbl_page.pack(side="left", padx=12)
        self.lbl_zoom = ttk.Label(self, text="100%")
        self.lbl_zoom.pack(side="left", padx=6)

        self.chk_text = ttk.Checkbutton(
            self,
            text="Texto",
            variable=self.var_text,
            command=lambda: on_toggle_text(self.var_text.get()),
        )
        self.chk_text.pack(side="left", padx=12)

        self.btn_download_pdf = ttk.Button(self, text="Baixar PDF", command=on_download_pdf)
        self.btn_download_pdf.pack(side="right", padx=8, pady=6)
        self.btn_download_img = ttk.Button(self, text="Baixar imagem", command=on_download_image)
        self.btn_download_img.pack(side="right", padx=8, pady=6)
