"""
application/api.py
------------------
Central facade API for core application operations.

This module provides a thin wrapper layer over existing services,
offering a single point of entry for common operations. It does NOT
move logic — all work is delegated to existing services/adapters.

Purpose:
- Single import point for GUI/CLI clients
- Clear API contract for operations
- Easier testing (mock this facade vs. 10 services)
- Future: can add caching, retry logic, telemetry here

Usage example (future):
    from application.api import upload_folder, download_folder_zip

    upload_folder("/path/to/local", org_id="123", client_id="456", subdir="SIFAP")
    download_folder_zip("org_123/client_456", dest="/path/to/save.zip")

Note: This is an ADDITIVE module. Existing code continues to work as-is.
      To integrate, replace direct service calls with api.* calls gradually.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import logging

log = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Theme Management
# -------------------------------------------------------------------------


def switch_theme(root: Any, theme_name: str) -> None:
    """
    Apply a theme to the application root window.

    Args:
        root: Tkinter root window (ttkbootstrap.Window)
        theme_name: Theme name (e.g., "flatly", "darkly")

    Delegates to:
        - utils/themes.py::apply_theme()
        - utils/theme_manager.py::set_theme()

    Where to edit:
        - Add new themes: utils/themes.py
        - Modify theme application logic: utils/themes.py::apply_theme()
    """
    try:
        from utils import themes

        themes.apply_theme(root, theme=theme_name)
    except Exception as e:
        log.warning(f"Failed to apply theme '{theme_name}': {e}")


def get_current_theme() -> str:
    """
    Get currently active theme name.

    Returns:
        Theme name (e.g., "flatly")

    Delegates to:
        - utils/themes.py::load_theme()
    """
    try:
        from utils import themes

        return themes.load_theme()
    except Exception:
        return "flatly"  # fallback


# -------------------------------------------------------------------------
# Storage Operations
# -------------------------------------------------------------------------


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


def upload_folder(
    local_dir: str, org_id: str, client_id: str, subdir: str = "GERAL"
) -> Dict[str, Any]:
    """
    Upload a folder of documents to storage (e.g., SIFAP, Farmacia Popular).

    Args:
        local_dir: Local directory path
        org_id: Organization ID
        client_id: Client ID
        subdir: Subdirectory name (default: "GERAL")

    Returns:
        Dict with keys: success (bool), uploaded_count (int), errors (list)

    Delegates to:
        - core/services/upload_service.py

    Where to edit:
        - Upload orchestration: core/services/upload_service.py
        - File validation: core/services/upload_service.py
        - Subpasta config: utils/subpastas_config.py
    """
    try:
        from core.services import upload_service

        # Note: Actual implementation may differ; adapt as needed
        result = upload_service.upload_folder(
            local_dir, org_id=org_id, client_id=client_id, subdir=subdir
        )
        return result
    except Exception as e:
        log.error(f"Folder upload failed: {e}")
        return {"success": False, "uploaded_count": 0, "errors": [str(e)]}


def download_folder_zip(
    bucket: str, prefix: str, dest_path: Optional[str] = None
) -> Optional[str]:
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

        zip_path = storage_api.download_folder_zip(bucket, prefix, dest_path)
        return zip_path
    except Exception as e:
        log.error(f"Folder ZIP download failed for {prefix}: {e}")
        return None


def list_storage_files(bucket: str, prefix: str) -> List[Dict[str, Any]]:
    """
    List files in a storage folder.

    Args:
        bucket: Storage bucket name
        prefix: Folder prefix

    Returns:
        List of file metadata dicts (name, size, modified, etc.)

    Delegates to:
        - adapters/storage/api.py::list_files()
    """
    try:
        from adapters.storage import api as storage_api

        return storage_api.list_files(bucket, prefix)
    except Exception as e:
        log.error(f"List files failed for {prefix}: {e}")
        return []


# -------------------------------------------------------------------------
# Trash/Lixeira Operations
# -------------------------------------------------------------------------


def list_trash_clients(org_id: str) -> List[Dict[str, Any]]:
    """
    List clients in trash (soft-deleted).

    Args:
        org_id: Organization ID

    Returns:
        List of client dicts

    Delegates to:
        - core/services/lixeira_service.py::list_trash_clients()
        - core/db_manager/db_manager.py::list_clientes_deletados()

    Where to edit:
        - Trash query logic: core/services/lixeira_service.py
        - Database query: core/db_manager/db_manager.py
    """
    try:
        from core.services import lixeira_service

        return lixeira_service.list_trash_clients(org_id)
    except Exception as e:
        log.error(f"List trash clients failed: {e}")
        return []


def restore_from_trash(org_id: str, client_ids: List[str]) -> bool:
    """
    Restore clients from trash.

    Args:
        org_id: Organization ID
        client_ids: List of client IDs to restore

    Returns:
        True if successful, False otherwise

    Delegates to:
        - core/services/lixeira_service.py::restore_clients()

    Where to edit:
        - Restore logic: core/services/lixeira_service.py
        - Database update: core/db_manager/db_manager.py::restore_clientes()
    """
    try:
        from core.services import lixeira_service

        lixeira_service.restore_clients(org_id, client_ids)
        return True
    except Exception as e:
        log.error(f"Restore from trash failed: {e}")
        return False


def purge_from_trash(org_id: str, client_ids: List[str]) -> bool:
    """
    Permanently delete clients from trash.

    Args:
        org_id: Organization ID
        client_ids: List of client IDs to purge

    Returns:
        True if successful, False otherwise

    Delegates to:
        - core/services/lixeira_service.py::purge_clients()

    Where to edit:
        - Purge logic: core/services/lixeira_service.py
        - Storage cleanup: adapters/storage/api.py
    """
    try:
        from core.services import lixeira_service

        lixeira_service.purge_clients(org_id, client_ids)
        return True
    except Exception as e:
        log.error(f"Purge from trash failed: {e}")
        return False


# -------------------------------------------------------------------------
# Resource Management
# -------------------------------------------------------------------------


def resolve_asset(asset_name: str) -> str:
    """
    Resolve path to application asset (icon, image, etc.).

    Works in both dev and PyInstaller bundled environments.

    Args:
        asset_name: Asset filename (e.g., "rc.ico", "logo.png")

    Returns:
        Absolute path to asset

    Delegates to:
        - utils/resource_path.py::resource_path()

    Where to edit:
        - Resource resolution logic: utils/resource_path.py
    """
    try:
        from utils.resource_path import resource_path

        return resource_path(asset_name)
    except Exception:
        # Fallback: relative path
        return asset_name


# -------------------------------------------------------------------------
# Client CRUD (High-Level)
# -------------------------------------------------------------------------


def create_client(data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new client.

    Args:
        data: Client data dict (razao_social, cnpj, nome_fantasia, etc.)

    Returns:
        Client ID if successful, None otherwise

    Delegates to:
        - core/services/clientes_service.py::create_cliente()

    Where to edit:
        - Validation: core/services/clientes_service.py
        - Database insert: core/db_manager/db_manager.py::insert_cliente()
    """
    try:
        from core.services import clientes_service

        client_id = clientes_service.create_cliente(data)
        return client_id
    except Exception as e:
        log.error(f"Create client failed: {e}")
        return None


def update_client(client_id: str, data: Dict[str, Any]) -> bool:
    """
    Update an existing client.

    Args:
        client_id: Client ID
        data: Updated client data

    Returns:
        True if successful, False otherwise

    Delegates to:
        - core/services/clientes_service.py::update_cliente()
    """
    try:
        from core.services import clientes_service

        clientes_service.update_cliente(client_id, data)
        return True
    except Exception as e:
        log.error(f"Update client failed: {e}")
        return False


def delete_client(client_id: str, soft: bool = True) -> bool:
    """
    Delete a client (soft or hard delete).

    Args:
        client_id: Client ID
        soft: If True, soft delete (move to trash); if False, hard delete

    Returns:
        True if successful, False otherwise

    Delegates to:
        - core/services/clientes_service.py::delete_cliente()
    """
    try:
        from core.services import clientes_service

        clientes_service.delete_cliente(client_id, soft=soft)
        return True
    except Exception as e:
        log.error(f"Delete client failed: {e}")
        return False


# -------------------------------------------------------------------------
# Search
# -------------------------------------------------------------------------


def search_clients(query: str, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search for clients by CNPJ, razão social, or nome fantasia.

    Args:
        query: Search query string
        org_id: Optional organization ID filter

    Returns:
        List of matching client dicts

    Delegates to:
        - core/search/search.py::search_clientes()

    Where to edit:
        - Search logic: core/search/search.py
        - Query optimization: core/db_manager/db_manager.py
    """
    try:
        from core.search import search_clientes

        return search_clientes(query, org_id=org_id)
    except Exception as e:
        log.error(f"Client search failed: {e}")
        return []


# -------------------------------------------------------------------------
# Export for easy discovery
# -------------------------------------------------------------------------

__all__ = [
    # Theme
    "switch_theme",
    "get_current_theme",
    # Storage
    "upload_file",
    "upload_folder",
    "download_folder_zip",
    "list_storage_files",
    # Trash
    "list_trash_clients",
    "restore_from_trash",
    "purge_from_trash",
    # Resources
    "resolve_asset",
    # CRUD
    "create_client",
    "update_client",
    "delete_client",
    # Search
    "search_clients",
]
