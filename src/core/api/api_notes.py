from __future__ import annotations

import logging
from typing import Any, Sequence

log = logging.getLogger(__name__)

__all__ = [
    "list_storage_files",
    "list_trash_clients",
    "restore_from_trash",
    "purge_from_trash",
    "resolve_asset",
]


def list_storage_files(bucket: str, prefix: str) -> list[dict[str, Any]]:
    """Return storage metadata for the given prefix; on error logs and returns an empty list."""
    try:
        from adapters.storage import api as storage_api

        return storage_api.list_files(bucket, prefix)  # pyright: ignore[reportCallIssue]
    except Exception as exc:
        log.error(f"List files failed for {prefix}: {exc}")
        return []


def list_trash_clients(org_id: str) -> list[dict[str, Any]]:
    """List soft-deleted clients for an organization; logs and returns [] when the backend fails."""
    try:
        from src.core.services import lixeira_service

        return lixeira_service.list_trash_clients(org_id)
    except Exception as exc:
        log.error(f"List trash clients failed: {exc}")
        return []


def restore_from_trash(org_id: str, client_ids: Sequence[str]) -> bool:
    """Restore the provided client IDs; logs and returns False if the service raises."""
    try:
        from src.core.services import lixeira_service

        lixeira_service.restore_clients(org_id, client_ids)  # pyright: ignore[reportArgumentType]
        return True
    except Exception as exc:
        log.error(f"Restore from trash failed: {exc}")
        return False


def purge_from_trash(org_id: str, client_ids: Sequence[str]) -> bool:
    """Permanently delete the given clients from trash; logs and returns False on error."""
    try:
        from src.core.services import lixeira_service

        lixeira_service.purge_clients(org_id, client_ids)
        return True
    except Exception as exc:
        log.error(f"Purge from trash failed: {exc}")
        return False


def resolve_asset(asset_name: str) -> str:
    """Resolve an asset path via resource_path, falling back to the original name on failure."""
    try:
        from src.utils.resource_path import resource_path

        return resource_path(asset_name)
    except Exception:
        return asset_name
