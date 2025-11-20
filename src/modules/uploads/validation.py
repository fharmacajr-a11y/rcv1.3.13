"""Validation and normalization helpers for uploads module."""

from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence, TypeVar

from src.core.storage_key import make_storage_key, storage_slug_filename, storage_slug_part

_TItem = TypeVar("_TItem")


@dataclass(slots=True)
class PreparedUploadEntry:
    """Metadata necessary to persist a local file into Supabase."""

    path: Path
    relative_path: str
    storage_path: str
    safe_relative_path: str
    size_bytes: int
    sha256: str
    mime_type: str


def ensure_existing_folder(folder: str | Path) -> Path:
    """Resolve folder path and ensure it exists."""

    base = Path(folder).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Pasta nao encontrada: {base}")
    return base


def iter_local_files(base: Path) -> Iterable[Path]:
    """Yield every file contained in a directory recursively."""

    for item in base.rglob("*"):
        if item.is_file():
            yield item


def guess_mime(path: Path) -> str:
    """Guess MIME type for a local file."""

    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "application/octet-stream"


def normalize_relative_path(relative: str) -> str:
    """Normalize user-provided relative paths and strip unsafe segments."""  # noqa: D401

    rel = relative.replace("\\", "/")
    rel = os.path.normpath(rel).replace("\\", "/")
    rel = rel.replace("..", "").lstrip("./")
    return rel.strip("/")


def _split_relative_path(relative_path: str, fallback_name: str) -> tuple[list[str], str]:
    segments_raw = [segment for segment in relative_path.split("/") if segment]
    if segments_raw:
        filename_raw = segments_raw[-1]
        dir_segments_raw = segments_raw[:-1]
    else:
        filename_raw = fallback_name
        dir_segments_raw = []
    return dir_segments_raw, filename_raw


def _sanitize_directory_segments(dir_segments: Sequence[str]) -> list[str]:
    sanitized: list[str] = []
    for segment in dir_segments:
        cleaned = storage_slug_part(segment)
        if cleaned:
            sanitized.append(cleaned)
    return sanitized


def prepare_folder_entries(
    base: Path,
    client_id: int,
    subdir: str,
    org_id: str,
    hash_func: Callable[[Path | str], str],
) -> list[PreparedUploadEntry]:
    """Collect files and build metadata required for persistence."""

    prepared: list[PreparedUploadEntry] = []
    safe_subdir = str(subdir)
    for path in iter_local_files(base):
        relative_path = str(path.relative_to(base)).replace("\\", "/")
        if not relative_path:
            relative_path = path.name

        dir_segments_raw, filename_raw = _split_relative_path(relative_path, path.name)
        storage_path = make_storage_key(
            org_id,
            str(client_id),
            safe_subdir,
            *dir_segments_raw,
            filename=filename_raw,
        )
        dir_segments_sanitized = _sanitize_directory_segments(dir_segments_raw)
        filename_sanitized = storage_slug_filename(filename_raw)
        safe_rel = "/".join(dir_segments_sanitized + [filename_sanitized])
        size_bytes = path.stat().st_size
        sha_value = hash_func(path)
        mime_type = guess_mime(path)

        prepared.append(
            PreparedUploadEntry(
                path=path,
                relative_path=relative_path or filename_raw,
                storage_path=storage_path,
                safe_relative_path=safe_rel,
                size_bytes=size_bytes,
                sha256=sha_value,
                mime_type=mime_type,
            )
        )
    return prepared


def collect_pdf_items_from_folder(dirpath: str, factory: Callable[[Path, str], _TItem]) -> list[_TItem]:
    """Collect PDF files inside a folder and build UploadItems via factory."""

    base = Path(dirpath)
    if not base.is_dir():
        return []

    records: list[tuple[str, str, Path]] = []
    for file_path in base.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() != ".pdf":
            continue
        relative = file_path.relative_to(base).as_posix()
        records.append((relative.lower(), relative, file_path))

    records.sort(key=lambda entry: entry[0])
    return [factory(path, relative) for _, relative, path in records]


def build_items_from_files(paths: Sequence[str], factory: Callable[[Path, str], _TItem]) -> list[_TItem]:
    """Create UploadItems for an arbitrary list of files."""

    records: list[tuple[str, str, Path]] = []
    for raw in paths:
        path = Path(raw)
        if path.suffix.lower() != ".pdf":
            continue
        records.append((path.name.lower(), path.name, path))

    records.sort(key=lambda entry: entry[0])
    return [factory(path, relative) for _, relative, path in records]


def build_remote_path(
    cnpj_digits: str,
    relative_path: str,
    subfolder: str | None,
    *,
    client_id: int | None = None,
    org_id: str | None = None,
) -> str:
    """
    Compose a storage key for the uploads bucket.

    Estrutura (quando client_id e org_id fornecidos):
        {org_id}/{client_id}/GERAL/{subfolder?}/{relative_path}

    Estrutura (fallback quando apenas cnpj_digits):
        {cnpj_digits}/{subfolder?}/{relative_path}
    """
    from src.modules.uploads.components.helpers import client_prefix_for_id

    parts: list[str] = []

    # Se temos client_id e org_id, usa estrutura padrao do pipeline
    if client_id is not None and org_id:
        prefix = client_prefix_for_id(client_id, org_id)
        parts.append(prefix)
        parts.append("GERAL")  # DEFAULT_IMPORT_SUBFOLDER
    else:
        # Fallback para compatibilidade com codigo legado
        parts.append(cnpj_digits)

    if subfolder:
        parts.append(subfolder.strip("/"))
    parts.append(normalize_relative_path(relative_path))

    return "/".join(segment.strip("/") for segment in parts if segment)


__all__ = [
    "PreparedUploadEntry",
    "ensure_existing_folder",
    "iter_local_files",
    "guess_mime",
    "normalize_relative_path",
    "prepare_folder_entries",
    "collect_pdf_items_from_folder",
    "build_items_from_files",
    "build_remote_path",
]
