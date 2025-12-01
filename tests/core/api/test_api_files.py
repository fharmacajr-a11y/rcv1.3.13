from __future__ import annotations

import logging

import src.core.api.api_files as api_files


def test_upload_file_returns_true_when_backend_succeeds(monkeypatch):
    calls: list[tuple[str, str, str]] = []

    def fake_upload(file_path: str, bucket: str, remote_path: str) -> None:
        calls.append((file_path, bucket, remote_path))

    monkeypatch.setattr("adapters.storage.api.upload_file", fake_upload)

    assert api_files.upload_file("local.pdf", "bucket-a", "remote/name.pdf") is True
    assert calls == [("local.pdf", "bucket-a", "remote/name.pdf")]


def test_upload_file_logs_and_returns_false_on_failure(monkeypatch, caplog):
    def fake_upload(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("adapters.storage.api.upload_file", fake_upload)
    caplog.set_level(logging.ERROR)

    assert api_files.upload_file("file.pdf", "bucket-a", "remote/file.pdf") is False
    assert "Upload failed for file.pdf" in caplog.text


def test_download_folder_zip_returns_path_from_backend(monkeypatch):
    def fake_download(bucket: str, prefix: str, dest_path):
        return f"{bucket}-{prefix}-{dest_path or 'tmp'}.zip"

    monkeypatch.setattr("adapters.storage.api.download_folder_zip", fake_download)

    path = api_files.download_folder_zip("bucket-a", "client-42", dest_path="/tmp/archive.zip")
    assert path == "bucket-a-client-42-/tmp/archive.zip.zip"


def test_download_folder_zip_uses_none_when_dest_path_missing(monkeypatch):
    captured: list[tuple[str, str, str | None]] = []

    def fake_download(bucket: str, prefix: str, dest_path: str | None):
        captured.append((bucket, prefix, dest_path))
        return "generated.zip"

    monkeypatch.setattr("adapters.storage.api.download_folder_zip", fake_download)

    assert api_files.download_folder_zip("bucket", "client") == "generated.zip"
    assert captured == [("bucket", "client", None)]


def test_download_folder_zip_logs_and_returns_none_on_error(monkeypatch, caplog):
    def fake_download(*_args, **_kwargs):
        raise ValueError("network down")

    monkeypatch.setattr("adapters.storage.api.download_folder_zip", fake_download)
    caplog.set_level(logging.ERROR)

    assert api_files.download_folder_zip("bucket-a", "client-42") is None
    assert "Folder ZIP download failed for client-42" in caplog.text
