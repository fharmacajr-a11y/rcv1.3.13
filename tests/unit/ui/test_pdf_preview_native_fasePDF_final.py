from __future__ import annotations

import types
from typing import Any

import pytest

import src.modules.pdf_preview.view  # noqa: F401  # garante inicialização antes do import do bridge
import src.ui.pdf_preview_native as pdf_native


class DummyMaster:
    def __init__(self) -> None:
        self.toplevel_calls = 0

    def winfo_toplevel(self):
        self.toplevel_calls += 1
        return self


@pytest.fixture
def fake_viewer_class(monkeypatch):
    class FakeViewer:
        instances: list["FakeViewer"] = []

        def __init__(self, master, pdf_path=None, display_name=None, data_bytes=None):
            self.master = master
            self.args = {
                "master": master,
                "pdf_path": pdf_path,
                "display_name": display_name,
                "data_bytes": data_bytes,
            }
            self._exists = True
            self.transient_parent = None
            self.grabbed = False
            self.focused = False
            self.open_calls: list[dict[str, Any]] = []
            self._bindings: dict[str, Any] = {}
            FakeViewer.instances.append(self)

        def winfo_exists(self):
            return self._exists

        def open_document(self, pdf_path=None, data_bytes=None, display_name=None):
            self.open_calls.append(
                {
                    "pdf_path": pdf_path,
                    "data_bytes": data_bytes,
                    "display_name": display_name,
                }
            )

        def transient(self, parent):
            self.transient_parent = parent

        def grab_set(self):
            self.grabbed = True

        def focus_canvas(self):
            self.focused = True

        def bind(self, sequence, callback, add=None):
            self._bindings[sequence] = callback
            return "bindid"

        def simulate_destroy(self):
            callback = self._bindings.get("<Destroy>")
            if callback:
                event = types.SimpleNamespace(widget=self)
                callback(event)

    monkeypatch.setattr(pdf_native, "PdfViewerWin", FakeViewer)
    monkeypatch.setattr(pdf_native, "_singleton_viewer", None)
    return FakeViewer


def test_open_pdf_viewer_creates_new_window(fake_viewer_class):
    master = DummyMaster()

    viewer = pdf_native.open_pdf_viewer(master, pdf_path="doc.pdf", display_name="Doc")

    assert viewer is fake_viewer_class.instances[0]
    assert viewer.args["pdf_path"] == "doc.pdf"
    assert viewer.transient_parent is master
    assert viewer.grabbed and viewer.focused
    assert pdf_native._singleton_viewer is viewer


def test_open_pdf_viewer_reuses_existing_window(fake_viewer_class):
    master = DummyMaster()
    first = pdf_native.open_pdf_viewer(master, pdf_path="primeiro.pdf")

    second = pdf_native.open_pdf_viewer(master, pdf_path="segundo.pdf", data_bytes=b"123", display_name="Segundo")

    assert first is second
    assert len(fake_viewer_class.instances) == 1
    assert first.open_calls[-1] == {"pdf_path": "segundo.pdf", "data_bytes": b"123", "display_name": "Segundo"}


def test_open_pdf_viewer_recreates_after_destroy(fake_viewer_class):
    master = DummyMaster()
    first = pdf_native.open_pdf_viewer(master, pdf_path="primeiro.pdf")
    first._exists = False

    second = pdf_native.open_pdf_viewer(master, pdf_path="novo.pdf")

    assert second is not first
    assert len(fake_viewer_class.instances) == 2


def test_destroy_event_resets_singleton(fake_viewer_class):
    master = DummyMaster()
    viewer = pdf_native.open_pdf_viewer(master, pdf_path="doc.pdf")

    viewer.simulate_destroy()

    assert pdf_native._singleton_viewer is None
