from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

__all__ = ["upload_file", "download_folder_zip"]


def upload_file(file_path: str, bucket: str, remote_path: str) -> bool:
    """
    Upload a single file to storage.

    Args:
        file_path: Local file path
        bucket: Storage bucket name
        remote_path: Remote path within bucket

    Returns:
        True if successful, False otherwise

    Delegates to:
        - adapters/storage/api.py::upload_file()

    Where to edit:
        - Upload logic: adapters/storage/api.py
        - Backend implementation: adapters/storage/supabase_storage.py
    """
    try:
        from adapters.storage import api as storage_api

        storage_api.upload_file(file_path, bucket, remote_path)
        return True
    except Exception as e:
        log.error(f"Upload failed for {file_path}: {e}")
        return False


def download_folder_zip(bucket: str, prefix: str, dest_path: Optional[str] = None) -> Optional[str]:
    """
    Download a folder from storage as a ZIP file.

    Args:
        bucket: Storage bucket name
        prefix: Folder prefix (e.g., "org_123/client_456")
        dest_path: Optional destination path (if None, uses temp file)

    Returns:
        Path to downloaded ZIP file, or None if failed

    Delegates to:
        - adapters/storage/api.py::download_folder_zip()

    Where to edit:
        - ZIP creation logic: adapters/storage/api.py
        - Streaming download: adapters/storage/supabase_storage.py
    """
    try:
        from adapters.storage import api as storage_api

        zip_path = storage_api.download_folder_zip(bucket, prefix, dest_path)  # pyright: ignore[reportCallIssue]
        return zip_path
    except Exception as e:
        log.error(f"Folder ZIP download failed for {prefix}: {e}")
        return None
