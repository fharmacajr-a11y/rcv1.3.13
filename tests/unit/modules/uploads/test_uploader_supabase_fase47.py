"""
TESTE_1 - uploader_supabase

Objetivo: aumentar a cobertura de src/modules/uploads/uploader_supabase.py na fase 47,
cobrindo fluxos interativos de envio ao Supabase, erros esperados e casos de borda.
"""

from __future__ import annotations

from pathlib import Path
import types

import pytest

import src.modules.uploads.uploader_supabase as uploader_supabase
from src.modules.uploads.file_validator import FileValidationResult


def _stub_messagebox(monkeypatch, askyesno_return=True):
    calls = {"info": [], "warning": [], "error": [], "askyesno": []}

    def record(key, ret=None):
        def _inner(*args, **kwargs):
            calls[key].append((args, kwargs))
            return ret

        return _inner

    mb = types.SimpleNamespace(
        showinfo=record("info"),
        showwarning=record("warning"),
        showerror=record("error"),
        askyesno=record("askyesno", askyesno_return),
    )
    monkeypatch.setattr(uploader_supabase, "messagebox", mb)
    return calls


def _stub_filedialog(monkeypatch, files=None, folder=None):
    fd = types.SimpleNamespace(
        askopenfilenames=lambda **kwargs: files,
        askdirectory=lambda **kwargs: folder,
    )
    monkeypatch.setattr(uploader_supabase, "filedialog", fd)
    return fd


def _make_upload_items(*names: str):
    return [types.SimpleNamespace(path=Path(name), relative_path=name) for name in names]


@pytest.fixture(autouse=True)
def _stub_validate_upload_files(monkeypatch: pytest.MonkeyPatch):
    """Evita tocar no disco em testes de upload_files_to_supabase."""

    def _fake_validate(paths, **kwargs):
        results = []
        for path in paths:
            file_path = Path(path)
            ext = file_path.suffix or ".pdf"
            results.append(
                FileValidationResult(
                    valid=True,
                    path=file_path,
                    size_bytes=1,
                    extension=ext,
                )
            )
        return results, []

    monkeypatch.setattr(
        uploader_supabase,
        "validate_upload_files",
        _fake_validate,
    )


def test_send_to_supabase_interactive_sem_cliente_retorna_zero(monkeypatch):
    calls = _stub_messagebox(monkeypatch)
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: None)
    app = object()

    result = uploader_supabase.send_to_supabase_interactive(app)

    assert result == (0, 0)
    assert calls["info"]


def test_send_to_supabase_interactive_cliente_nao_salvo(monkeypatch):
    _stub_messagebox(monkeypatch)
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: (1, {"CNPJ": "1"}))
    monkeypatch.setattr(uploader_supabase, "ensure_client_saved_or_abort", lambda app, cid: False)
    called = {"select": False}
    monkeypatch.setattr(
        uploader_supabase, "_select_pdfs_dialog", lambda parent=None: called.__setitem__("select", True)
    )

    result = uploader_supabase.send_to_supabase_interactive(object())

    assert result == (0, 0)
    assert called["select"] is False


def test_send_to_supabase_interactive_cancel_dialogo(monkeypatch):
    calls = _stub_messagebox(monkeypatch)
    _stub_filedialog(monkeypatch, files=[])
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: (1, {"CNPJ": "123"}))
    monkeypatch.setattr(uploader_supabase, "ensure_client_saved_or_abort", lambda app, cid: True)
    app = object()

    result = uploader_supabase.send_to_supabase_interactive(app)

    assert result == (0, 0)
    assert calls["info"]  # "Nenhum arquivo selecionado."


def test_send_to_supabase_interactive_sem_items_validos(monkeypatch):
    calls = _stub_messagebox(monkeypatch)
    _stub_filedialog(monkeypatch, files=["a.pdf"])
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: (1, {"CNPJ": "123"}))
    monkeypatch.setattr(uploader_supabase, "ensure_client_saved_or_abort", lambda app, cid: True)
    monkeypatch.setattr(uploader_supabase, "build_items_from_files", lambda paths: [])

    result = uploader_supabase.send_to_supabase_interactive(object())

    assert result == (0, 0)
    assert calls["warning"]


def test_send_to_supabase_interactive_caminho_feliz_chama_upload(monkeypatch):
    _stub_messagebox(monkeypatch)
    _stub_filedialog(monkeypatch, files=["a.pdf", "b.pdf"])
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: (10, {"CNPJ": "789"}))
    monkeypatch.setattr(uploader_supabase, "ensure_client_saved_or_abort", lambda app, cid: True)
    items = _make_upload_items("a.pdf", "b.pdf")
    monkeypatch.setattr(uploader_supabase, "build_items_from_files", lambda paths: items)
    called = {}

    def fake_upload(app, cliente, items_arg, subpasta, parent=None, bucket=None, client_id=None):
        called["params"] = (cliente, items_arg, subpasta, parent, bucket, client_id)
        return (3, 1)

    monkeypatch.setattr(uploader_supabase, "upload_files_to_supabase", fake_upload)

    result = uploader_supabase.send_to_supabase_interactive(object(), default_bucket="bucket-x")

    assert result == (3, 1)
    assert called["params"][0]["cnpj"] == "789"
    assert called["params"][1] == items
    assert called["params"][3] is not None  # parent/target
    assert called["params"][4] == "bucket-x"
    assert called["params"][5] == 10


def test_upload_files_to_supabase_sem_items(monkeypatch):
    monkeypatch.setattr(
        uploader_supabase, "_confirm_large_volume", lambda parent, total: pytest.fail("nao deveria chamar")
    )
    result = uploader_supabase.upload_files_to_supabase(object(), {}, [], None)
    assert result == (0, 0)


def test_upload_files_to_supabase_confirma_false(monkeypatch):
    calls = _stub_messagebox(monkeypatch)
    monkeypatch.setattr(uploader_supabase, "_confirm_large_volume", lambda parent, total: False)
    result = uploader_supabase.upload_files_to_supabase(
        object(),
        {"cnpj": "123"},
        _make_upload_items("a.pdf"),
        None,
    )
    assert result == (0, 0)
    assert not calls["warning"]


def test_upload_files_to_supabase_sem_cnpj_mostra_warning(monkeypatch):
    calls = _stub_messagebox(monkeypatch)
    monkeypatch.setattr(uploader_supabase, "_confirm_large_volume", lambda parent, total: True)
    monkeypatch.setattr(uploader_supabase, "_upload_batch", lambda *a, **k: pytest.fail("nao deve chamar"))
    items = _make_upload_items("a.pdf", "b.pdf")

    ok, errors = uploader_supabase.upload_files_to_supabase(object(), {"cnpj": ""}, items, None)

    assert ok == 0 and errors == len(items)
    assert calls["warning"]


def test_upload_files_to_supabase_sucesso_com_bucket_e_org(monkeypatch):
    _stub_messagebox(monkeypatch)
    monkeypatch.setattr(uploader_supabase, "_confirm_large_volume", lambda parent, total: True)
    captured = {}

    def fake_batch(app, items, cnpj_digits, subfolder, parent, bucket=None, client_id=None, org_id=None):
        captured["args"] = (cnpj_digits, subfolder, bucket, client_id, org_id)
        return 2, []

    monkeypatch.setattr(uploader_supabase, "_upload_batch", fake_batch)
    monkeypatch.setattr(
        uploader_supabase,
        "_show_upload_summary",
        lambda ok_count, failed_items, parent=None, validation_errors=None: captured.__setitem__(
            "summary", (ok_count, failed_items)
        ),
    )  # noqa: E501
    monkeypatch.setattr(
        uploader_supabase, "uploads_service", types.SimpleNamespace()
    )  # silence real service usage in summary
    items = _make_upload_items("a.pdf")

    class AppStub:
        supabase = object()

    def fake_get_org(sb):
        return "org-42"

    monkeypatch.setattr("src.modules.uploads.components.helpers.get_current_org_id", fake_get_org)

    ok, errors = uploader_supabase.upload_files_to_supabase(
        AppStub(), {"cnpj": "12.345"}, items, subpasta="SUB", bucket="bucket-y", client_id=5
    )

    assert (ok, errors) == (2, 0)
    assert captured["args"] == ("12345", "SUB", "bucket-y", 5, "org-42")
    assert captured["summary"][0] == 2


def test_upload_files_to_supabase_usa_bucket_padrao_no_batch(monkeypatch):
    monkeypatch.setattr(uploader_supabase, "_confirm_large_volume", lambda parent, total: True)
    uploader_supabase.CLIENTS_BUCKET = "clientes-default"
    recorded = {}

    class DummyProgress:
        def __init__(self, parent, total):  # noqa: ANN001
            self.parent = parent
            self.total = total
            self.closed = False

        def after(self, delay, func):
            func()

        def update_idletasks(self):
            pass

        def update(self):
            pass

        def close(self):
            self.closed = True

    monkeypatch.setattr(uploader_supabase, "UploadProgressDialog", DummyProgress)

    def fake_upload_items(
        items,
        cnpj_digits,
        bucket,
        supabase_client=None,
        subfolder=None,
        progress_callback=None,
        client_id=None,
        org_id=None,
    ):
        recorded["bucket"] = bucket
        return (1, [])

    monkeypatch.setattr(uploader_supabase.uploads_service, "upload_items_for_client", fake_upload_items)

    item = types.SimpleNamespace(path=Path("file.pdf"), relative_path="file.pdf")
    ok, failures = uploader_supabase._upload_batch(
        app=types.SimpleNamespace(supabase=None),
        items=[item],
        cnpj_digits="123",
        subfolder=None,
        parent=object(),
        bucket=None,
        client_id=None,
        org_id=None,
    )

    assert (ok, failures) == (1, [])
    assert recorded["bucket"] == "clientes-default"


def test_send_folder_to_supabase_sem_cliente(monkeypatch):
    calls = _stub_messagebox(monkeypatch)
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: None)
    result = uploader_supabase.send_folder_to_supabase(object())
    assert result == (0, 0)
    assert calls["info"]


def test_send_folder_to_supabase_cancel_dialogo(monkeypatch):
    calls = _stub_messagebox(monkeypatch)
    _stub_filedialog(monkeypatch, folder="")
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: (1, {"CNPJ": "123"}))
    monkeypatch.setattr(uploader_supabase, "ensure_client_saved_or_abort", lambda app, cid: True)
    result = uploader_supabase.send_folder_to_supabase(object())
    assert result == (0, 0)
    assert calls["info"]


def test_send_folder_to_supabase_sem_pdfs(monkeypatch):
    calls = _stub_messagebox(monkeypatch)
    _stub_filedialog(monkeypatch, folder="/tmp/folder")
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: (1, {"CNPJ": "123"}))
    monkeypatch.setattr(uploader_supabase, "ensure_client_saved_or_abort", lambda app, cid: True)
    monkeypatch.setattr(uploader_supabase, "collect_pdfs_from_folder", lambda folder: [])
    result = uploader_supabase.send_folder_to_supabase(object())
    assert result == (0, 0)
    assert calls["info"]


def test_send_folder_to_supabase_caminho_feliz(monkeypatch):
    _stub_messagebox(monkeypatch)
    _stub_filedialog(monkeypatch, folder="/tmp/dircliente")
    monkeypatch.setattr(uploader_supabase, "_resolve_selected_cliente", lambda app: (9, {"CNPJ": "999"}))
    monkeypatch.setattr(uploader_supabase, "ensure_client_saved_or_abort", lambda app, cid: True)
    items = _make_upload_items("dircliente/a.pdf")
    monkeypatch.setattr(uploader_supabase, "collect_pdfs_from_folder", lambda folder: items)
    captured = {}

    def fake_upload(app, cliente, items_arg, subpasta, parent=None, bucket=None, client_id=None):
        captured["params"] = (cliente, items_arg, subpasta, bucket, client_id)
        return (1, 0)

    monkeypatch.setattr(uploader_supabase, "upload_files_to_supabase", fake_upload)

    result = uploader_supabase.send_folder_to_supabase(object(), default_bucket="bucket-z")

    assert result == (1, 0)
    assert captured["params"][0]["cnpj"] == "999"
    assert captured["params"][1] == items
    assert captured["params"][2] == "dircliente"
    assert captured["params"][3] == "bucket-z"
    assert captured["params"][4] == 9
