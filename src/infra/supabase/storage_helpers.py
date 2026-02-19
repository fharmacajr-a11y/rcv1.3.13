"""Utility helpers for working with Supabase Storage objects."""

from __future__ import annotations

from typing import Optional

from src.infra.supabase_client import get_supabase


def download_bytes(bucket: str, path: str) -> Optional[bytes]:
    """Return raw bytes for a Storage object or ``None`` if unavailable."""
    if not bucket:
        raise ValueError("bucket obrigatório")
    if not path:
        raise ValueError("path obrigatório")

    client = get_supabase()
    key = path.strip("/")
    data = client.storage.from_(bucket.strip()).download(key)
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if data is None:
        return None
    return bytes(data)
