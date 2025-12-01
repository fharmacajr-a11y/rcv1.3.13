from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable

from src.ui.search_nav import SearchNavigator

logger = logging.getLogger(__name__)


class PdfTextPanel(ttk.Frame):
    """
    Painel de texto/OCR:
    - contém o widget Text/ScrolledText;
    - oferece API para setar texto, limpar e focar;
    - integra com SearchNavigator / atalhos F3/Shift+F3.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_search_next: Callable[[str], None],
        on_search_prev: Callable[[str], None],
    ) -> None:
        super().__init__(master)

        self.text = ScrolledText(self, wrap="word", height=10)
        self.text.pack(side="top", fill="both", expand=True)

        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="Copiar", command=self._copy)
        self._menu.add_command(label="Selecionar tudo", command=self._select_all)
        self.text.bind("<Button-3>", self._show_menu)

        self.search_nav = SearchNavigator(self.text)
        self.text.bind("<F3>", lambda e: (self._on_search_next(on_search_next), "break"))
        self.text.bind("<Shift-F3>", lambda e: (self._on_search_prev(on_search_prev), "break"))
        self.text.tag_raise("sel")

    def set_text(self, content: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        # Reindexar busca com a query atual, se existir
        self.search_nav.set_query(self.search_nav.query)

    def focus_text(self) -> None:
        self.text.focus_set()

    def clear(self) -> None:
        self.text.delete("1.0", "end")
        self.search_nav.set_query("")

    def _on_search_next(self, callback: Callable[[str], None]) -> None:
        self.search_nav.next()
        callback(self.search_nav.query)

    def _on_search_prev(self, callback: Callable[[str], None]) -> None:
        self.search_nav.prev()
        callback(self.search_nav.query)

    def _copy(self) -> None:
        try:
            self.text.event_generate("<<Copy>>")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao copiar texto do painel OCR: %s", exc)

    def _select_all(self) -> None:
        try:
            self.text.event_generate("<<SelectAll>>")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao selecionar texto do painel OCR: %s", exc)

    def _show_menu(self, event: tk.Event) -> str:
        self.text.focus_set()
        try:
            self._menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu.grab_release()
        return "break"
