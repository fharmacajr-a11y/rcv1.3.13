from src.core.api import api_clients, api_files, api_notes
from src.core.api.api_clients import (
    create_client,
    delete_client,
    get_current_theme,
    search_clients,
    switch_theme,
    update_client,
    upload_folder,
)
from src.core.api.api_files import download_folder_zip, upload_file
from src.core.api.api_notes import (
    list_storage_files,
    list_trash_clients,
    purge_from_trash,
    resolve_asset,
    restore_from_trash,
)
from src.core.api.router import register_endpoints

__all__ = [
    "register_endpoints",
    "api_clients",
    "api_files",
    "api_notes",
    "switch_theme",
    "get_current_theme",
    "upload_file",
    "upload_folder",
    "download_folder_zip",
    "list_storage_files",
    "list_trash_clients",
    "restore_from_trash",
    "purge_from_trash",
    "resolve_asset",
    "create_client",
    "update_client",
    "delete_client",
    "search_clients",
]
