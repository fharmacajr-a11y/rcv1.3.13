from __future__ import annotations

import pytest

import adapters.storage.api as storage_api


class RecordingBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def upload_file(self, local_path, remote_key, content_type):
        self.calls.append(("upload_file", (local_path, remote_key, content_type), {}))
        return "uploaded"

    def download_file(self, remote_key, local_path):
        self.calls.append(("download_file", (remote_key, local_path), {}))
        return b"data"

    def delete_file(self, remote_key):
        self.calls.append(("delete_file", (remote_key,), {}))
        return True

    def list_files(self, prefix):
        self.calls.append(("list_files", (prefix,), {}))
        return ["a.txt"]

    def download_folder_zip(self, prefix, **kwargs):
        self.calls.append(("download_folder_zip", (prefix,), kwargs))
        return f"{prefix}-zip"


@pytest.fixture(autouse=True)
def restore_backend():
    original = storage_api.get_current_backend()
    yield
    storage_api.set_storage_backend(original)


def test_file_operations_delegate_to_backend_methods():
    backend = RecordingBackend()
    with storage_api.using_storage_backend(backend):
        assert storage_api.upload_file("local.txt", "remote.txt", "text/plain") == "uploaded"
        assert storage_api.download_file("remote.txt", "local.txt") == b"data"
        assert storage_api.delete_file("remote.txt") is True
        assert storage_api.list_files("prefix/") == ["a.txt"]

    expected_calls = [
        ("upload_file", ("local.txt", "remote.txt", "text/plain"), {}),
        ("download_file", ("remote.txt", "local.txt"), {}),
        ("delete_file", ("remote.txt",), {}),
        ("list_files", ("prefix/",), {}),
    ]
    assert backend.calls[:4] == expected_calls


def test_call_raises_when_backend_missing_method():
    class EmptyBackend:
        pass

    with storage_api.using_storage_backend(EmptyBackend()):
        with pytest.raises(AttributeError) as excinfo:
            storage_api.list_files()

    assert "list_files" in str(excinfo.value)


def test_reset_storage_backend_restores_default():
    sentinel_backend = object()
    storage_api.set_storage_backend(sentinel_backend)
    storage_api.reset_storage_backend()

    assert storage_api.get_current_backend() is storage_api.supabase_storage


def test_using_storage_backend_restores_previous_backend():
    original = storage_api.get_current_backend()
    backend = RecordingBackend()
    with storage_api.using_storage_backend(backend):
        assert storage_api.get_current_backend() is backend

    assert storage_api.get_current_backend() is original


def test_download_folder_zip_raises_when_method_absent():
    class NoZipBackend:
        pass

    with storage_api.using_storage_backend(NoZipBackend()):
        with pytest.raises(AttributeError) as excinfo:
            storage_api.download_folder_zip("prefix/")

    assert "download_folder_zip" in str(excinfo.value)


def test_download_folder_zip_passes_arguments_and_bucket_when_provided():
    backend = RecordingBackend()
    with storage_api.using_storage_backend(backend):
        first_result = storage_api.download_folder_zip(
            "prefix/",
            zip_name="bundle.zip",
            out_dir="/tmp/out",
            timeout_s=120,
            cancel_event="evt",
        )
        assert first_result == "prefix/-zip"
        method, args, kwargs = backend.calls[-1]
        assert method == "download_folder_zip"
        assert args == ("prefix/",)
        assert kwargs["zip_name"] == "bundle.zip"
        assert kwargs["out_dir"] == "/tmp/out"
        assert kwargs["timeout_s"] == 120
        assert kwargs["cancel_event"] == "evt"
        assert "bucket" not in kwargs

        second_result = storage_api.download_folder_zip("other/", bucket="public")
        assert second_result == "other/-zip"
        method, args, kwargs_with_bucket = backend.calls[-1]
        assert method == "download_folder_zip"
        assert args == ("other/",)
        assert kwargs_with_bucket["bucket"] == "public"
