from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
        from src.utils import themes

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
        from src.utils import themes

        return themes.load_theme()
    except Exception:
        return "flatly"  # fallback


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
        from src.core.services import upload_service

        # Note: Actual implementation may differ; adapt as needed
        result = upload_service.upload_folder(
            local_dir, org_id=org_id, client_id=client_id, subdir=subdir
        )
        return result
    except Exception as e:
        log.error(f"Folder upload failed: {e}")
        return {"success": False, "uploaded_count": 0, "errors": [str(e)]}


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
        from src.core.services import clientes_service

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
        from src.core.services import clientes_service

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
        from src.core.services import clientes_service

        clientes_service.delete_cliente(client_id, soft=soft)
        return True
    except Exception as e:
        log.error(f"Delete client failed: {e}")
        return False


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
        from src.core.search import search_clientes

        return search_clientes(query, org_id=org_id)
    except Exception as e:
        log.error(f"Client search failed: {e}")
        return []
