# adapters/storage/port.py
from __future__ import annotations
from typing import Protocol, Optional, Iterable, Any


class StoragePort(Protocol):
    def upload_file(self, local_path: Any, remote_key: str, content_type: Optional[str] = None) -> str: ...
    def download_file(self, remote_key: str, local_path: Optional[str] = None) -> Any: ...
    def delete_file(self, remote_key: str) -> bool: ...
    def list_files(self, prefix: str = "") -> Iterable[Any]: ...

    def download_folder_zip(
        self,
        prefix: str,
        *,
        zip_name: Optional[str] = None,
        out_dir: Optional[str] = None,
        timeout_s: int = 300,
        cancel_event: Optional[Any] = None,
    ) -> Any: ...
