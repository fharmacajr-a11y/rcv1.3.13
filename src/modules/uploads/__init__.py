"""API publica do modulo Uploads / Arquivos."""

from __future__ import annotations

from .view import UploadsFrame, open_files_browser
from .service import (
    DownloadCancelledError,
    UploadItem,
    build_items_from_files,
    client_prefix_for_id,
    collect_pdfs_from_folder,
    delete_file,
    download_bytes,
    download_file,
    download_folder_zip,
    format_cnpj_for_display,
    get_clients_bucket,
    get_current_org_id,
    list_storage_objects,
    strip_cnpj_from_razao,
    upload_folder_to_supabase,
    upload_items_for_client,
)
from .exceptions import (
    UploadError,
    UploadValidationError,
    UploadNetworkError,
    UploadServerError,
    ERROR_MESSAGES,
    make_validation_error,
    make_network_error,
    make_server_error,
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
    upload_with_retry,
    classify_upload_exception,
)
from . import service

__all__ = [
    # View
    "UploadsFrame",
    "open_files_browser",
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
