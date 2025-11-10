"""Upload helper used by the Tkinter UI to push folders to Supabase."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Garante MIME de .docx em qualquer SO
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".docx",
)

try:
    from src.utils.hash_utils import sha256_file as _sha256
except Exception:  # pragma: no cover

    def _sha256(path: Path | str) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()


from adapters.storage.api import list_files as storage_list_files
from adapters.storage.api import upload_file as storage_upload_file
from src.core.storage_key import make_storage_key, storage_slug_filename, storage_slug_part

logger = logging.getLogger(__name__)
from infra.supabase_client import exec_postgrest, supabase


def _guess_mime(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "application/octet-stream"


def _iter_files(base: Path) -> Iterable[Path]:
    for item in base.rglob("*"):
        if item.is_file():
            yield item



def _current_user_id() -> Optional[str]:
    """Return the currently authenticated Supabase user id (SDK-version agnostic)."""
    try:
        response = supabase.auth.get_user()
        user = getattr(response, "user", None)
        if user and getattr(user, "id", None):
            return user.id
        if isinstance(response, dict):
            return (response.get("user") or {}).get("id")
    except Exception:
        return None
    return None


def _resolve_org_id() -> str:
    """Resolve the organisation identifier for the logged user."""
    user_id = _current_user_id()
    fallback = (os.getenv("SUPABASE_DEFAULT_ORG") or "").strip() or "unknown-org"
    if not user_id:
        return fallback
    try:
        response = exec_postgrest(
            supabase.table("memberships")
            .select("org_id")
            .eq("user_id", user_id)
            .limit(1)
        )
        data = getattr(response, "data", None) or []
        if data:
            return data[0]["org_id"]
    except Exception:
        pass
    return fallback


def upload_folder_to_supabase(
    folder: str | Path,
    client_id: int,
    *,
    subdir: str = "SIFAP",
) -> List[Dict[str, Any]]:
    """
    Upload all files from ``folder`` to Supabase Storage and register metadata rows.

    For each file the storage path is ``{org}/{client_id}/{subdir}/{relative_path}`` and
    the function inserts records into ``documents`` and ``document_versions``.
    """
    base = Path(folder).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Pasta nao encontrada: {base}")

    user_id = _current_user_id()
    if not user_id:
        raise RuntimeError(
            "Usuario nao autenticado no Supabase. Faca login antes de enviar."
        )

    org_id = _resolve_org_id()
    results: List[Dict[str, Any]] = []

    def _raise_if_exists(path_key: str) -> None:
        folder, _, filename = path_key.rpartition("/")
        candidates = storage_list_files(folder)
        for item in candidates:
            if isinstance(item, dict):
                name = item.get("name")
                full_path = item.get("full_path")
                if name == filename or full_path == path_key:
                    raise RuntimeError(f"Arquivo ja existente no storage: {path_key}")
            elif isinstance(item, str) and item.strip("/") in {filename, path_key}:
                raise RuntimeError(f"Arquivo ja existente no storage: {path_key}")

    for path in _iter_files(base):
        relative_path = str(path.relative_to(base)).replace("\\", "/")
        segments_raw = [segment for segment in relative_path.split("/") if segment]
        if segments_raw:
            filename_raw = segments_raw[-1]
            dir_segments_raw = segments_raw[:-1]
        else:
            filename_raw = path.name
            dir_segments_raw = []

        storage_path = make_storage_key(
            org_id,
            client_id,
            subdir,
            *dir_segments_raw,
            filename=filename_raw,
        )

        dir_segments_sanitized: List[str] = []
        for segment in dir_segments_raw:
            sanitized_segment = storage_slug_part(segment)
            if sanitized_segment:
                dir_segments_sanitized.append(sanitized_segment)
        filename_sanitized = storage_slug_filename(filename_raw)
        safe_rel = "/".join(dir_segments_sanitized + [filename_sanitized])

        size_bytes = path.stat().st_size
        sha_value = _sha256(path)
        mime_type = _guess_mime(path)

        logger.info("Upload Storage: original=%r -> key=%s", relative_path or filename_raw, storage_path)
        _raise_if_exists(storage_path)
        storage_upload_file(str(path), storage_path, mime_type)

        document_response = exec_postgrest(
            supabase.table("documents").insert(
                {
                    "client_id": int(client_id),
                    "title": path.name,
                    "kind": mime_type,
                    "user_id": user_id,
                },
                returning="representation",
            )
        )

        if not document_response.data:
            raise RuntimeError(
                f"INSERT bloqueado por RLS em 'documents' para arquivo: {path.name}"
            )

        document_id = document_response.data[0]["id"]

        version_response = exec_postgrest(
            supabase.table("document_versions").insert(
                {
                    "document_id": document_id,
                    "storage_path": storage_path,
                    "size_bytes": size_bytes,
                    "sha256": sha_value,
                    "uploaded_by": user_id,
                },
                returning="representation",
            )
        )

        if not version_response.data:
            raise RuntimeError(
                f"INSERT bloqueado por RLS em 'document_versions' para arquivo: {path.name}"
            )

        version_id = version_response.data[0]["id"]

        exec_postgrest(
            supabase.table("documents")
            .update({"current_version": version_id})
            .eq("id", document_id)
        )

        results.append(
            {
                "relative_path": safe_rel,
                "storage_path": storage_path,
                "document_id": document_id,
                "version_id": version_id,
                "size_bytes": size_bytes,
                "sha256": sha_value,
                "mime": mime_type,
            }
        )

    return results
