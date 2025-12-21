# adapters/storage/api.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Optional, Union

from .port import StoragePort
from . import supabase_storage
from .supabase_storage import DownloadCancelledError

# Backend pode ser um módulo com funções (supabase_storage) ou uma instância StoragePort.
_BackendType = Union[StoragePort, Any]

_BACKEND: _BackendType = supabase_storage


def _call(method: str, *args, **kwargs):
    target = _BACKEND
    fn = getattr(target, method, None)
    if callable(fn):
        return fn(*args, **kwargs)
    raise AttributeError(f"Backend atual não expõe '{method}'")


def set_storage_backend(backend: _BackendType) -> None:
    global _BACKEND
    _BACKEND = backend


def reset_storage_backend() -> None:
    set_storage_backend(supabase_storage)


@contextmanager
def using_storage_backend(backend: _BackendType):
    previous = _BACKEND
    set_storage_backend(backend)
    try:
        yield
    finally:
        set_storage_backend(previous)


def upload_file(local_path: object, remote_key: str, content_type: Optional[str] = None) -> str:
    return _call("upload_file", local_path, remote_key, content_type)  # pyright: ignore[reportReturnType]


def download_file(remote_key: str, local_path: Optional[str] = None):
    return _call("download_file", remote_key, local_path)


def delete_file(remote_key: str) -> bool:
    return _call("delete_file", remote_key)  # pyright: ignore[reportReturnType]


def list_files(prefix: str = "") -> Iterable[object]:
    return _call("list_files", prefix)  # pyright: ignore[reportReturnType]


def download_folder_zip(
    prefix: str,
    *,
    bucket: Optional[str] = None,
    zip_name: Optional[str] = None,
    out_dir: Optional[str] = None,
    timeout_s: int = 300,
    cancel_event: Optional[Any] = None,
    progress_cb: Optional[Any] = None,
):
    backend = get_current_backend()
    fn = getattr(backend, "download_folder_zip", None)
    if not callable(fn):
        raise AttributeError("Backend atual não expõe 'download_folder_zip'")
    kwargs = {
        "zip_name": zip_name,
        "out_dir": out_dir,
        "timeout_s": timeout_s,
        "cancel_event": cancel_event,
        "progress_cb": progress_cb,
    }
    if bucket is not None:
        kwargs["bucket"] = bucket
    return fn(prefix, **kwargs)


def get_current_backend() -> _BackendType:
    return _BACKEND


__all__ = [
    "upload_file",
    "download_file",
    "delete_file",
    "list_files",
    "download_folder_zip",
    "set_storage_backend",
    "reset_storage_backend",
    "using_storage_backend",
    "get_current_backend",
    "DownloadCancelledError",
]
