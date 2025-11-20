# adapters/storage/supabase_storage.py
from __future__ import annotations

import mimetypes
import os
import unicodedata
from pathlib import Path
from typing import Iterable, Optional, Any

# Garante MIME de .docx em qualquer SO
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".docx",
)

from src.config.paths import CLOUD_ONLY
from infra.supabase_client import supabase, baixar_pasta_zip, DownloadCancelledError
from adapters.storage.port import StoragePort

DEFAULT_BUCKET = (os.getenv("SUPABASE_BUCKET") or "rc-docs").strip() or "rc-docs"


def _normalize_bucket(bucket: Optional[str]) -> str:
    value = (bucket or DEFAULT_BUCKET).strip() or DEFAULT_BUCKET
    return value


def _strip_accents(value: str) -> str:
    """Remove acentos de uma string usando normalizacao Unicode NFKD."""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_key_for_storage(key: str) -> str:
    """Normaliza key do Storage removendo acentos APENAS do nome do arquivo (ultimo segmento)."""
    key = key.strip("/").replace("\\", "/")
    parts = key.split("/")
    if parts:
        # Remove acentos apenas do nome do arquivo (ultimo segmento)
        filename = parts[-1]
        parts[-1] = _strip_accents(filename)
    return "/".join(parts)


def _normalize_key(key: str) -> str:
    # Aplica normalizacao completa: remove acentos do filename + strip barras
    return normalize_key_for_storage(key)


def _guess_content_type(remote_key: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    guess, _ = mimetypes.guess_type(remote_key)
    return guess or "application/octet-stream"


def _read_data(source: Any) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    path = Path(source)
    with path.open("rb") as handle:
        return handle.read()


def _upload(
    client: Any,
    bucket: str,
    source: Any,
    remote_key: str,
    content_type: Optional[str],
    *,
    upsert: bool = True,
) -> str:
    key = _normalize_key(remote_key)
    file_options = {
        "content-type": _guess_content_type(key, content_type),
        # storage3 espera string, não bool (evita erro 'bool'.encode)
        "upsert": "true" if upsert else "false",
    }
    data = _read_data(source)
    response = client.storage.from_(bucket).upload(key, data, file_options=file_options)
    if isinstance(response, dict):
        data_obj = response.get("data")
        if isinstance(data_obj, dict):
            return data_obj.get("path", key)
    return key


def _download(client: Any, bucket: str, remote_key: str, local_path: Optional[str]) -> str | bytes:
    key = _normalize_key(remote_key)
    data = client.storage.from_(bucket).download(key)
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if local_path:
        target = Path(local_path)
        if not CLOUD_ONLY:
            target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            handle.write(data)  # pyright: ignore[reportArgumentType]
        return str(target)
    return data  # pyright: ignore[reportReturnType]


def _delete(client: Any, bucket: str, remote_key: str) -> bool:
    key = _normalize_key(remote_key)
    response = client.storage.from_(bucket).remove([key])
    if isinstance(response, dict):
        error = response.get("error")
        return not error
    return True


def _list(client: Any, bucket: str, prefix: str = "") -> list[dict[str, Any]]:
    base = prefix.strip("/")
    path = f"{base}/" if base else ""
    response = client.storage.from_(bucket).list(
        path=path,
        options={
            "limit": 1000,
            "offset": 0,
            "sortBy": {"column": "name", "order": "asc"},
        },
    )
    results: list[dict[str, Any]] = []
    for obj in response or []:
        if not isinstance(obj, dict):
            continue
        entry = dict(obj)
        name = entry.get("name") or ""
        entry["full_path"] = f"{base}/{name}".strip("/") if base else name
        results.append(entry)
    return results


class SupabaseStorageAdapter(StoragePort):
    """Concrete implementation of StoragePort backed by the shared supabase client."""

    def __init__(
        self,
        client: Any | None = None,
        bucket: Optional[str] = None,
        *,
        overwrite: bool = True,
    ) -> None:
        self._client = client or supabase
        self._bucket = _normalize_bucket(bucket)
        self._overwrite = overwrite

    def upload_file(self, local_path: Any, remote_key: str, content_type: Optional[str] = None) -> str:
        return _upload(
            self._client,
            self._bucket,
            local_path,
            remote_key,
            content_type,
            upsert=self._overwrite,
        )

    def download_file(self, remote_key: str, local_path: Optional[str] = None) -> str | bytes:
        return _download(self._client, self._bucket, remote_key, local_path)

    def delete_file(self, remote_key: str) -> bool:
        return _delete(self._client, self._bucket, remote_key)

    def list_files(self, prefix: str = "") -> list[dict[str, Any]]:
        return _list(self._client, self._bucket, prefix)

    def download_folder_zip(
        self,
        prefix: str,
        *,
        zip_name: Optional[str] = None,
        out_dir: Optional[str] = None,
        timeout_s: int = 300,
        cancel_event: Optional[Any] = None,
    ):
        normalized_prefix = prefix.strip("/")
        return baixar_pasta_zip(
            self._bucket,
            normalized_prefix,
            zip_name=zip_name,
            out_dir=out_dir,
            timeout_s=timeout_s,
            cancel_event=cancel_event,
        )


_default_adapter = SupabaseStorageAdapter()


def upload_file(local_path: Any, remote_key: str, content_type: Optional[str] = None) -> str:
    return _default_adapter.upload_file(local_path, remote_key, content_type)


def download_file(remote_key: str, local_path: Optional[str] = None) -> str | bytes:
    return _default_adapter.download_file(remote_key, local_path)


def delete_file(remote_key: str) -> bool:
    return _default_adapter.delete_file(remote_key)


def list_files(prefix: str = "") -> Iterable[dict[str, Any]]:
    return _default_adapter.list_files(prefix)


def download_folder_zip(
    prefix: str,
    *,
    bucket: Optional[str] = None,
    zip_name: Optional[str] = None,
    out_dir: Optional[str] = None,
    timeout_s: int = 300,
    cancel_event: Optional[Any] = None,
):
    adapter = _default_adapter if bucket is None else SupabaseStorageAdapter(bucket=bucket)
    return adapter.download_folder_zip(
        prefix,
        zip_name=zip_name,
        out_dir=out_dir,
        timeout_s=timeout_s,
        cancel_event=cancel_event,
    )


def get_default_adapter() -> SupabaseStorageAdapter:
    return _default_adapter


__all__ = [
    "SupabaseStorageAdapter",
    "upload_file",
    "download_file",
    "delete_file",
    "list_files",
    "download_folder_zip",
    "DownloadCancelledError",
    "get_default_adapter",
    "normalize_key_for_storage",
]
