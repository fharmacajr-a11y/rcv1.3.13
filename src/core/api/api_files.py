from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

__all__ = ["upload_file", "download_folder_zip"]


def upload_file(file_path: str, bucket: str, remote_path: str) -> bool:
    """Upload a single file via adapters.storage.api; on failure logs and returns False."""
    try:
        from adapters.storage import api as storage_api

        storage_api.upload_file(file_path, bucket, remote_path)
        return True
    except Exception as e:
        log.error(f"Upload failed for {file_path}: {e}")
        return False


def download_folder_zip(bucket: str, prefix: str, dest_path: Optional[str] = None) -> Optional[str]:
    """Download a storage prefix as a ZIP, returning the path or None when the backend raises."""
    try:
        from adapters.storage import api as storage_api

        zip_path = storage_api.download_folder_zip(bucket, prefix, dest_path)  # pyright: ignore[reportCallIssue]
        return zip_path
    except Exception as e:
        log.error(f"Folder ZIP download failed for {prefix}: {e}")
        return None
