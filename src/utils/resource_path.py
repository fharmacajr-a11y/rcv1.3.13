"""Utilities for resolving resource paths in both dev and PyInstaller builds."""

from __future__ import annotations

import os
import sys
from typing import Final


def resource_path(relative_path: str) -> str:
    """Return an absolute path to the given resource, handling PyInstaller."""
    try:
        base_path: str = getattr(sys, "_MEIPASS")  # type: ignore[attr-defined]
    except AttributeError:
        # Not running in PyInstaller bundle
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


__all__: Final = ["resource_path"]
