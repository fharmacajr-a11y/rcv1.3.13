from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from src.modules.pdf_preview.views import main_window as pdf_view_main
from src.modules.pdf_preview.views.main_window import PdfPreviewController, PdfViewerWin


class DummyController:
    def __init__(self, *, page_count: int = 3, zoom: float = 1.0) -> None:
        self.state = types.SimpleNamespace(page_count=page_count, current_page=0, zoom=zoom, show_text=False)
        self.page_sizes = [(400, 600)] * max(1, page_count)
        self.text_buffer = ["texto"] * max(1, page_count)
        self.calls: list[tuple[str, Any]] = []

    def apply_zoom_delta(self, wheel_steps: float, *, step: float = PdfPreviewController.ZOOM_STEP) -> float:
        self.calls.append(("apply_zoom_delta", wheel_steps, step))
        self.state.zoom = max(
            PdfPreviewController.MIN_ZOOM, min(PdfPreviewController.MAX_ZOOM, self.state.zoom + wheel_steps * step)
        )
        return self.state.zoom

    def go_to_page(self, index: int) -> None:
        self.calls.append(("go_to_page", index))
        total = max(1, self.state.page_count)
        self.state.current_page = max(0, min(index, total - 1))

    def get_render_state(self):
        return types.SimpleNamespace(
            page_index=self.state.current_page,
            page_count=self.state.page_count,
            zoom=self.state.zoom,
            show_text=self.state.show_text,
        )

    def get_page_label(self, prefix: str = "Pagina") -> str:
        self.calls.append(("get_page_label", prefix))
        return f"{prefix} {self.state.current_page + 1}/{max(1, self.state.page_count)}"

    def set_show_text(self, value: bool) -> bool:
        self.calls.append(("set_show_text", value))
        self.state.show_text = bool(value)
        return self.state.show_text

    def set_zoom(self, zoom: float, *, fit_mode: str | None = None) -> None:
        self.calls.append(("set_zoom", zoom, fit_mode))
        self.state.zoom = zoom

    def get_page_pixmap(self, page_index: int, zoom: float):
        self.calls.append(("get_page_pixmap", page_index, zoom))
        return types.SimpleNamespace(pixmap=None, width=400, height=600, zoom=zoom)

    def close(self) -> None:
        self.calls.append(("close", None))


@pytest.fixture
def pdf_viewer(tk_root, monkeypatch):
    monkeypatch.setattr(pdf_view_main, "show_centered", lambda win: None)
    viewer = PdfViewerWin(tk_root)
    yield viewer
    try:
        if viewer.winfo_exists():
            viewer.destroy()
    except Exception:
        pass


def _install_fake_messagebox(monkeypatch):
    import tkinter as tk_mod

    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _record(kind: str):
        def _inner(*args: Any, **kwargs: Any):
            calls.append((kind, args, kwargs))

        return _inner

    module = types.SimpleNamespace(
        showinfo=_record("info"),
        showwarning=_record("warning"),
        showerror=_record("error"),
    )
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", module)
    monkeypatch.setattr(tk_mod, "messagebox", module, raising=False)
    return calls


def test_zoom_by_delegates_to_controller(pdf_viewer):
    controller = DummyController()
    pdf_viewer._controller = controller
    pdf_viewer._empty_state_item = None  # Garantir que não há early return

    pdf_viewer._zoom_by(+2)

    assert any(call[0] == "apply_zoom_delta" and call[1] == 2 for call in controller.calls)


def test_on_toggle_text_toolbar_updates_controller_and_ui(pdf_viewer):
    controller = DummyController()
    pdf_viewer._controller = controller
    pdf_viewer._has_text = True
    pdf_viewer.var_show_text.set(False)

    pdf_viewer._on_toggle_text_toolbar(True)

    assert any(call[0] == "set_show_text" for call in controller.calls)
    assert pdf_viewer.var_show_text.get() is True
    assert pdf_viewer._pane_right_added is True


def test_update_page_label_uses_controller_render_state(pdf_viewer):
    controller = DummyController(page_count=4, zoom=1.25)
    pdf_viewer._controller = controller
    pdf_viewer.page_count = 4

    pdf_viewer._update_page_label(2)

    assert controller.state.current_page == 2
    assert pdf_viewer.lbl_page.cget("text").endswith("3/4")
    assert pdf_viewer.lbl_zoom.cget("text") == "125%"


def test_download_pdf_saves_current_bytes_and_shows_info(monkeypatch, tmp_path, pdf_viewer):
    pdf_viewer._pdf_bytes = b"binary"
    pdf_viewer._pdf_path = None
    saved: dict[str, Any] = {}

    def fake_save(data_bytes: bytes | None, source_path: str | None, ctx):
        saved["data_bytes"] = data_bytes
        saved["source_path"] = source_path
        saved["ctx"] = ctx
        return tmp_path / "arquivo.pdf"

    monkeypatch.setattr(pdf_view_main, "get_default_download_dir", lambda: tmp_path)
    monkeypatch.setattr(pdf_view_main, "save_pdf", fake_save)
    calls = _install_fake_messagebox(monkeypatch)

    pdf_viewer._download_pdf()

    assert saved["data_bytes"] == b"binary"
    assert saved["source_path"] is None
    assert calls[0][0] == "info"


def test_download_pdf_warns_when_no_source(monkeypatch, tmp_path, pdf_viewer):
    pdf_viewer._pdf_bytes = None
    pdf_viewer._pdf_path = "missing.pdf"

    monkeypatch.setattr(pdf_view_main.os.path, "exists", lambda path: False)
    monkeypatch.setattr(pdf_view_main, "get_default_download_dir", lambda: tmp_path)

    def _fail(*_args, **_kwargs):
        pytest.fail("save_pdf should not be called when no PDF is loaded")

    monkeypatch.setattr(pdf_view_main, "save_pdf", _fail)
    calls = _install_fake_messagebox(monkeypatch)

    pdf_viewer._download_pdf()

    assert calls[0][0] == "warning"


def test_update_download_buttons_detects_source_type(pdf_viewer):
    pdf_viewer._update_download_buttons(source="documento.pdf")
    assert pdf_viewer.btn_download_pdf.instate(["!disabled"])
    assert pdf_viewer.btn_download_img.instate(["disabled"])

    pdf_viewer._update_download_buttons(source="foto.png")
    assert pdf_viewer.btn_download_pdf.instate(["disabled"])
    assert pdf_viewer.btn_download_img.instate(["!disabled"])
