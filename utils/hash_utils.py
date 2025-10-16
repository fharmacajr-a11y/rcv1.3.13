"""Hashing helpers shared across the desktop application."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final, Union

PathLike = Union[str, Path]


def sha256_file(path: PathLike) -> str:
    """Return the SHA-256 checksum for the file at ``path``."""
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


__all__: Final = ["sha256_file"]

