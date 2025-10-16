
from __future__ import annotations
from config.paths import CLOUD_ONLY
"""Small wrappers around supabase storage upload/download (private buckets)."""
from pathlib import Path
import mimetypes
import os
from typing import Optional
from infra.supabase_client import supabase

BUCKET = (os.getenv("SUPABASE_BUCKET") or "rc-docs").strip() or "rc-docs"

def _mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"

def upload_file(local_path: str | Path, dest_key: str, bucket: Optional[str] = None) -> dict:
    path = Path(local_path)
    name = bucket or BUCKET
    with path.open("rb") as fh:
        return supabase.storage.from_(name).upload(dest_key.strip("/"), fh, {"content-type": _mime(path), "upsert": True})

def download_to_path(key: str, local_path: str | Path, bucket: Optional[str] = None) -> Path:
    name = bucket or BUCKET
    data = supabase.storage.from_(name).download(key.strip("/"))
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    p = Path(local_path)
    if not CLOUD_ONLY:
        p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as fh:
        fh.write(data)
    return p