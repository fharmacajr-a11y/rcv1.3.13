"""Storage helpers for the Auditoria module."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from src.shared.storage_ui_bridge import build_client_prefix as _build_client_prefix_shared

CLIENTS_BUCKET = os.getenv("RC_STORAGE_BUCKET_CLIENTS", "rc-docs").strip() or "rc-docs"


@dataclass(frozen=True)
class AuditoriaStorageContext:
    """Represents a fully qualified storage prefix for a client."""

    bucket: str
    org_id: str
    client_root: str
    auditoria_prefix: str

    def build_path(self, relative_path: str) -> str:
        return f"{self.auditoria_prefix}/{relative_path}".strip("/")


@dataclass(frozen=True)
class AuditoriaUploadContext:
    bucket: str
    base_prefix: str
    org_id: str
    client_id: int


def get_clients_bucket() -> str:
    return CLIENTS_BUCKET


def build_client_prefix(client_id: int, org_id: str) -> str:
    return _build_client_prefix_shared(org_id=org_id, client_id=client_id)


def build_auditoria_prefix(client_root: str) -> str:
    return f"{client_root}/GERAL/Auditoria".strip("/")


def make_storage_context(client_id: int, org_id: str) -> AuditoriaStorageContext:
    client_root = build_client_prefix(client_id, org_id)
    auditoria_prefix = build_auditoria_prefix(client_root)
    return AuditoriaStorageContext(
        bucket=get_clients_bucket(),
        org_id=org_id,
        client_root=client_root,
        auditoria_prefix=auditoria_prefix,
    )


def ensure_auditoria_folder(sb: Any, context: AuditoriaStorageContext) -> None:
    target = f"{context.auditoria_prefix}/.keep".strip("/")
    resp = sb.storage.from_(context.bucket).upload(
        path=target,
        file=b"",
        file_options={"content-type": "text/plain", "upsert": "true"},
    )
    if getattr(resp, "error", None):
        raise RuntimeError(str(resp.error))


def list_existing_file_names(sb: Any, bucket: str, prefix: str, *, page_size: int = 1000) -> set[str]:
    existing: set[str] = set()
    offset = 0
    while True:
        resp = sb.storage.from_(bucket).list(prefix, {"limit": page_size, "offset": offset})
        if not resp:
            break
        for item in resp:
            name = item.get("name")
            if name:
                existing.add(name)
        if len(resp) < page_size:
            break
        offset += page_size
    return existing


def upload_storage_bytes(
    sb: Any,
    bucket: str,
    dest_path: str,
    data: bytes,
    *,
    content_type: str,
    upsert: bool = False,
    cache_control: str = "3600",
) -> None:
    sb.storage.from_(bucket).upload(
        dest_path,
        data,
        {
            "content-type": content_type or "application/octet-stream",
            "upsert": str(bool(upsert)).lower(),
            "cacheControl": cache_control,
        },
    )


def remove_storage_objects(sb: Any, bucket: str, paths: Sequence[str] | Iterable[str]) -> None:
    batch = list(paths)
    if not batch:
        return
    sb.storage.from_(bucket).remove(batch)
