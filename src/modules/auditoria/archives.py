"""Archive processing helpers for the Auditoria module."""

from __future__ import annotations

import mimetypes
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

try:
    from infra.archive_utils import (  # type: ignore[import-untyped]
        ArchiveError as _ArchiveErrorType,
        extract_archive as _infra_extract_archive,
        is_supported_archive as _infra_is_supported_archive,
    )
except Exception:  # pragma: no cover - defensive fallback

    class _FallbackArchiveError(Exception):
        """Fallback when archive utilities are unavailable."""

    _ArchiveErrorType = _FallbackArchiveError

    def _infra_extract_archive(src: str | Path, out_dir: str | Path, *, password: str | None = None) -> Path:
        raise _ArchiveErrorType("Archive utilities are not available.")

    def _infra_is_supported_archive(path: str | Path) -> bool:
        lowered = (path or "").lower()
        return lowered.endswith((".zip", ".rar", ".7z"))


ArchiveError: type[Exception]
ArchiveError = _ArchiveErrorType

if TYPE_CHECKING:  # pragma: no cover
    from .storage import AuditoriaUploadContext


@dataclass(frozen=True)
class AuditoriaArchiveEntry:
    relative_path: str
    file_size: int


@dataclass
class AuditoriaArchivePlan:
    archive_path: Path
    extension: str
    entries: list[AuditoriaArchiveEntry]
    extracted_dir: Path | None = None
    _temp_dir: tempfile.TemporaryDirectory | None = None

    def cleanup(self) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None


@dataclass(frozen=True)
class AuditoriaUploadItem:
    relative_path: str
    dest_name: str
    upsert: bool
    file_size: int


@dataclass(frozen=True)
class AuditoriaUploadProgress:
    done_files: int
    done_bytes: int
    total_files: int
    total_bytes: int
    skipped_duplicates: int
    failed_count: int


@dataclass(frozen=True)
class AuditoriaUploadResult:
    uploaded_paths: list[str]
    failed: list[tuple[str, str]]
    done_files: int
    done_bytes: int
    total_files: int
    total_bytes: int
    skipped_duplicates: int
    cancelled: bool = False


def extract_archive_to(source: str | Path, target_folder: str | Path) -> Path:
    return _infra_extract_archive(source, target_folder)


def is_supported_archive(path: str | Path) -> bool:
    return _infra_is_supported_archive(path)


def _normalize_archive_relative_path(value: str) -> str:
    rel = (value or "").lstrip("/").replace("\\", "/")
    if not rel or rel.startswith((".", "__MACOSX")) or ".." in rel:
        return ""
    return rel


def prepare_archive_plan(
    archive_path: str | Path,
    *,
    extract_func: Callable[[str | Path, str | Path], Path] | None = None,
) -> AuditoriaArchivePlan:
    path = Path(archive_path)
    lower_name = path.name.lower()
    is_7z_volume = ".7z." in lower_name and lower_name.split(".7z.", 1)[1].isdigit()
    if lower_name.endswith(".zip"):
        ext = "zip"
    elif lower_name.endswith(".rar"):
        ext = "rar"
    elif lower_name.endswith(".7z") or is_7z_volume:
        ext = "7z"
    else:
        raise ValueError("Formato nao suportado. Use arquivos .zip, .rar ou .7z.")

    entries: list[AuditoriaArchiveEntry] = []
    temp_dir: tempfile.TemporaryDirectory | None = None
    extracted_dir: Path | None = None

    extractor = extract_func or extract_archive_to

    if ext == "zip":
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    rel = _normalize_archive_relative_path(info.filename)
                    if not rel:
                        continue
                    entries.append(AuditoriaArchiveEntry(relative_path=rel, file_size=info.file_size))
        except zipfile.BadZipFile as exc:
            raise ArchiveError(f"Arquivo ZIP invalido: {exc}") from exc
    else:
        temp_dir = tempfile.TemporaryDirectory()
        extracted_dir = Path(temp_dir.name)
        try:
            extractor(path, extracted_dir)
        except Exception:
            temp_dir.cleanup()
            raise
        for file in extracted_dir.rglob("*"):
            if file.is_file():
                rel = _normalize_archive_relative_path(file.relative_to(extracted_dir).as_posix())
                if not rel:
                    continue
                entries.append(AuditoriaArchiveEntry(relative_path=rel, file_size=file.stat().st_size))

    return AuditoriaArchivePlan(archive_path=path, extension=ext, entries=entries, extracted_dir=extracted_dir, _temp_dir=temp_dir)


def cleanup_archive_plan(plan: AuditoriaArchivePlan | None) -> None:
    if plan is not None:
        plan.cleanup()


def detect_duplicate_file_names(plan: AuditoriaArchivePlan, existing_names: set[str]) -> set[str]:
    file_names = {Path(entry.relative_path).name for entry in plan.entries}
    return file_names & set(existing_names)


def _next_copy_name(name: str, existing: set[str]) -> str:
    base = Path(name).stem or "arquivo"
    suffix = Path(name).suffix
    idx = 2
    candidate = f"{base} ({idx}){suffix}"
    while candidate in existing:
        idx += 1
        candidate = f"{base} ({idx}){suffix}"
    return candidate


def build_upload_items(
    entries: list[AuditoriaArchiveEntry],
    existing_names: set[str],
    duplicates: set[str],
    strategy: str,
) -> tuple[list[AuditoriaUploadItem], int]:
    strategy = (strategy or "skip").lower()
    if strategy not in {"skip", "replace", "rename"}:
        raise ValueError("Estrategia de duplicatas invalida.")
    planned: list[AuditoriaUploadItem] = []
    skipped = 0
    names_cache = set(existing_names)
    for entry in entries:
        file_name = Path(entry.relative_path).name
        is_dup = file_name in duplicates
        if is_dup:
            if strategy == "skip":
                skipped += 1
                continue
            if strategy == "replace":
                planned.append(
                    AuditoriaUploadItem(
                        relative_path=entry.relative_path,
                        dest_name=entry.relative_path,
                        upsert=True,
                        file_size=entry.file_size,
                    )
                )
            elif strategy == "rename":
                new_name = _next_copy_name(file_name, names_cache)
                names_cache.add(new_name)
                parent = Path(entry.relative_path).parent.as_posix()
                dest_name = new_name if parent in ("", ".") else f"{parent}/{new_name}"
                planned.append(
                    AuditoriaUploadItem(
                        relative_path=entry.relative_path,
                        dest_name=dest_name,
                        upsert=False,
                        file_size=entry.file_size,
                    )
                )
        else:
            planned.append(
                AuditoriaUploadItem(
                    relative_path=entry.relative_path,
                    dest_name=entry.relative_path,
                    upsert=False,
                    file_size=entry.file_size,
                )
            )
    return planned, skipped


def guess_mime(path: str) -> str:
    ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
    if ext == "7z" or ".7z." in path.lower():
        return "application/x-7z-compressed"
    if ext == "zip":
        return "application/zip"
    if ext == "rar":
        return "application/x-rar-compressed"
    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"


def execute_archive_upload(
    plan: AuditoriaArchivePlan,
    context: "AuditoriaUploadContext",
    *,
    strategy: str,
    existing_names: set[str],
    duplicates: set[str],
    upload_callback: Callable[..., Any],
    cancel_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[AuditoriaUploadProgress], None] | None = None,
) -> AuditoriaUploadResult:
    upload_items, skipped = build_upload_items(plan.entries, existing_names, duplicates, strategy)
    total_files = len(upload_items)
    total_bytes = sum(item.file_size for item in upload_items)
    uploaded_paths: list[str] = []
    failed: list[tuple[str, str]] = []
    done_files = 0
    done_bytes = 0
    failed_count = 0
    cancelled = False

    def emit_progress() -> None:
        if progress_callback:
            progress_callback(
                AuditoriaUploadProgress(
                    done_files=done_files,
                    done_bytes=done_bytes,
                    total_files=total_files,
                    total_bytes=total_bytes,
                    skipped_duplicates=skipped,
                    failed_count=failed_count,
                )
            )

    try:
        emit_progress()
        if plan.extension == "zip":
            with zipfile.ZipFile(plan.archive_path, "r") as zf:
                for item in upload_items:
                    if cancel_check and cancel_check():
                        cancelled = True
                        break
                    try:
                        data = zf.read(item.relative_path)
                        dest = f"{context.base_prefix}/{item.dest_name}".strip("/")
                        upload_callback(
                            context.bucket,
                            dest,
                            data,
                            content_type=guess_mime(item.dest_name),
                            upsert=item.upsert,
                        )
                        uploaded_paths.append(dest)
                        done_files += 1
                        done_bytes += item.file_size
                    except Exception as exc:  # pragma: no cover - integration path
                        failed.append((item.dest_name, str(exc)))
                        failed_count += 1
                    emit_progress()
        else:
            base = plan.extracted_dir
            if base is None:
                raise ValueError("Diretorio extraido nao encontrado para upload.")
            for item in upload_items:
                if cancel_check and cancel_check():
                    cancelled = True
                    break
                source = (base / item.relative_path).resolve()
                try:
                    dest = f"{context.base_prefix}/{item.dest_name}".strip("/")
                    with open(source, "rb") as fh:
                        upload_callback(
                            context.bucket,
                            dest,
                            fh.read(),
                            content_type=guess_mime(item.dest_name),
                            upsert=item.upsert,
                        )
                    uploaded_paths.append(dest)
                    done_files += 1
                    done_bytes += item.file_size
                except Exception as exc:  # pragma: no cover - integration path
                    failed.append((item.dest_name, str(exc)))
                    failed_count += 1
                emit_progress()
    finally:
        cleanup_archive_plan(plan)

    return AuditoriaUploadResult(
        uploaded_paths=uploaded_paths,
        failed=failed,
        done_files=done_files,
        done_bytes=done_bytes,
        total_files=total_files,
        total_bytes=total_bytes,
        skipped_duplicates=skipped,
        cancelled=cancelled,
    )
