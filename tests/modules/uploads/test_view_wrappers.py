from __future__ import annotations

from src.modules.uploads import view as uploads_view


def test_open_files_browser_delegates_to_modular_impl(monkeypatch):
    calls = {}

    def fake_open(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return "window"

    monkeypatch.setattr("src.modules.uploads.views.browser.open_files_browser", fake_open)

    result = uploads_view.open_files_browser("parent", org_id="ORG", client_id=10, bucket="bkt")

    assert result == "window"
    assert calls["args"][0] == "parent"
    assert calls["kwargs"]["org_id"] == "ORG"
    assert calls["kwargs"]["bucket"] == "bkt"


def test_uploads_frame_alias(monkeypatch):
    def fake_open(*_args, **_kwargs):
        return "frame-window"

    monkeypatch.setattr("src.modules.uploads.views.browser.open_files_browser", fake_open)

    result = uploads_view.UploadsFrame("parent", org_id="ORG", client_id=99)
    assert result == "frame-window"
