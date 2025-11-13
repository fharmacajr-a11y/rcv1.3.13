"""Utilities for resolving resource paths in both dev and PyInstaller builds.

This module provides a robust resource_path() implementation that:
- Detects PyInstaller's _MEIPASS bundle directory
- Falls back cleanly to development paths
- Is fully tested for both scenarios

Also provides PathLike type alias and normalization helpers for cross-platform
path handling following PEP 519 recommendations.
"""

from __future__ import annotations

import os
import sys
from os import PathLike, fspath
from pathlib import Path
from typing import Final, TypeAlias, Union

# Type alias for path-like objects (PEP 519 compatible)
# Accepts str, pathlib.Path, or any object implementing __fspath__
# Reference: https://peps.python.org/pep-0519/
PathLikeStr: TypeAlias = Union[str, Path, PathLike[str]]


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


def ensure_str_path(path: PathLikeStr) -> str:
    """Normalize any path-like object to str using os.fspath (PEP 519).

    This helper accepts str, pathlib.Path, or any object implementing __fspath__
    and returns a normalized string representation. Follows Python's standard
    library conventions for path handling.

    Args:
        path: Any path-like object (str, Path, os.PathLike[str])

    Returns:
        String representation of the path

    Examples:
        >>> ensure_str_path("/usr/local")
        '/usr/local'
        >>> ensure_str_path(Path("/usr/local"))  # doctest: +SKIP
        '/usr/local'

    Reference:
        - PEP 519: https://peps.python.org/pep-0519/
        - os.fspath: https://docs.python.org/3/library/os.html#os.fspath
    """
    return str(fspath(path))


__all__: Final = ["resource_path", "is_bundled", "PathLikeStr", "ensure_str_path"]
