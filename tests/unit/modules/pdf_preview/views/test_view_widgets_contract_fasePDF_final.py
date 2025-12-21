from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from src.modules.pdf_preview.views import text_panel as text_panel_mod
from src.modules.pdf_preview.views.page_view import PdfPageView
from src.modules.pdf_preview.views.text_panel import PdfTextPanel
from src.modules.pdf_preview.views.toolbar import PdfToolbar


def _button_by_text(frame: PdfToolbar, label: str) -> ttk.Button:
    for child in frame.winfo_children():
        if isinstance(child, ttk.Button) and child.cget("text") == label:
            return child
    raise AssertionError(f"Botao '{label}' nao encontrado")


def test_pdf_toolbar_dispatches_callbacks(tk_root):
    events: list[str] = []
    toggle_calls: list[bool] = []
    toolbar = PdfToolbar(
        tk_root,
        on_zoom_in=lambda: events.append("zoom_in"),
        on_zoom_out=lambda: events.append("zoom_out"),
        on_zoom_100=lambda: events.append("zoom_100"),
        on_fit_width=lambda: events.append("fit_width"),
        on_toggle_text=lambda value: toggle_calls.append(value),
        on_download_pdf=lambda: events.append("download_pdf"),
        on_download_image=lambda: events.append("download_image"),
        on_open_converter=lambda: events.append("open_converter"),
    )
    toolbar.pack()
    tk_root.update_idletasks()

    _button_by_text(toolbar, "\u2212").invoke()
    _button_by_text(toolbar, "100%").invoke()
    _button_by_text(toolbar, "+").invoke()
    _button_by_text(toolbar, "Largura").invoke()
    toolbar.chk_text.invoke()
    toolbar.chk_text.invoke()
    toolbar.btn_download_pdf.invoke()
    toolbar.btn_download_img.invoke()
    toolbar.btn_converter.invoke()

    assert {"zoom_in", "zoom_out", "zoom_100", "fit_width", "download_pdf", "download_image", "open_converter"} <= set(
        events
    )
    assert toggle_calls == [True, False]


def test_pdf_page_view_show_image_and_bindings(tk_root):
    callbacks: list[str] = []

    def _register(name: str) -> Callable[[], None]:
        return lambda: callbacks.append(name)

    view = PdfPageView(
        tk_root,
        on_page_up=_register("page_up"),
        on_page_down=_register("page_down"),
        on_page_first=_register("page_first"),
        on_page_last=_register("page_last"),
    )
    view.pack(fill="both", expand=True)
    tk_root.update()
    view.canvas.configure(width=200, height=220)
    tk_root.update()

    img = tk.PhotoImage(width=50, height=100)
    view.show_image(img, 50, 100)
    tk_root.update()

    assert len(view.canvas.find_all()) == 1
    region = tuple(int(value) for value in view.canvas.cget("scrollregion").split())
    assert region[2] >= 50 and region[3] >= 100

    assert view.canvas.bind("<Prior>")
    assert view.canvas.bind("<Next>")
    assert view.canvas.bind("<Home>")
    assert view.canvas.bind("<End>")

    view._call_and_break(_register("page_up"))
    view._call_and_break(_register("page_down"))
    view._call_and_break(_register("page_first"))
    view._call_and_break(_register("page_last"))

    assert callbacks == ["page_up", "page_down", "page_first", "page_last"]


def test_pdf_text_panel_set_text_and_search_callbacks(tk_root, monkeypatch):
    events: list[tuple[str, str]] = []

    class DummySearchNavigator:
        def __init__(self, text_widget):
            self.text_widget = text_widget
            self.query = ""

        def set_query(self, value: str) -> None:
            self.query = value
            events.append(("set_query", value))

        def next(self) -> None:
            events.append(("next", self.query))

        def prev(self) -> None:
            events.append(("prev", self.query))

    monkeypatch.setattr(text_panel_mod, "SearchNavigator", DummySearchNavigator)
    panel = PdfTextPanel(
        tk_root,
        on_search_next=lambda query: events.append(("cb_next", query)),
        on_search_prev=lambda query: events.append(("cb_prev", query)),
    )

    panel.search_nav.query = "needle"
    panel.set_text("conteudo")

    assert panel.text.get("1.0", "end-1c") == "conteudo"
    assert ("set_query", "needle") in events

    panel._on_search_next(lambda query: events.append(("manual_next", query)))
    panel._on_search_prev(lambda query: events.append(("manual_prev", query)))

    assert ("manual_next", "needle") in events
    assert ("manual_prev", "needle") in events

    panel.search_nav.query = "reset"
    panel.clear()

    assert panel.text.get("1.0", "end-1c") == ""
    assert ("set_query", "") in events
