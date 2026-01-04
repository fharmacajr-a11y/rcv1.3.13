# tests/test_infra_storage_client_fase42.py
"""
Testes para infra/supabase/storage_client.py (COV-INFRA-SUPABASE-STORAGE).
Cobrem paths felizes e ramos de erro de baixar_pasta_zip e helpers.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import threading
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest
from requests import exceptions as req_exc


@pytest.fixture
def storage_client(monkeypatch):
    """Isola import com stub de infra.supabase_client para evitar circular."""
    stub_client_mod = ModuleType("src.infra.supabase_client")
    stub_client_mod.supabase = SimpleNamespace(storage=SimpleNamespace(from_=MagicMock()))
    monkeypatch.setitem(sys.modules, "src.infra.supabase_client", stub_client_mod)
    sys.modules.pop("src.infra.supabase.storage_client", None)
    module = importlib.import_module("src.infra.supabase.storage_client")
    return module


def make_response(
    status=200,
    headers=None,
    content=b"",
    json_data=None,
    text_data="",
    chunks=None,
):
    """Cria resposta fake compatível com uso no cliente."""
    headers = headers or {}
    chunks = chunks if chunks is not None else [content]

    class FakeResp:
        def __init__(self):
            self.status_code = status
            self.headers = headers
            self._json = json_data
            self.text = text_data
            self.raw = SimpleNamespace(decode_content=False)
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.closed = True

        def json(self):
            if isinstance(self._json, Exception):
                raise self._json
            return self._json

        def close(self):
            self.closed = True

        def iter_content(self, chunk_size=1024):
            yield from chunks

    return FakeResp()


def test_pick_name_from_content_disposition(storage_client):
    mod = storage_client
    fallback = "default.zip"
    assert mod._pick_name_from_cd("", fallback) == fallback
    cd = "attachment; filename*=UTF-8''my%20file.zip"
    assert mod._pick_name_from_cd(cd, fallback) == "my file.zip"
    assert mod._pick_name_from_cd("attachment; name=foo", fallback) == fallback


def test_downloads_dir_fallback(monkeypatch, storage_client, tmp_path):
    mod = storage_client
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(mod.Path, "home", staticmethod(lambda: fake_home))
    path = mod._downloads_dir()
    assert path == mod.Path(tempfile.gettempdir())


def test_sess_creates_once(storage_client, monkeypatch):
    mod = storage_client
    fake_session = object()
    mod._session = None
    monkeypatch.setattr(mod, "make_session", lambda: fake_session)

    first = mod._sess()
    second = mod._sess()

    assert first is fake_session
    assert second is fake_session


def test_baixar_pasta_zip_success(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    content = b"data"
    resp = make_response(
        status=200,
        headers={
            "Content-Type": "application/zip",
            "Content-Disposition": 'attachment; filename="bundle.zip"',
            "Content-Length": str(len(content)),
        },
        chunks=[content],
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    path = mod.baixar_pasta_zip("bucket", "prefix/files", timeout_s=5)

    assert path.exists()
    assert path.read_bytes() == content
    assert session.get.call_args.kwargs["params"]["bucket"] == "bucket"
    assert session.get.call_args.kwargs["params"]["prefix"] == "prefix/files"


def test_baixar_pasta_zip_status_error_uses_json(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    resp = make_response(
        status=500,
        json_data={"error": "boom"},
        text_data="ignored",
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    with pytest.raises(RuntimeError) as exc:
        mod.baixar_pasta_zip("b", "p")

    assert "HTTP 500" in str(exc.value)


def test_baixar_pasta_zip_status_error_uses_text(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    resp = make_response(status=404, json_data=ValueError("no json"), text_data="plain detail")
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    with pytest.raises(RuntimeError) as exc:
        mod.baixar_pasta_zip("b", "p")

    assert "plain detail" in str(exc.value)


def test_baixar_pasta_zip_bad_content_type_uses_text(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    resp = make_response(
        status=200,
        headers={"Content-Type": "application/json"},
        json_data=ValueError("no json"),
        text_data="fallback detail",
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    with pytest.raises(RuntimeError) as exc:
        mod.baixar_pasta_zip("bucket", "prefix")

    assert "Content-Type=application/json" in str(exc.value)
    assert "fallback detail" in str(exc.value)


def test_baixar_pasta_zip_timeout(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    session = MagicMock()
    session.get.side_effect = req_exc.Timeout("late")
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    with pytest.raises(TimeoutError):
        mod.baixar_pasta_zip("bucket", "prefix")


def test_baixar_pasta_zip_request_exception(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    session = MagicMock()
    session.get.side_effect = req_exc.RequestException("net down")
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    with pytest.raises(RuntimeError) as exc:
        mod.baixar_pasta_zip("bucket", "prefix")

    assert "Falha de rede" in str(exc.value)


def test_baixar_pasta_zip_cancelled(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    content = b"abc"
    cancel_event = threading.Event()
    cancel_event.set()
    resp = make_response(
        status=200,
        headers={"Content-Type": "application/zip", "Content-Length": str(len(content))},
        chunks=[content],
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    with pytest.raises(mod.DownloadCancelledError):
        mod.baixar_pasta_zip("bucket", "prefix", out_dir=tmp_path, cancel_event=cancel_event)

    part_files = list(tmp_path.glob("*.part"))
    assert not part_files


def test_baixar_pasta_zip_truncated(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    content = b"short"
    resp = make_response(
        status=200,
        headers={
            "Content-Type": "application/zip",
            "Content-Length": "999",
        },
        chunks=[content],
    )
    original_unlink = mod.Path.unlink

    def raising_unlink(self, missing_ok=False):
        raise OSError("cannot delete")

    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)
    monkeypatch.setattr(mod.Path, "unlink", raising_unlink)

    with pytest.raises(IOError):
        mod.baixar_pasta_zip("bucket", "prefix", out_dir=tmp_path)

    monkeypatch.setattr(mod.Path, "unlink", original_unlink)
    # Como unlink falhou, o .part pode permanecer; garantir que limpamos o patch
    assert list(tmp_path.glob("*.part"))


def test_baixar_pasta_zip_empty_chunk_and_progress(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    progress_calls = []

    def progress_cb(n):
        progress_calls.append(n)
        raise RuntimeError("progress fail")

    chunks = [b"", b"abc"]
    resp = make_response(
        status=200,
        headers={"Content-Type": "application/zip", "Content-Length": "3"},
        chunks=chunks,
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    path = mod.baixar_pasta_zip("bucket", "prefix", out_dir=tmp_path, progress_cb=progress_cb)

    assert path.read_bytes() == b"abc"
    assert progress_calls == [3]


def test_baixar_pasta_zip_cancel_after_write(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    cancel_event = threading.Event()

    def progress_cb(_):
        cancel_event.set()

    resp = make_response(
        status=200,
        headers={"Content-Type": "application/zip", "Content-Length": "3"},
        chunks=[b"abc"],
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    with pytest.raises(mod.DownloadCancelledError):
        mod.baixar_pasta_zip("bucket", "prefix", out_dir=tmp_path, cancel_event=cancel_event, progress_cb=progress_cb)


def test_baixar_pasta_zip_cancel_after_write_unlink_failure(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    cancel_event = threading.Event()

    def progress_cb(_):
        cancel_event.set()

    resp = make_response(
        status=200,
        headers={"Content-Type": "application/zip", "Content-Length": "3"},
        chunks=[b"abc"],
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    def raising_unlink(self, missing_ok=False):
        raise OSError("cannot unlink")

    monkeypatch.setattr(mod.Path, "unlink", raising_unlink)

    with pytest.raises(mod.DownloadCancelledError):
        mod.baixar_pasta_zip("bucket", "prefix", out_dir=tmp_path, cancel_event=cancel_event, progress_cb=progress_cb)


def test_baixar_pasta_zip_validation_errors(storage_client):
    mod = storage_client
    with pytest.raises(ValueError):
        mod.baixar_pasta_zip("", "p")
    with pytest.raises(ValueError):
        mod.baixar_pasta_zip("b", "")


def test_baixar_pasta_zip_duplicate_name_and_len_parse(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    existing = tmp_path / "files.zip"
    existing.write_bytes(b"x")
    content = b"ok"
    resp = make_response(
        status=200,
        headers={
            "Content-Type": "application/zip",
            "Content-Disposition": 'attachment; filename="files.zip"',
            "Content-Length": "not-a-number",
        },
        chunks=[content],
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)
    monkeypatch.setattr(mod, "CLOUD_ONLY", False)

    path = mod.baixar_pasta_zip("bucket", "prefix/files", out_dir=tmp_path)

    assert path.name == "files (1).zip"
    assert path.read_bytes() == content


def test_baixar_pasta_zip_cleanup_errors_in_cancel(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    cancel_event = threading.Event()
    cancel_event.set()
    resp = make_response(
        status=200,
        headers={"Content-Type": "application/zip", "Content-Length": "3"},
        chunks=[b"abc"],
    )
    session = MagicMock()
    session.get.return_value = resp
    monkeypatch.setattr(mod, "_sess", lambda: session)
    monkeypatch.setattr(mod, "_downloads_dir", lambda: tmp_path)

    class FakeFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, data):
            return len(data)

        def close(self):
            raise RuntimeError("close failed")

    def raising_unlink(self, missing_ok=False):
        raise OSError("cannot unlink")

    import builtins

    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: FakeFile())
    monkeypatch.setattr(mod.Path, "unlink", raising_unlink)

    with pytest.raises(mod.DownloadCancelledError):
        mod.baixar_pasta_zip("bucket", "prefix", out_dir=tmp_path, cancel_event=cancel_event)


def test_build_client_prefix_requires_id(storage_client):
    mod = storage_client
    with pytest.raises(ValueError):
        mod.build_client_prefix("org", "cnpj", client_id=None)


def test_build_client_prefix_success(storage_client):
    mod = storage_client
    prefix = mod.build_client_prefix("org", "cnpj", client_id=123)
    assert prefix == "org/123"


def test_ensure_client_storage_prefix_success(tmp_path, storage_client, monkeypatch):
    mod = storage_client
    uploads = {}

    class FakeBucket:
        def upload(self, key, tmp_path, options):
            uploads["key"] = key
            uploads["path"] = tmp_path
            uploads["options"] = options
            return SimpleNamespace(data="ok")

    fake_storage = SimpleNamespace(from_=lambda bucket: FakeBucket())
    fake_supabase = SimpleNamespace(storage=fake_storage)
    monkeypatch.setitem(sys.modules, "src.infra.supabase_client", SimpleNamespace(supabase=fake_supabase))

    prefix = mod.ensure_client_storage_prefix("bucket", "org", "cnpj", client_id=5)

    assert prefix == "org/5"
    assert uploads["key"] == "org/5/.keep"
    assert uploads["options"]["upsert"] == "true"
    assert not os.path.exists(uploads["path"])


def test_ensure_client_storage_prefix_propagates_error(tmp_path, storage_client, monkeypatch):
    mod = storage_client

    class ExplodingBucket:
        def upload(self, key, tmp_path, options):
            raise RuntimeError("boom")

    fake_storage = SimpleNamespace(from_=lambda bucket: ExplodingBucket())
    fake_supabase = SimpleNamespace(storage=fake_storage)
    monkeypatch.setitem(sys.modules, "src.infra.supabase_client", SimpleNamespace(supabase=fake_supabase))

    with pytest.raises(RuntimeError):
        mod.ensure_client_storage_prefix("b", "org", "cnpj", client_id=1)


def test_ensure_client_storage_prefix_cleanup_warning(tmp_path, storage_client, monkeypatch):
    mod = storage_client

    class DummyBucket:
        def upload(self, key, tmp_path, options):
            return SimpleNamespace(data="ok")

    fake_storage = SimpleNamespace(from_=lambda bucket: DummyBucket())
    fake_supabase = SimpleNamespace(storage=fake_storage)
    removed_paths = []

    def fake_remove(path):
        removed_paths.append(path)
        raise OSError("cannot remove")

    monkeypatch.setitem(sys.modules, "src.infra.supabase_client", SimpleNamespace(supabase=fake_supabase))
    monkeypatch.setattr(mod.os, "remove", fake_remove)

    prefix = mod.ensure_client_storage_prefix("b", "org", "cnpj", client_id=9)

    assert prefix == "org/9"
    assert removed_paths


def test_slugify_variations(storage_client):
    mod = storage_client
    assert mod._slugify("") == ""
    assert mod._slugify("Café & Co.") == "cafe-co"
