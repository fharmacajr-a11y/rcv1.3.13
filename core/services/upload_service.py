"""Upload helper used by the Tkinter UI to push folders to Supabase."""
from __future__ import annotations

from pathlib import Path
import hashlib
import mimetypes
import os
from typing import Any, Dict, Iterable, List, Optional

try:
    from utils.hash_utils import sha256_file as _sha256
except Exception:  # pragma: no cover
    def _sha256(path: Path | str) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()

from infra.supabase_client import supabase

BUCKET_NAME = (os.getenv("SUPABASE_BUCKET") or "rc-docs").strip() or "rc-docs"


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
    fallback = (os.getenv("SUPABASE_DEFAULT_ORG") or "").strip()
    if not user_id:
        return fallback
    try:
        response = (
            supabase.table("memberships")
            .select("org_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
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
        raise RuntimeError("Usuario nao autenticado no Supabase. Faca login antes de enviar.")

    org_id = _resolve_org_id() or "unknown-org"
    results: List[Dict[str, Any]] = []

    for path in _iter_files(base):
        relative_path = str(path.relative_to(base)).replace("\\", "/")
        size_bytes = path.stat().st_size
        sha_value = _sha256(path)
        mime_type = _guess_mime(path)

        storage_path = f"{org_id}/{client_id}/{subdir}/{relative_path}"
        with path.open("rb") as handle:
            supabase.storage.from_(BUCKET_NAME).upload(
                file=handle,
                path=storage_path,
                file_options={"content-type": mime_type, "upsert": "false"},
            )

        document_response = supabase.table("documents").insert(
            {
                "client_id": int(client_id),
                "title": path.name,
                "kind": mime_type,
                "user_id": user_id,
            },
            returning="representation",
        ).execute()

        if not document_response.data:
            raise RuntimeError(f"INSERT bloqueado por RLS em 'documents' para arquivo: {path.name}")

        document_id = document_response.data[0]["id"]

        version_response = supabase.table("document_versions").insert(
            {
                "document_id": document_id,
                "storage_path": storage_path,
                "size_bytes": size_bytes,
                "sha256": sha_value,
                "uploaded_by": user_id,
            },
            returning="representation",
        ).execute()

        if not version_response.data:
            raise RuntimeError(f"INSERT bloqueado por RLS em 'document_versions' para arquivo: {path.name}")

        version_id = version_response.data[0]["id"]

        supabase.table("documents").update({"current_version": version_id}).eq("id", document_id).execute()

        results.append(
            {
                "relative_path": relative_path,
                "storage_path": storage_path,
                "document_id": document_id,
                "version_id": version_id,
                "size_bytes": size_bytes,
                "sha256": sha_value,
                "mime": mime_type,
            }
        )

    return results
