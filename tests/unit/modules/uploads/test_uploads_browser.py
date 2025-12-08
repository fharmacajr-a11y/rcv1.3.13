from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from src.modules.uploads.views import browser
from src.ui.files_browser.utils import sanitize_filename, suggest_zip_filename


@pytest.fixture
def make_window(
    monkeypatch: pytest.MonkeyPatch, tk_root_session: object
) -> Callable[..., browser.UploadsBrowserWindow]:
    """
    Cria UploadsBrowserWindow sem carregar estado inicial (evita chamadas de rede nos testes).
    """

    monkeypatch.setattr(browser.UploadsBrowserWindow, "_populate_initial_state", lambda self: None)
    monkeypatch.setattr(browser, "show_centered", lambda *args, **kwargs: None)

    def _factory(**kwargs):
        win = browser.UploadsBrowserWindow(
            tk_root_session,
            client_id=1,
            razao="Acme Corp",
            cnpj="12345678000199",
            bucket="bucket-test",
            base_prefix="org/1",
            **kwargs,
        )
        return win

    yield _factory


@pytest.mark.skip(reason="Método _download_folder_zip não existe mais no código")
def test_download_folder_zip_uses_service_and_destination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, make_window):
    calls: list[dict] = []

    def fake_download_folder_zip(prefix, **kwargs):
        calls.append({"prefix": prefix, "kwargs": kwargs})
        return tmp_path / "downloaded.zip"

    class ImmediateFuture:
        def __init__(self, result):
            self._result = result

        def result(self):
            return self._result

        def add_done_callback(self, cb):
            cb(self)

    class ImmediateExecutor:
        def __init__(self):
            self.submitted = []

        def submit(self, fn, *args, **kwargs):
            result = fn(*args, **kwargs)
            fut = ImmediateFuture(result)
            self.submitted.append(fut)
            return fut

    messages: list[tuple] = []

    monkeypatch.setattr(browser, "download_folder_zip", fake_download_folder_zip)
    monkeypatch.setattr(browser, "_executor", ImmediateExecutor())
    monkeypatch.setattr(browser.filedialog, "askdirectory", lambda **_kwargs: str(tmp_path))
    monkeypatch.setattr(browser.messagebox, "showinfo", lambda *args, **_kwargs: messages.append(args))
    monkeypatch.setattr(browser.messagebox, "showerror", lambda *args, **_kwargs: messages.append(args))

    win = make_window()
    win.file_list.selected_item = lambda: "docs"
    win._last_listing_map = {"docs": True}
    win.after = lambda _delay, fn, *args: fn(*args)  # type: ignore[assignment]

    expected_stem = sanitize_filename(
        f"{suggest_zip_filename('org/1/docs')} - {win._cnpj or f'ID {win._client_id}'} - {win._razao}"
    )

    try:
        win._download_folder_zip()
    finally:
        win.destroy()

    assert calls, "download_folder_zip deve ser chamado"
    call = calls[0]
    assert call["prefix"] == "org/1/docs"
    assert call["kwargs"]["bucket"] == "bucket-test"
    assert call["kwargs"]["zip_name"] == expected_stem
    assert call["kwargs"]["out_dir"] == str(tmp_path)
    assert any(msg and msg[0] == "Download concluido" for msg in messages)


@pytest.mark.skip(reason="Método _delete_selected não existe mais no código")
def test_delete_folder_uses_handler_when_provided(monkeypatch: pytest.MonkeyPatch, make_window):
    handler_calls: list[tuple[str, str]] = []

    def handler(bucket: str, prefix: str) -> None:
        handler_calls.append((bucket, prefix))

    monkeypatch.setattr(browser.messagebox, "askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(browser.messagebox, "showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        browser, "delete_storage_folder", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError())
    )

    win = make_window(delete_folder_handler=handler)
    win.file_list.selected_item = lambda: "folder"
    win._last_listing_map = {"folder": True}

    try:
        win._delete_selected()
    finally:
        win.destroy()

    assert handler_calls == [("bucket-test", "org/1/folder")]


@pytest.mark.skip(reason="Método _delete_selected não existe mais no código")
def test_delete_folder_default_path(monkeypatch: pytest.MonkeyPatch, make_window):
    delete_calls: list[tuple[str, str]] = []
    refresh_called: list[bool] = []

    def fake_delete(prefix: str, *, bucket: str | None = None):
        delete_calls.append((bucket, prefix))
        return {"ok": True, "deleted": 3, "errors": [], "message": "ok"}

    monkeypatch.setattr(browser.messagebox, "askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(browser.messagebox, "showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr(browser, "delete_storage_folder", fake_delete)

    win = make_window()
    win._refresh_listing = lambda: refresh_called.append(True)  # type: ignore[assignment]
    win.file_list.selected_item = lambda: "folder"
    win._last_listing_map = {"folder": True}

    try:
        win._delete_selected()
    finally:
        win.destroy()

    assert delete_calls == [("bucket-test", "org/1/folder")]
    assert refresh_called, "Deve atualizar listagem apos exclusao de pasta"
