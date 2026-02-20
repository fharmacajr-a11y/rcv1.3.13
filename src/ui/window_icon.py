# -*- coding: utf-8 -*-
"""Utility module for applying the application icon to windows.

Provides a centralized way to apply rc.ico to all windows (Tk, Toplevel, CTkToplevel).
This ensures consistent branding across all dialogs and windows in the application.

Usage:
    from src.ui.window_icon import apply_app_icon
    apply_app_icon(my_toplevel_window)
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from pathlib import Path
from typing import Any, Union

log = logging.getLogger(__name__)

# Cache for loaded PhotoImage to prevent garbage collection
_icon_photo_cache: dict[int, tk.PhotoImage] = {}


def _get_icon_path() -> str | None:
    """Get the path to rc.ico using resource_path helper.

    Returns:
        Path to rc.ico if found, None otherwise.
    """
    try:
        from src.utils.paths import resource_path

        icon_path = resource_path("rc.ico")
        if os.path.exists(icon_path):
            return icon_path
    except Exception as e:
        log.debug(f"[WindowIcon] Error getting icon path via resource_path: {e}")

    # Fallback: try common locations
    fallback_paths = [
        Path(__file__).parent.parent.parent / "rc.ico",  # Project root
        Path.cwd() / "rc.ico",
    ]

    for path in fallback_paths:
        if path.exists():
            return str(path)

    return None


def apply_app_icon(window: Any, icon_path: Union[str, Path, None] = None) -> bool:
    """Apply the application icon (rc.ico) to a window.

    Works with Tk, Toplevel, and CTkToplevel windows. On Windows, uses iconbitmap.
    Falls back to iconphoto if iconbitmap fails (useful for Linux/Mac).

    Args:
        window: The window to apply the icon to (Tk, Toplevel, CTkToplevel).
        icon_path: Optional explicit path to the icon file. If None, uses rc.ico.

    Returns:
        True if icon was successfully applied, False otherwise.
    """
    if icon_path is None:
        icon_path = _get_icon_path()

    if icon_path is None:
        log.debug("[WindowIcon] No icon path available")
        return False

    icon_path_str = str(icon_path)

    # Try iconbitmap first (works best on Windows with .ico files)
    try:
        window.iconbitmap(icon_path_str)
        log.debug(f"[WindowIcon] Applied iconbitmap: {icon_path_str}")
        return True
    except Exception as e:
        log.debug(f"[WindowIcon] iconbitmap failed: {e}")

    # Fallback: try iconphoto with PNG version
    try:
        png_path = icon_path_str.replace(".ico", ".png")
        if os.path.exists(png_path):
            # Create PhotoImage and cache it to prevent GC
            photo = tk.PhotoImage(file=png_path)
            window_id = id(window)
            _icon_photo_cache[window_id] = photo

            # Apply to window (True = apply to all future toplevels from this root)
            window.iconphoto(False, photo)
            log.debug(f"[WindowIcon] Applied iconphoto: {png_path}")
            return True
    except Exception as e:
        log.debug(f"[WindowIcon] iconphoto fallback failed: {e}")

    return False


def apply_default_icon_to_root(root: tk.Tk, icon_path: Union[str, Path, None] = None) -> bool:
    """Apply the default icon to root window AND all future child Toplevels.

    On Windows with .ico files, this uses iconbitmap on root.
    With .png files, uses iconphoto with True flag to propagate to children.

    Args:
        root: The root Tk window.
        icon_path: Optional explicit path to the icon file. If None, uses rc.ico.

    Returns:
        True if icon was successfully applied, False otherwise.
    """
    if icon_path is None:
        icon_path = _get_icon_path()

    if icon_path is None:
        log.debug("[WindowIcon] No icon path available for root")
        return False

    icon_path_str = str(icon_path)
    success = False

    # Apply iconbitmap to root (Windows .ico)
    try:
        root.iconbitmap(icon_path_str)
        log.debug(f"[WindowIcon] Applied iconbitmap to root: {icon_path_str}")
        success = True
    except Exception as e:
        log.debug(f"[WindowIcon] iconbitmap on root failed: {e}")

    # Also try iconphoto with True flag to propagate to child windows
    try:
        png_path = icon_path_str.replace(".ico", ".png")
        if os.path.exists(png_path):
            photo = tk.PhotoImage(file=png_path)
            _icon_photo_cache[id(root)] = photo
            root.iconphoto(True, photo)  # True = apply to all child toplevels
            log.debug(f"[WindowIcon] Applied iconphoto to root (propagate): {png_path}")
            success = True
    except Exception as e:
        log.debug(f"[WindowIcon] iconphoto on root failed: {e}")

    return success


def cleanup_icon_cache(window: Any) -> None:
    """Remove cached PhotoImage for a destroyed window.

    Call this when a window is destroyed to free memory.

    Args:
        window: The window being destroyed.
    """
    window_id = id(window)
    if window_id in _icon_photo_cache:
        del _icon_photo_cache[window_id]
        log.debug(f"[WindowIcon] Cleaned up icon cache for window {window_id}")
