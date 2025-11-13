"""
application/commands.py
-----------------------
Command registry for orchestrating application operations.

Provides a simple command pattern implementation where operations
can be registered and invoked by name. Useful for:
- CLI tools (scripts/rc.py)
- Testing (mock commands)
- Telemetry/logging (wrap all commands)
- Future: undo/redo, command history

Usage:
    from application import commands

    # Register a command
    commands.register("upload:folder", my_upload_func, help="Upload a folder")

    # Run a command
    result = commands.run("upload:folder", local_dir="/path", org_id="123")

Note: This is an ADDITIVE module. GUI code can continue calling services
      directly. Commands are optional and primarily for CLI/scripting.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

log = logging.getLogger(__name__)

# Command registry: {name: (func, help, defaults)}
_REGISTRY: Dict[str, tuple[Callable, str, dict]] = {}


def register(name: str, func: Callable, help: str = "", **defaults: Any) -> None:
    """
    Register a command.

    Args:
        name: Command name (e.g., "theme:switch", "upload:folder")
        func: Callable to execute
        help: Help text describing the command
        **defaults: Default keyword arguments

    Example:
        def upload_wrapper(local_dir, org_id, subdir="GERAL"):
        result = upload_or_link_external()
        if result:
            try:
                from src.core.api import upload_folder
            return upload_folder(local_dir, org_id, client_id="", subdir=subdir)

        register(
            "upload:folder",
            upload_wrapper,
            help="Upload a folder to storage",
            subdir="GERAL"
        )
    """
    if name in _REGISTRY:
        log.warning(f"Command '{name}' already registered, overwriting")

    _REGISTRY[name] = (func, help, defaults)
    log.debug(f"Registered command: {name}")


def unregister(name: str) -> bool:
    """
    Unregister a command.

    Args:
        name: Command name

    Returns:
        True if command was registered and removed, False otherwise
    """
    if name in _REGISTRY:
        del _REGISTRY[name]
        log.debug(f"Unregistered command: {name}")
        return True
    return False


def run(name: str, **kwargs: Any) -> Any:
    """
    Execute a registered command.

    Args:
        name: Command name
        **kwargs: Arguments to pass to the command

    Returns:
        Command result (any type)

    Raises:
        KeyError: If command not found
        Exception: If command execution fails

    Example:
        result = run("upload:folder", local_dir="/docs", org_id="123")
    """
    if name not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys())
        raise KeyError(f"Command '{name}' not found. Available: {available}")

    func, _, defaults = _REGISTRY[name]

    # Merge defaults with provided kwargs
    merged_kwargs = {**defaults, **kwargs}

    log.info(f"Executing command: {name} with {merged_kwargs}")

    try:
        result = func(**merged_kwargs)
        log.info(f"Command '{name}' completed successfully")
        return result
    except Exception as e:
        log.error(f"Command '{name}' failed: {e}", exc_info=True)
        raise


def list_commands() -> Dict[str, str]:
    """
    List all registered commands.

    Returns:
        Dict mapping command names to help text
    """
    return {name: help_text for name, (_, help_text, _) in _REGISTRY.items()}


def get_command_info(name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed info about a command.

    Args:
        name: Command name

    Returns:
        Dict with keys: name, func, help, defaults
        or None if command not found
    """
    if name not in _REGISTRY:
        return None

    func, help_text, defaults = _REGISTRY[name]

    return {
        "name": name,
        "func": func.__name__,
        "help": help_text,
        "defaults": defaults,
    }


# -------------------------------------------------------------------------
# Bootstrap: Register built-in commands
# -------------------------------------------------------------------------


def _bootstrap_commands() -> None:
    """Register standard application commands."""

    # Theme commands
    def _theme_switch(root: Any, theme_name: str) -> None:
        from src.core.api import switch_theme

        switch_theme(root, theme_name)

    register(
        "theme:switch",
        _theme_switch,
        help="Switch application theme (flatly, darkly, etc.)",
    )

    # Upload commands
    def _upload_folder(local_dir: str, org_id: str, client_id: str, subdir: str = "GERAL") -> Dict:
        from src.core.api import upload_folder

        return upload_folder(local_dir, org_id, client_id, subdir)

    register(
        "upload:folder",
        _upload_folder,
        help="Upload a folder of documents to storage",
        subdir="GERAL",
    )

    # Download commands
    def _download_zip(bucket: str, prefix: str, dest: Optional[str] = None) -> Optional[str]:
        from src.core.api import download_folder_zip

        return download_folder_zip(bucket, prefix, dest)

    register("download:zip", _download_zip, help="Download a storage folder as ZIP")

    # Trash commands
    def _trash_list(org_id: str) -> list:
        from src.core.api import list_trash_clients

        return list_trash_clients(org_id)

    register("trash:list", _trash_list, help="List clients in trash")

    def _trash_restore(org_id: str, client_ids: list) -> bool:
        from src.core.api import restore_from_trash

        return restore_from_trash(org_id, client_ids)

    register("trash:restore", _trash_restore, help="Restore clients from trash")

    def _trash_purge(org_id: str, client_ids: list) -> bool:
        from src.core.api import purge_from_trash

        return purge_from_trash(org_id, client_ids)

    register("trash:purge", _trash_purge, help="Permanently delete clients from trash")

    # Asset commands
    def _asset_path(name: str) -> str:
        from src.core.api import resolve_asset

        return resolve_asset(name)

    register(
        "asset:path",
        _asset_path,
        help="Resolve path to application asset (icon, image, etc.)",
    )

    # Search commands
    def _client_search(query: str, org_id: Optional[str] = None) -> list:
        from src.core.api import search_clients

        return search_clients(query, org_id)

    register("client:search", _client_search, help="Search for clients")

    log.debug("Bootstrap commands registered")


# Auto-bootstrap on import
_bootstrap_commands()


__all__ = [
    "register",
    "unregister",
    "run",
    "list_commands",
    "get_command_info",
]
