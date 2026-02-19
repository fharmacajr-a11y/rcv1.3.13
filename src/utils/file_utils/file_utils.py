"""Façade de utilitários de arquivos, reexportando bytes/path/zip helpers em um único pacote."""

from __future__ import annotations

from typing import Final

# compat: reexport pacote
from .bytes_utils import *  # noqa: F401,F403
from .path_utils import *  # noqa: F401,F403
from .zip_utils import *  # noqa: F401,F403

__all__: Final = tuple(name for name in globals().keys() if not name.startswith("_"))  # pyright: ignore[reportUnsupportedDunderAll]
