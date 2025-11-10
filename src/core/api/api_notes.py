from __future__ import annotations

import logging
from typing import Any, Dict, List

log = logging.getLogger(__name__)

__all__ = [
    "list_storage_files",
    "list_trash_clients",
    "restore_from_trash",
    "purge_from_trash",
    "resolve_asset",
]


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
        from src.core.services import lixeira_service

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
        from src.core.services import lixeira_service

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
        from src.core.services import lixeira_service

        lixeira_service.purge_clients(org_id, client_ids)
        return True
    except Exception as e:
        log.error(f"Purge from trash failed: {e}")
        return False


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
        from src.utils.resource_path import resource_path

        return resource_path(asset_name)
    except Exception:
        # Fallback: relative path
        return asset_name
