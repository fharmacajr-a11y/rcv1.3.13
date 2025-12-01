from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

from src.core.models import Cliente

log = logging.getLogger(__name__)

__all__ = [
    "switch_theme",
    "get_current_theme",
    "upload_folder",
    "create_client",
    "update_client",
    "delete_client",
    "search_clients",
]


def switch_theme(root: Any, theme_name: str) -> None:
    """Apply a UI theme and log a warning if applying fails."""
    try:
        from src.utils import themes

        themes.apply_theme(root, theme=theme_name)
    except Exception as exc:
        log.warning(f"Failed to apply theme '{theme_name}': {exc}")


def get_current_theme() -> str:
    """Return the stored theme name, falling back to 'flatly' when load_theme errors."""
    try:
        from src.utils import themes

        return themes.load_theme()
    except Exception:
        return "flatly"


def upload_folder(local_dir: str, org_id: str, client_id: str, subdir: str = "GERAL") -> Dict[str, Any]:
    """Upload a folder to storage; on failure log the error and return a default payload."""
    try:
        from src.core.services import upload_service

        return upload_service.upload_folder(local_dir, org_id=org_id, client_id=client_id, subdir=subdir)
    except Exception as exc:
        log.error(f"Folder upload failed: {exc}")
        return {"success": False, "uploaded_count": 0, "errors": [str(exc)]}


def create_client(data: Mapping[str, Any]) -> Optional[str]:
    """Create a client via clientes_service; log and return None when it raises."""
    try:
        from src.core.services import clientes_service

        return clientes_service.create_cliente(data)
    except Exception as exc:
        log.error(f"Create client failed: {exc}")
        return None


def update_client(client_id: str, data: Mapping[str, Any]) -> bool:
    """Update client data; log and return False if clientes_service errors."""
    try:
        from src.core.services import clientes_service

        clientes_service.update_cliente(client_id, data)  # pyright: ignore[reportCallIssue]
        return True
    except Exception as exc:
        log.error(f"Update client failed: {exc}")
        return False


def delete_client(client_id: str, soft: bool = True) -> bool:
    """Delete a client (soft or hard); log and return False when the service fails."""
    try:
        from src.core.services import clientes_service

        clientes_service.delete_cliente(client_id, soft=soft)
        return True
    except Exception as exc:
        log.error(f"Delete client failed: {exc}")
        return False


def search_clients(query: str, org_id: Optional[str] = None) -> list[Cliente]:
    """Search clients using search_clientes; log and return [] on errors."""
    try:
        from src.core.search import search_clientes

        return search_clientes(query, org_id=org_id)
    except Exception as exc:
        log.error(f"Client search failed: {exc}")
        return []
