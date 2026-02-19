"""Utilities for resolving resource paths in both dev and PyInstaller builds.

BACKWARD COMPATIBILITY MODULE
This module re-exports resource_path() from src.utils.paths for backward
compatibility. New code should import directly from src.utils.paths.

P1-003: Removed duplicate implementation to avoid code duplication.
"""

from __future__ import annotations

from typing import Final

# Re-export from canonical source (src.utils.paths)
from src.utils.paths import resource_path

__all__: Final = ["resource_path"]
