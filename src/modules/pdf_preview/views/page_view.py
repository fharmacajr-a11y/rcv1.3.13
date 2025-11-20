from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Literal

TkBindReturn = Literal["break"] | None
TkCallback = Callable[..., TkBindReturn]


class PdfPageView(ttk.Frame):
    """
    Área principal de visualização da página PDF:
    - contém o Canvas e as Scrollbars;
    - sabe desenhar uma imagem numa posição apropriada;
    - expõe binds básicos de scroll e clique.

    Não conhece PyMuPDF diretamente; recebe PhotoImage da janela.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_page_up: TkCallback,
        on_page_down: TkCallback,
        on_page_first: TkCallback,
        on_page_last: TkCallback,
    ) -> None:
        super().__init__(master)

        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#f3f3f3")
        vs = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vs.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")

        bindings = [
            ("<Prior>", on_page_up),
            ("<Next>", on_page_down),
            ("<Home>", on_page_first),
            ("<End>", on_page_last),
        ]
        for sequence, handler in bindings:
            self.canvas.bind(sequence, lambda e, func=handler: self._call_and_break(func))

    def _call_and_break(self, func: TkCallback) -> TkBindReturn:
        func()
        return "break"

    def show_image(self, image: tk.PhotoImage, width: int, height: int) -> None:
        """
        Desenha a imagem centralizada no canvas e ajusta scrollregion.
        Reaproveita lógica atual de renderização.
        """
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            # canvas ainda não dimensionado; tenta novamente
            self.after(20, lambda: self.show_image(image, width, height))
            return

        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=image, anchor="center")

        region_w = max(width, cw)
        region_h = max(height, ch)
        self.canvas.configure(scrollregion=(0, 0, region_w, region_h))
