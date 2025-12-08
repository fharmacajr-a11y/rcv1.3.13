from __future__ import annotations

import logging
import tkinter as tk
from tkinter import TclError, ttk
from typing import Callable, Literal

logger = logging.getLogger(__name__)

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
        self._current_image: tk.PhotoImage | None = None
        # Usa tk.Scrollbar ao invés de ttk.Scrollbar para evitar crash de
        # access violation em Python 3.13 + ttkbootstrap (element_create bug)
        vs = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
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

    def _resolve_canvas_dimension(self, option: Literal["width", "height"], requested: int) -> int:
        """Resolve canvas dimension even when widget is unmapped/headless."""
        try:
            configured = int(self.canvas.cget(option))
        except (TclError, ValueError, TypeError):
            configured = 0

        req = self.canvas.winfo_reqwidth() if option == "width" else self.canvas.winfo_reqheight()
        return max(configured, req, requested, 1)

    def show_image(self, image: tk.PhotoImage | None, width: int, height: int) -> None:
        """
        Desenha a imagem centralizada no canvas e ajusta scrollregion.
        Reaproveita lógica atual de renderização.
        """
        # Guarda None se não tiver imagem – saída precoce
        if image is None:
            self._current_image = None
            return

        # Processa eventos pendentes para garantir dimensões atualizadas
        self.canvas.update_idletasks()

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        # Fallback síncrono: se canvas não mapeado (withdraw/headless), usa cget/reqwidth/height
        # ou a dimensão da imagem. Evita self.after() que causa flakiness em testes.
        if cw <= 1:
            cw = self._resolve_canvas_dimension("width", width)
        if ch <= 1:
            ch = self._resolve_canvas_dimension("height", height)

        self.canvas.delete("all")

        render_image = image
        image_tk = getattr(image, "tk", None)
        canvas_tk = getattr(self.canvas, "tk", None)
        if image_tk is not None and canvas_tk is not None and image_tk is not canvas_tk:
            render_image = tk.PhotoImage(
                master=self.canvas,
                width=max(width, 1),
                height=max(height, 1),
            )

        self._current_image = render_image

        if cw <= 0 or ch <= 0:
            # Canvas ainda sem dimensões válidas; guarda imagem e tenta renderizar depois.
            return

        try:
            self.canvas.create_image(cw // 2, ch // 2, image=self._current_image, anchor="center")
        except TclError as exc:
            # Em casos raros, Tk pode já ter descartado a imagem.
            # Não queremos travar o app por isso; registramos e seguimos.
            logger.debug(
                "Falha ao renderizar imagem no PdfPageView (canvas=%sx%s, image=%sx%s): %s",
                cw,
                ch,
                width,
                height,
                exc,
            )
            self._current_image = None
            return

        region_w = max(width, cw)
        region_h = max(height, ch)
        self.canvas.configure(scrollregion=(0, 0, region_w, region_h))
