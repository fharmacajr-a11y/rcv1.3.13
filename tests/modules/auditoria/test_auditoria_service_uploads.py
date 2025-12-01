from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.modules.auditoria import service as auditoria_service


def _make_context() -> auditoria_service.AuditoriaUploadContext:
    return auditoria_service.AuditoriaUploadContext(
        bucket="bucket",
        base_prefix="org/1/GERAL/Auditoria",
        org_id="org",
        client_id=1,
    )


def _build_zip(tmp_path):
    archive = tmp_path / "auditoria.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("foo.txt", "alpha")
        zf.writestr("nested/bar.txt", "beta")
    return archive


def test_execute_archive_upload_happy_path(monkeypatch, tmp_path):
    archive = _build_zip(tmp_path)
    plan = auditoria_service.prepare_archive_plan(archive)
    context = _make_context()

    uploads: list[tuple[str, str, bytes, bool]] = []

    def fake_upload(bucket, dest_path, data, *, content_type, upsert, cache_control="3600"):
        uploads.append((bucket, dest_path, data, upsert))

    progress_events: list[auditoria_service.AuditoriaUploadProgress] = []

    monkeypatch.setattr(auditoria_service, "upload_storage_bytes", fake_upload)

    result = auditoria_service.execute_archive_upload(
        plan,
        context,
        strategy="skip",
        existing_names=set(),
        duplicates=set(),
        cancel_check=None,
        progress_callback=progress_events.append,
    )

    assert {dest for _bucket, dest, _data, _upsert in uploads} == {
        f"{context.base_prefix}/foo.txt",
        f"{context.base_prefix}/nested/bar.txt",
    }
    assert result.failed == []
    assert progress_events[-1].done_files == progress_events[-1].total_files


def test_prepare_archive_plan_rejects_unknown_extension(tmp_path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("content")

    with pytest.raises(auditoria_service.AuditoriaServiceError):
        auditoria_service.prepare_archive_plan(file_path)


def test_prepare_archive_plan_uses_extract_archive_stub(monkeypatch, tmp_path):
    archive = tmp_path / "bundle.7z"
    archive.write_bytes(b"fake")

    def fake_extract(_source, target_folder):
        target_path = Path(target_folder)
        target_path.mkdir(parents=True, exist_ok=True)
        (target_path / "Arquivo.pdf").write_text("data")
        return target_path

    monkeypatch.setattr(auditoria_service, "extract_archive_to", fake_extract)

    plan = auditoria_service.prepare_archive_plan(archive)
    try:
        assert any(entry.relative_path == "Arquivo.pdf" for entry in plan.entries)
    finally:
        plan.cleanup()


def test_execute_archive_upload_renames_duplicates(monkeypatch, tmp_path):
    extracted = tmp_path / "extracted"
    (extracted / "sub").mkdir(parents=True)
    (extracted / "Arquivo.pdf").write_text("x")
    (extracted / "sub" / "Arquivo.pdf").write_text("y")

    plan = auditoria_service.AuditoriaArchivePlan(
        archive_path=tmp_path / "dummy.7z",
        extension="7z",
        entries=[
            auditoria_service.AuditoriaArchiveEntry("Arquivo.pdf", 1),
            auditoria_service.AuditoriaArchiveEntry("sub/Arquivo.pdf", 1),
        ],
        extracted_dir=extracted,
        _temp_dir=None,
    )

    context = _make_context()
    existing = {"Arquivo.pdf"}
    duplicates = auditoria_service.detect_duplicate_file_names(plan, existing)

    uploads: list[str] = []

    def fake_upload(_bucket, dest_path, data, *, content_type, upsert, cache_control="3600"):
        uploads.append(dest_path)

    monkeypatch.setattr(auditoria_service, "upload_storage_bytes", fake_upload)

    result = auditoria_service.execute_archive_upload(
        plan,
        context,
        strategy="rename",
        existing_names=existing,
        duplicates=duplicates,
        cancel_check=None,
        progress_callback=None,
    )

    assert result.failed == []
    assert uploads == [
        f"{context.base_prefix}/Arquivo (2).pdf",
        f"{context.base_prefix}/sub/Arquivo (3).pdf",
    ]


def test_execute_archive_upload_handles_cancel(monkeypatch, tmp_path):
    archive = _build_zip(tmp_path)
    plan = auditoria_service.prepare_archive_plan(archive)
    context = _make_context()

    uploads: list[str] = []

    def fake_upload(_bucket, dest_path, data, *, content_type, upsert, cache_control="3600"):
        uploads.append(dest_path)

    monkeypatch.setattr(auditoria_service, "upload_storage_bytes", fake_upload)

    cancel_counter = {"count": 0}

    def cancel_check():
        cancel_counter["count"] += 1
        return cancel_counter["count"] > 1

    result = auditoria_service.execute_archive_upload(
        plan,
        context,
        strategy="skip",
        existing_names=set(),
        duplicates=set(),
        cancel_check=cancel_check,
        progress_callback=None,
    )

    assert result.cancelled is True
    assert len(uploads) == 1


def test_execute_archive_upload_collects_failures_and_supports_rollback(monkeypatch, tmp_path):
    archive = _build_zip(tmp_path)
    plan = auditoria_service.prepare_archive_plan(archive)
    context = _make_context()

    uploads: list[str] = []

    def failing_upload(_bucket, dest_path, data, *, content_type, upsert, cache_control="3600"):
        uploads.append(dest_path)
        if dest_path.endswith("bar.txt"):
            raise RuntimeError("boom")

    monkeypatch.setattr(auditoria_service, "upload_storage_bytes", failing_upload)

    result = auditoria_service.execute_archive_upload(
        plan,
        context,
        strategy="skip",
        existing_names=set(),
        duplicates=set(),
        cancel_check=None,
        progress_callback=None,
    )

    assert len(result.failed) == 1
    assert uploads[0].endswith("foo.txt")

    rollback_calls: list[tuple[str, list[str]]] = []

    def fake_remove(bucket, paths):
        rollback_calls.append((bucket, list(paths)))

    monkeypatch.setattr(auditoria_service, "remove_storage_objects", fake_remove)

    auditoria_service.rollback_uploaded_paths(context, result.uploaded_paths)

    assert rollback_calls == [(context.bucket, result.uploaded_paths)]
