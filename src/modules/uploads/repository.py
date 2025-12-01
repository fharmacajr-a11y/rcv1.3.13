"""Backend integrations for the uploads module."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable, Sequence, Tuple, TypeVar, cast

from adapters.storage.api import list_files as _storage_list_files, upload_file as _storage_upload_file
from adapters.storage.supabase_storage import SupabaseStorageAdapter
from infra.supabase_client import exec_postgrest, supabase

if False:  # pragma: no cover
    pass

_TUploadItem = TypeVar("_TUploadItem")
logger = logging.getLogger(__name__)


def current_user_id() -> str | None:
    """Return the Supabase user id if available."""

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


def resolve_org_id() -> str:
    """Determine org_id for the authenticated user or fallback env."""

    user_id = current_user_id()
    fallback = (os.getenv("SUPABASE_DEFAULT_ORG") or "").strip() or "unknown-org"
    if not user_id:
        return fallback
    try:
        response = exec_postgrest(supabase.table("memberships").select("org_id").eq("user_id", user_id).limit(1))
        data = getattr(response, "data", None) or []
        if data:
            return data[0]["org_id"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao resolver org_id para uploads: %s", exc)
    return fallback


def ensure_storage_object_absent(path_key: str) -> None:
    """Guard against overriding existing files in the storage bucket."""

    folder_prefix, _, filename = path_key.rpartition("/")
    candidates = _storage_list_files(folder_prefix)
    for item in candidates:
        if isinstance(item, dict):
            name = item.get("name")
            full_path = item.get("full_path")
            if name == filename or full_path == path_key:
                raise RuntimeError(f"Arquivo ja existente no storage: {path_key}")
        elif isinstance(item, str) and item.strip("/") in {filename, path_key}:
            raise RuntimeError(f"Arquivo ja existente no storage: {path_key}")


def upload_local_file(local_path: Path | str, storage_path: str, mime_type: str) -> None:
    """Upload a file to Supabase storage."""

    _storage_upload_file(str(local_path), storage_path, mime_type)


def insert_document_record(*, client_id: int, title: str, mime_type: str, user_id: str) -> dict[str, Any]:
    """Insert a row into documents and return representation."""

    response = exec_postgrest(
        supabase.table("documents").insert(
            {
                "client_id": int(client_id),
                "title": title,
                "kind": mime_type,
                "user_id": user_id,
            },
            returning="representation",
        )
    )
    if not response.data:
        raise RuntimeError(f"INSERT bloqueado por RLS em 'documents' para arquivo: {title}")
    return response.data[0]


def insert_document_version_record(
    *,
    document_id: int,
    storage_path: str,
    size_bytes: int,
    sha_value: str,
    uploaded_by: str,
) -> dict[str, Any]:
    """Insert a row into document_versions and return representation."""

    response = exec_postgrest(
        supabase.table("document_versions").insert(
            {
                "document_id": document_id,
                "storage_path": storage_path,
                "size_bytes": size_bytes,
                "sha256": sha_value,
                "uploaded_by": uploaded_by,
            },
            returning="representation",
        )
    )
    if not response.data:
        raise RuntimeError(f"INSERT bloqueado por RLS em 'document_versions' para arquivo: {storage_path}")
    return response.data[0]


def update_document_current_version(document_id: int, version_id: int) -> None:
    """Update current version reference for a document."""

    exec_postgrest(supabase.table("documents").update({"current_version": version_id}).eq("id", document_id))


def normalize_bucket(value: str | None) -> str:
    """Compute the bucket name for client documents."""

    raw = (value or os.getenv("SUPABASE_BUCKET") or "rc-docs").strip()
    return raw or "rc-docs"


def build_storage_adapter(*, bucket: str, supabase_client: Any | None = None) -> SupabaseStorageAdapter:
    """Instantiate the storage adapter with defaults."""

    return SupabaseStorageAdapter(
        client=supabase_client or supabase,
        bucket=bucket,
        overwrite=False,
    )


def upload_items_with_adapter(
    adapter: SupabaseStorageAdapter,
    items: Sequence[_TUploadItem],
    cnpj_digits: str,
    subfolder: str | None,
    *,
    progress_callback: Callable[[Any], None] | None = None,
    remote_path_builder: Callable[[str, str, str | None], str],
    client_id: int | None = None,
    org_id: str | None = None,
) -> Tuple[int, list[Tuple[_TUploadItem, Exception]]]:
    """Upload items using the provided adapter and collect failures."""

    ok = 0
    failures: list[Tuple[_TUploadItem, Exception]] = []
    duplicates = 0

    for item in items:
        if progress_callback:
            progress_callback(item)
        try:
            # build_remote_path aceita client_id/org_id como keyword-only, mas o tipo
            # do parâmetro remote_path_builder não inclui isso. Usamos cast para chamar corretamente.
            builder_fn = cast(Any, remote_path_builder)
            remote_key = builder_fn(
                cnpj_digits,
                getattr(item, "relative_path"),
                subfolder,
                client_id=client_id,
                org_id=org_id,
            )
            local_path = getattr(item, "path")

            logger.debug(
                "Uploading file: %s -> %s (client_id=%s, org_id=%s, subfolder=%s)",
                local_path,
                remote_key,
                client_id,
                org_id,
                subfolder,
            )

            adapter.upload_file(
                local_path,
                remote_key,
                content_type="application/pdf",
            )
            ok += 1
            logger.info("Upload SUCCESS: %s -> %s", Path(local_path).name, remote_key)

        except Exception as exc:  # pragma: no cover - integration behavior
            # Trata erro 409 Duplicate como "ja existe", nao como falha
            error_msg = str(exc)
            is_duplicate = "Duplicate" in error_msg or "409" in error_msg or "already exists" in error_msg

            if is_duplicate:
                duplicates += 1
                logger.info(
                    "Upload SKIPPED (duplicate): %s -> %s (client_id=%s, org_id=%s)",
                    Path(getattr(item, "path")).name,
                    remote_key if "remote_key" in locals() else "N/A",
                    client_id,
                    org_id,
                )
                # NAO adiciona em failures - arquivo ja existe na nuvem
                continue

            # Outros erros: registra como falha
            logger.error(
                "Upload FAILED: %s -> %s (client_id=%s, org_id=%s): %s",
                getattr(item, "path"),
                remote_key if "remote_key" in locals() else "N/A",
                client_id,
                org_id,
                repr(exc),
            )
            failures.append((item, exc))
    return ok, failures


__all__ = [
    "current_user_id",
    "resolve_org_id",
    "ensure_storage_object_absent",
    "upload_local_file",
    "insert_document_record",
    "insert_document_version_record",
    "update_document_current_version",
    "normalize_bucket",
    "build_storage_adapter",
    "upload_items_with_adapter",
]
