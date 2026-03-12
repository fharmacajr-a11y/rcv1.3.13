"""API publica do modulo Uploads / Arquivos."""

from __future__ import annotations

# Imports leves — não puxam Supabase; sempre disponíveis.
from .exceptions import (
    ERROR_MESSAGES,
    UploadError,
    UploadNetworkError,
    UploadServerError,
    UploadValidationError,
    make_network_error,
    make_server_error,
    make_validation_error,
)
from .file_validator import (
    ALLOWED_EXTENSIONS,
    MAX_SIZE_BYTES,
    FileValidationResult,
    validate_upload_file,
    validate_upload_file_strict,
    validate_upload_files,
)
from .upload_retry import (
    classify_upload_exception,
    upload_with_retry,
)

# Imports pesados (Supabase/rede) — carregados sob demanda via __getattr__ (PEP 562).
_SERVICE_EXPORTS: frozenset[str] = frozenset(
    {
        "service",
        "UploadItem",
        "collect_pdfs_from_folder",
        "collect_files_from_folder",
        "build_items_from_files",
        "upload_items_for_client",
        "upload_folder_to_supabase",
        "download_folder_zip",
        "download_file",
        "download_bytes",
        "delete_file",
        "list_storage_objects",
        "DownloadCancelledError",
        "client_prefix_for_id",
        "get_clients_bucket",
        "get_current_org_id",
        "format_cnpj_for_display",
        "strip_cnpj_from_razao",
    }
)


def __getattr__(name: str) -> object:
    """Carrega .service sob demanda para não puxar supabase-py ao importar o pacote."""
    if name in _SERVICE_EXPORTS:
        import importlib  # noqa: PLC0415

        _svc = importlib.import_module(f"{__name__}.service")
        # Cache no namespace do módulo para evitar nova chamada a __getattr__
        globals()["service"] = _svc
        if name == "service":
            return _svc
        return getattr(_svc, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Service
    "service",
    "UploadItem",
    "collect_pdfs_from_folder",
    "build_items_from_files",
    "upload_items_for_client",
    "upload_folder_to_supabase",
    "download_folder_zip",
    "download_file",
    "download_bytes",
    "delete_file",
    "list_storage_objects",
    "DownloadCancelledError",
    "client_prefix_for_id",
    "get_clients_bucket",
    "get_current_org_id",
    "format_cnpj_for_display",
    "strip_cnpj_from_razao",
    # Exceptions (FASE 7)
    "UploadError",
    "UploadValidationError",
    "UploadNetworkError",
    "UploadServerError",
    "ERROR_MESSAGES",
    "make_validation_error",
    "make_network_error",
    "make_server_error",
    # File Validation (FASE 7)
    "ALLOWED_EXTENSIONS",
    "MAX_SIZE_BYTES",
    "FileValidationResult",
    "validate_upload_file",
    "validate_upload_file_strict",
    "validate_upload_files",
    # Retry (FASE 7)
    "upload_with_retry",
    "classify_upload_exception",
]
