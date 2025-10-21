from application.api.router import register_endpoints
from application.api import api_clients, api_files, api_notes

from application.api.api_clients import (
    create_client,
    delete_client,
    search_clients,
    get_current_theme,
    update_client,
    upload_folder,
    switch_theme,
)
from application.api.api_files import download_folder_zip, upload_file
from application.api.api_notes import (
    list_storage_files,
    list_trash_clients,
    purge_from_trash,
    resolve_asset,
    restore_from_trash,
)

__all__ = [
    "register_endpoints",
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
