"""Utilities for resolving resource paths in both dev and PyInstaller builds.

This module provides a robust resource_path() implementation that:
- Detects PyInstaller's _MEIPASS bundle directory
- Falls back cleanly to development paths
- Is fully tested for both scenarios
"""

from __future__ import annotations

import os
import sys
from typing import Final


def resource_path(relative_path: str) -> str:
    """Return an absolute path to the given resource.

    Handles both PyInstaller bundled executables and development environments.

    Args:
        relative_path: Path relative to the application root

    Returns:
        Absolute path to the resource

    Examples:
        >>> resource_path("rc.ico")  # doctest: +SKIP
        '/path/to/bundle/rc.ico'  # or dev path
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path: str = getattr(sys, "_MEIPASS")  # type: ignore[attr-defined]
    except AttributeError:
        # Development mode: use current working directory
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def is_bundled() -> bool:
    """Check if running as a PyInstaller bundle.

    Returns:
        True if running from a bundled executable, False otherwise
    """
    return hasattr(sys, "_MEIPASS")


__all__: Final = ["resource_path", "is_bundled"]
