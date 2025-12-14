from __future__ import annotations

from pathlib import Path

import pytest

import src.modules.uploads.uploader_supabase as uploader
from src.modules.uploads.service import UploadItem


class DummyProgress:
    def __init__(self, _parent=None, total=0):
        self.calls = []

    def after(self, _delay, callback):
        callback()

    def advance(self, label):
        self.calls.append(label)

    def update_idletasks(self):
        pass

    def update(self):
        pass

    def close(self):
        pass


class DummyThread:
    def __init__(self, target, daemon):
        self._target = target

    def start(self):
        self._target()

    def is_alive(self):
        return False

    def join(self, timeout=None):
        pass


class AliveThread:
    def __init__(self, target, daemon):
        self._target = target
        self._alive = True

    def start(self):
        self._target()

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self._alive = False


class FailingAfterProgress(DummyProgress):
    def after(self, _delay, _callback):
        raise RuntimeError("after fail")


@pytest.fixture(autouse=True)
def stub_messagebox(monkeypatch):
    calls = {"info": [], "warn": [], "ask": []}
    monkeypatch.setattr(uploader.messagebox, "showinfo", lambda title, msg, **_: calls["info"].append((title, msg)))
    monkeypatch.setattr(uploader.messagebox, "showwarning", lambda title, msg, **_: calls["warn"].append((title, msg)))
    monkeypatch.setattr(
        uploader.messagebox, "askyesno", lambda title, msg, **_: calls["ask"].append((title, msg)) or False
    )
    return calls


def test_select_pdfs_dialog(monkeypatch):
    monkeypatch.setattr(uploader.filedialog, "askopenfilenames", lambda **_: ["a.pdf", "b.pdf"])
    assert uploader._select_pdfs_dialog() == ["a.pdf", "b.pdf"]


def test_show_upload_summary_warning_and_info(monkeypatch, stub_messagebox):
    # Cria um item fake para simular falha de upload
    from src.modules.uploads.service import UploadItem
    from pathlib import Path

    fake_item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    uploader._show_upload_summary(ok_count=1, failed_items=[(fake_item, Exception("test"))], parent=None)
    uploader._show_upload_summary(ok_count=2, failed_items=[], parent=None)
    # A nova implementação usa títulos diferentes:
    # - "Envio concluído com falhas" quando ok_count > 0 e há falhas
    # - "Envio concluído" quando não há falhas
    assert stub_messagebox["warn"][0][0] == "Envio concluído com falhas"
    assert stub_messagebox["info"][0][0] == "Envio concluído"


def test_ensure_client_saved_or_abort(monkeypatch):
    class App:
        def ensure_client_saved_for_upload(self, cid):
            return cid == 1

    assert uploader.ensure_client_saved_or_abort(App(), 1) is True
    assert uploader.ensure_client_saved_or_abort(object(), 2) is True


def test_confirm_large_volume(monkeypatch, stub_messagebox):
    monkeypatch.setattr(uploader, "VOLUME_CONFIRM_THRESHOLD", 1)
    monkeypatch.setattr(uploader.messagebox, "askyesno", lambda *_args, **_kwargs: False)
    assert uploader._confirm_large_volume(parent=None, total=1) is True
    assert uploader._confirm_large_volume(parent=None, total=2) is False


def test_upload_batch_success(monkeypatch):
    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    monkeypatch.setattr(uploader, "UploadProgressDialog", DummyProgress)
    monkeypatch.setattr("threading.Thread", DummyThread)
    monkeypatch.setattr(uploader.uploads_service, "upload_items_for_client", lambda *args, **kwargs: (1, []))

    ok, failures = uploader._upload_batch(
        app=type("App", (), {"supabase": "sb"})(),
        items=[item],
        cnpj_digits="123",
        subfolder=None,
        parent=None,
        bucket="bucket",
        client_id=1,
        org_id="ORG",
    )

    assert ok == 1 and failures == []


def test_upload_batch_error_raises(monkeypatch):
    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    monkeypatch.setattr(uploader, "UploadProgressDialog", DummyProgress)
    monkeypatch.setattr("threading.Thread", DummyThread)

    def boom(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(uploader.uploads_service, "upload_items_for_client", boom)

    with pytest.raises(RuntimeError, match="fail"):
        uploader._upload_batch(
            app=type("App", (), {"supabase": "sb"})(),
            items=[item],
            cnpj_digits="123",
            subfolder=None,
            parent=None,
        )


def test_upload_batch_progress_callback(monkeypatch):
    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    monkeypatch.setattr(uploader, "UploadProgressDialog", DummyProgress)
    monkeypatch.setattr("threading.Thread", DummyThread)

    def uploader_fn(*args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback(item)
        return (1, [])

    monkeypatch.setattr(uploader.uploads_service, "upload_items_for_client", uploader_fn)
    ok, failures = uploader._upload_batch(
        app=type("App", (), {"supabase": "sb"})(),
        items=[item],
        cnpj_digits="123",
        subfolder=None,
        parent=None,
    )
    assert ok == 1 and failures == []


def test_upload_batch_loop_updates(monkeypatch):
    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    monkeypatch.setattr(uploader, "UploadProgressDialog", DummyProgress)
    monkeypatch.setattr("threading.Thread", AliveThread)
    monkeypatch.setattr(uploader.uploads_service, "upload_items_for_client", lambda *args, **kwargs: (0, []))
    ok, failures = uploader._upload_batch(
        app=type("App", (), {"supabase": "sb"})(),
        items=[item],
        cnpj_digits="123",
        subfolder=None,
        parent=None,
    )
    assert ok == 0 and failures == []


def test_upload_batch_after_failure_logs(monkeypatch, caplog):
    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    monkeypatch.setattr(uploader, "UploadProgressDialog", FailingAfterProgress)
    monkeypatch.setattr("threading.Thread", DummyThread)

    def uploader_fn(*args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback(item)
        return (1, [])

    monkeypatch.setattr(uploader.uploads_service, "upload_items_for_client", uploader_fn)
    with caplog.at_level("DEBUG", logger=uploader.log.name):
        ok, failures = uploader._upload_batch(
            app=type("App", (), {"supabase": "sb"})(),
            items=[item],
            cnpj_digits="123",
            subfolder=None,
            parent=None,
        )
    assert ok == 1 and failures == []
    assert any("Failed to schedule callback" in rec.getMessage() for rec in caplog.records)


def test_upload_files_to_supabase_empty_and_cancel(monkeypatch, stub_messagebox):
    assert uploader.upload_files_to_supabase(app=None, cliente={}, items=[], subpasta=None) == (0, 0)
    monkeypatch.setattr(uploader, "_confirm_large_volume", lambda *_args, **_kwargs: False)
    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    assert uploader.upload_files_to_supabase(app=None, cliente={"cnpj": "1"}, items=[item], subpasta=None) == (0, 0)


def test_upload_files_to_supabase_missing_cnpj(monkeypatch, stub_messagebox):
    monkeypatch.setattr(uploader, "_confirm_large_volume", lambda *_args, **_kwargs: True)
    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    ok, failed = uploader.upload_files_to_supabase(app=None, cliente={"cnpj": ""}, items=[item], subpasta=None)
    assert ok == 0 and failed == 1
    assert stub_messagebox["warn"][0][0] == "Envio"


def test_upload_files_to_supabase_success(monkeypatch, stub_messagebox):
    monkeypatch.setattr(uploader, "_confirm_large_volume", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        uploader, "_upload_batch", lambda *args, **kwargs: (2, [(UploadItem(Path("a"), "a"), Exception("x"))])
    )

    # Stub _show_upload_summary com a nova assinatura (failed_items em vez de failed_paths)
    def fake_show_summary(ok_count, failed_items, *, parent=None, validation_errors=None):
        # Extrai os paths dos failed_items para compatibilidade com asserção existente
        paths = [
            str(Path(item.relative_path).name) if hasattr(item, "relative_path") else str(item)
            for item, _ in failed_items
        ]
        stub_messagebox["info"].append((ok_count, paths))

    monkeypatch.setattr(uploader, "_show_upload_summary", fake_show_summary)

    # Stub validate_upload_files para evitar validação de arquivos físicos
    from src.modules.uploads.file_validator import FileValidationResult

    monkeypatch.setattr(
        uploader,
        "validate_upload_files",
        lambda paths: (
            [
                FileValidationResult(valid=True, path=Path(p), size_bytes=1024, extension=".pdf", error=None)
                for p in paths
            ],
            [],
        ),
    )

    # Logger stub com todos os métodos necessários
    class L:
        @staticmethod
        def debug(*args, **kwargs):
            pass

        @staticmethod
        def info(*args, **kwargs):
            pass

        @staticmethod
        def warning(*args, **kwargs):
            pass

        @staticmethod
        def error(*args, **kwargs):
            pass

    monkeypatch.setattr(uploader, "log", L)

    class App:
        supabase = "sb"

    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    ok, failed = uploader.upload_files_to_supabase(
        app=App(), cliente={"cnpj": "12.345"}, items=[item], subpasta=None, client_id=1
    )
    assert ok == 2 and failed == 1
    assert stub_messagebox["info"][-1][1] == ["a"]


def test_send_to_supabase_interactive_no_selection(monkeypatch, stub_messagebox):
    monkeypatch.setattr(uploader, "_resolve_selected_cliente", lambda _app: None)
    assert uploader.send_to_supabase_interactive(app=None) == (0, 0)
    assert stub_messagebox["info"][0][0] == "Envio"


def test_send_to_supabase_interactive_missing_files(monkeypatch, stub_messagebox):
    monkeypatch.setattr(uploader, "_resolve_selected_cliente", lambda _app: (1, {"CNPJ": "123"}))
    monkeypatch.setattr(uploader, "ensure_client_saved_or_abort", lambda _app, _cid: False)
    assert uploader.send_to_supabase_interactive(app=None) == (0, 0)

    monkeypatch.setattr(uploader, "ensure_client_saved_or_abort", lambda _app, _cid: True)
    monkeypatch.setattr(uploader, "_select_pdfs_dialog", lambda parent=None: [])
    assert uploader.send_to_supabase_interactive(app=None) == (0, 0)

    monkeypatch.setattr(uploader, "_select_pdfs_dialog", lambda parent=None: ["a.pdf"])
    monkeypatch.setattr(uploader, "build_items_from_files", lambda files: [])
    assert uploader.send_to_supabase_interactive(app=None) == (0, 0)
    assert stub_messagebox["warn"][-1][0] == "Envio"


def test_send_to_supabase_interactive_success(monkeypatch):
    monkeypatch.setattr(uploader, "_resolve_selected_cliente", lambda _app: (1, {"CNPJ": "123"}))
    monkeypatch.setattr(uploader, "ensure_client_saved_or_abort", lambda _app, _cid: True)
    monkeypatch.setattr(uploader, "_select_pdfs_dialog", lambda parent=None: ["a.pdf"])
    item = UploadItem(path=Path("a.pdf"), relative_path="a.pdf")
    monkeypatch.setattr(uploader, "build_items_from_files", lambda files: [item])
    monkeypatch.setattr(uploader, "upload_files_to_supabase", lambda *args, **kwargs: (1, 0))
    assert uploader.send_to_supabase_interactive(app=None) == (1, 0)


def test_resolve_selected_cliente_variants():
    class Frame:
        _col_order = ("ID", "CNPJ")

    class App:
        def _selected_main_values(self):
            return (5, "123")

        def _main_screen_frame(self):
            return Frame()

    assert uploader._resolve_selected_cliente(App()) == (5, {"ID": "5", "CNPJ": "123"})

    class App2:
        def _selected_main_values(self):
            return ("10",)

    assert uploader._resolve_selected_cliente(App2()) == (10, {"0": "10"})


def test_ask_storage_subfolder(monkeypatch):
    class FakeDialog:
        def __init__(self, parent, default=""):
            self.result = "sub"

    class Parent:
        def wait_window(self, dialog):
            self.dialog = dialog

    # Patch no lugar correto onde uploader_supabase importa SubpastaDialog
    monkeypatch.setattr("src.modules.clientes.forms.client_subfolder_prompt.SubpastaDialog", FakeDialog)
    parent = Parent()
    assert uploader.ask_storage_subfolder(parent) == "sub"


def test_progress_dialog_constructs(monkeypatch):
    calls = {"messages": [], "details": [], "values": [], "closed": 0, "after": 0, "updates": 0}

    class DummyProgress:
        def __init__(self, *_args, **_kwargs):
            calls["instance"] = self

        def after(self, delay, callback):
            calls["after"] += 1
            return callback

        def update_idletasks(self):
            calls["updates"] += 1

        def update(self):
            calls["updates"] += 1

        def set_message(self, text):
            calls["messages"].append(text)

        def set_detail(self, text):
            calls["details"].append(text)

        def set_progress(self, value):
            calls["values"].append(value)

        def close(self):
            calls["closed"] += 1

    monkeypatch.setattr("src.modules.uploads.uploader_supabase.ProgressDialog", DummyProgress)

    dlg = uploader.UploadProgressDialog(parent=object(), total=2)
    dlg.after(0, lambda: None)
    dlg.update_idletasks()
    dlg.update()
    dlg.advance("test")
    dlg.close()

    assert calls["messages"] == ["test"]
    assert calls["details"][-1].startswith("1/2")
    assert calls["values"][-1] == 0.5
    assert calls["closed"] == 1


def test_send_folder_to_supabase_paths(monkeypatch, stub_messagebox):
    monkeypatch.setattr(uploader, "_resolve_selected_cliente", lambda _app: None)
    assert uploader.send_folder_to_supabase(app=None) == (0, 0)
    assert stub_messagebox["info"][-1][0] == "Envio"

    monkeypatch.setattr(uploader, "_resolve_selected_cliente", lambda _app: (1, {"CNPJ": "123"}))
    monkeypatch.setattr(uploader, "ensure_client_saved_or_abort", lambda _app, _cid: False)
    assert uploader.send_folder_to_supabase(app=None) == (0, 0)

    monkeypatch.setattr(uploader, "ensure_client_saved_or_abort", lambda _app, _cid: True)
    monkeypatch.setattr(uploader.filedialog, "askdirectory", lambda **_: "")
    assert uploader.send_folder_to_supabase(app=None) == (0, 0)

    monkeypatch.setattr(uploader.filedialog, "askdirectory", lambda **_: "/tmp/folder")
    monkeypatch.setattr(uploader, "collect_pdfs_from_folder", lambda folder: [])
    assert uploader.send_folder_to_supabase(app=None) == (0, 0)

    monkeypatch.setattr(uploader, "collect_pdfs_from_folder", lambda folder: [UploadItem(Path("a.pdf"), "a.pdf")])
    monkeypatch.setattr(uploader, "upload_files_to_supabase", lambda *args, **kwargs: ("ok", "fail"))
    result = uploader.send_folder_to_supabase(app=None)
    assert result == ("ok", "fail")
